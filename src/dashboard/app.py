import streamlit as st
import duckdb
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import os
import asyncio
import asyncpg
import shutil
from datetime import datetime, timedelta
import src.analysis.indicators as ind

# --- 설정 (Configuration) ---
TICKS_DB = os.getenv("TICKS_DB", "data/ticks.duckdb")
NEWS_DB = os.getenv("NEWS_DB", "data/market_data.duckdb")
TIMESCALEDB_URL = os.getenv("TIMESCALEDB_URL", "postgresql://postgres:password@stock-timescale:5432/stockval")
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", "5")) # 상용 수준을 위해 인터벌 단축

# 페이지 설정
st.set_page_config(
    page_title="Antigravity Pro Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 커스텀 스타일링 (Premium Dark Mode)
st.markdown("""
<style>
    .main { background-color: #0b0e14; }
    .stMetric { background-color: #161a25; padding: 15px; border-radius: 8px; border: 1px solid #2d3446; }
    .stSelectbox label, .stSlider label { color: #a0aec0; font-weight: 600; }
    h1, h2, h3 { color: #edf2f7; font-family: 'Inter', sans-serif; }
</style>
""", unsafe_allow_html=True)

# --- 데이터 로딩 (Data Engine) ---

def get_duckdb_conn(db_path):
    """
    DuckDB 데이터베이스 연결을 생성한다. 
    동시성 문제(File Lock)를 방지하기 위해 파일 스냅샷을 만들어 읽기 전용으로 연결한다.

    Args:
        db_path (str): DuckDB 파일 경로
    
    Returns:
        duckdb.DuckDBPyConnection: 연결 객체 또는 None
    """
    if not os.path.exists(db_path): return None
    temp_path = f"/tmp/{os.path.basename(db_path)}"
    try:
        shutil.copyfile(db_path, temp_path)
        return duckdb.connect(temp_path, read_only=True)
    except: return None

async def load_ohlc_data(symbol, interval="1m", hours=6):
    """
    TimescaleDB의 Continuous Aggregates로부터 OHLC(Open, High, Low, Close, Volume) 데이터를 로드한다.
    추가로 SMA(이동평균선) 기술 지표를 계산하여 데이터프레임에 포함한다.

    Args:
        symbol (str): 종목 심볼
        interval (str): 데이터 주기 ('1m', '5m' 등)
        hours (int): 조회할 과거 시간 범위
    
    Returns:
        pd.DataFrame: OHLCV 및 기술 지표가 포함된 데이터프레임
    """
    try:
        conn = await asyncpg.connect(TIMESCALEDB_URL)
        
        # 인터벌에 따른 뷰 선택
        view_name = "candles_1m" if interval == "1m" else "candles_5m"
        
        query = f"""
            SELECT bucket as time, open, high, low, close, volume
            FROM {view_name}
            WHERE symbol = $1 AND bucket > NOW() - INTERVAL '{hours} hours'
            ORDER BY bucket ASC
        """
        rows = await conn.fetch(query, symbol)
        await conn.close()
        
        df = pd.DataFrame(rows, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        if not df.empty:
            # 기술 지표 계산 (SMA 20, 50)
            df['sma20'] = df['close'].rolling(window=20).mean()
            df['sma50'] = df['close'].rolling(window=50).mean()
            
            # 고급 기술 지표 추가
            df['rsi'] = ind.calculate_rsi(df)
            df['macd'], df['macd_signal'], df['macd_hist'] = ind.calculate_macd(df)
            df['bb_upper'], df['bb_mid'], df['bb_lower'] = ind.calculate_bollinger_bands(df)
            
        return df
    except Exception as e:
        st.error(f"데이터베이스 연결 오류: {e}")
        return pd.DataFrame()

async def get_active_symbols():
    try:
        conn = await asyncpg.connect(TIMESCALEDB_URL)
        rows = await conn.fetch("SELECT DISTINCT symbol FROM market_ticks WHERE time > NOW() - INTERVAL '24 hours'")
        await conn.close()
        return [r['symbol'] for r in rows]
    except: return []

# --- 사이드바 (Sidebar Controls) ---
with st.sidebar:
    st.header("⚙️ 터미널 설정")
    selected_interval = st.selectbox("봉 주기", ["1m", "5m"], index=0)
    window_hours = st.slider("조회 범위 (시간)", 1, 24, 6)
    
    st.divider()
    st.header("📈 지표 설정")
    show_sma = st.checkbox("이동평균선 (SMA)", value=True)
    show_bb = st.checkbox("볼린저 밴드 (BB)", value=True)
    show_rsi = st.checkbox("RSI 지수", value=True)
    show_macd = st.checkbox("MACD 인디케이터", value=True)
    
    st.divider()
    st.info("💡 Continuous Aggregates 기술을 사용하여 대용량 데이터를 지연 없이 렌더링합니다.")

# --- 메인 화면 (Main Terminal) ---
st.title("⚡ Antigravity Pro Terminal")
st.caption(f"인프라 상태: 정상 연결됨 | 최종 갱신: {datetime.now().strftime('%H:%M:%S')}")

# 1. 상단 지표 (Top Metrics)
symbols = asyncio.run(get_active_symbols())
if symbols:
    m_cols = st.columns(min(len(symbols), 5))
    for i, sym in enumerate(symbols[:5]): # 상위 5개만 메트릭 표시
        df_mini = asyncio.run(load_ohlc_data(sym, interval="1m", hours=1))
        if not df_mini.empty:
            curr = df_mini.iloc[-1]
            prev = df_mini.iloc[-2]['close'] if len(df_mini) > 1 else curr['close']
            diff = curr['close'] - prev
            pct = (diff / prev) * 100 if prev != 0 else 0
            with m_cols[i]:
                st.metric(sym, f"{curr['close']:,.0f}", f"{pct:+.2f}%")

st.divider()

# 2. 메인 차트 및 뉴스 (Charts & Intelligence)
col_chart, col_news = st.columns([3, 1])

with col_chart:
    st.subheader("📊 프로페셔널 차트 분석")
    if symbols:
        target_sym = st.selectbox("분석 대상 종목 선택", symbols)
        df = asyncio.run(load_ohlc_data(target_sym, interval=selected_interval, hours=window_hours))
        
        if not df.empty:
            # Subplots 구성 결정
            rows = 2
            row_heights = [0.7, 0.3]
            if show_rsi:
                rows += 1
                row_heights = [0.5, 0.2, 0.3] # 임시 비율 조정
            if show_macd:
                rows += 1
                # 비율 재조정 (Price가 항상 절반 정도 차지하도록)
                ph = 0.4
                others = (1.0 - ph) / (rows - 1)
                row_heights = [ph] + [others] * (rows - 1)

            fig = make_subplots(
                rows=rows, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.03, 
                row_heights=row_heights
            )
            
            # Row index tracker
            current_row = 1

            # 1. 캔들스틱 (Price)
            fig.add_trace(go.Candlestick(
                x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                name="OHLC", increasing_line_color='#ef5350', decreasing_line_color='#26a69a'
            ), row=current_row, col=1)
            
            # 이동평균선 오버레이
            if show_sma:
                fig.add_trace(go.Scatter(x=df['time'], y=df['sma20'], name="SMA 20", line=dict(color='#ffeb3b', width=1)), row=current_row, col=1)
                fig.add_trace(go.Scatter(x=df['time'], y=df['sma50'], name="SMA 50", line=dict(color='#2196f3', width=1)), row=current_row, col=1)
            
            # 볼린저 밴드 오버레이
            if show_bb:
                fig.add_trace(go.Scatter(x=df['time'], y=df['bb_upper'], name="BB Upper", line=dict(color='rgba(173, 216, 230, 0.4)', width=1, dash='dot')), row=current_row, col=1)
                fig.add_trace(go.Scatter(x=df['time'], y=df['bb_lower'], name="BB Lower", line=dict(color='rgba(173, 216, 230, 0.4)', width=1, dash='dot'), fill='tonexty'), row=current_row, col=1)

            current_row += 1

            # 2. 거래량 (Volume)
            colors = ['#ef5350' if row['open'] > row['close'] else '#26a69a' for _, row in df.iterrows()]
            fig.add_trace(go.Bar(x=df['time'], y=df['volume'], name="Volume", marker_color=colors), row=current_row, col=1)
            current_row += 1

            # 3. RSI
            if show_rsi:
                fig.add_trace(go.Scatter(x=df['time'], y=df['rsi'], name="RSI", line=dict(color='#9c27b0', width=1.5)), row=current_row, col=1)
                # RSI 70/30 가이드라인
                fig.add_hline(y=70, line_dash="dot", line_color="red", row=current_row, col=1)
                fig.add_hline(y=30, line_dash="dot", line_color="green", row=current_row, col=1)
                current_row += 1

            # 4. MACD
            if show_macd:
                fig.add_trace(go.Scatter(x=df['time'], y=df['macd'], name="MACD", line=dict(color='#2196f3', width=1.5)), row=current_row, col=1)
                fig.add_trace(go.Scatter(x=df['time'], y=df['macd_signal'], name="Signal", line=dict(color='#ff9800', width=1.5)), row=current_row, col=1)
                fig.add_trace(go.Bar(x=df['time'], y=df['macd_hist'], name="Hist", marker_color='rgba(255, 255, 255, 0.3)'), row=current_row, col=1)
                current_row += 1
            
            # 레이아웃 커스텀
            fig.update_layout(
                template="plotly_dark",
                xaxis_rangeslider_visible=False,
                height=800 if rows > 2 else 650,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig.update_yaxes(title_text="Price", row=1, col=1)
            fig.update_yaxes(title_text="Vol", row=2, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("데이터를 불러오는 중입니다... (데이터가 충분하지 않을 수 있습니다)")
    else:
        st.info("수집된 종목이 없습니다. 수집기 상태를 확인하세요.")

with col_news:
    st.subheader("📰 뉴스 인텔리전스")
    conn_news = get_duckdb_conn(NEWS_DB)
    if conn_news:
        try:
            news_df = conn_news.execute("SELECT * FROM news ORDER BY published_at DESC LIMIT 15").fetchdf()
            if not news_df.empty:
                for _, row in news_df.iterrows():
                    with st.expander(f"{row['title'][:30]}...", expanded=False):
                        st.markdown(f"**[{row['source']}]** {row['title']}")
                        st.caption(f"시간: {row['published_at']}")
                        st.write(f"[기사 원문 보기]({row['link']})")
                        if row['keywords']: st.info(f"태그: {row['keywords']}")
            else:
                st.write("최근 뉴스가 없습니다.")
        finally:
            conn_news.close()

# 자동 갱신을 위한 JS (Streamlit natively supports this via state or loops, 
# but for a terminal experience we use a short loop if needed or just cache TTL)
time.sleep(REFRESH_INTERVAL)
st.rerun()
