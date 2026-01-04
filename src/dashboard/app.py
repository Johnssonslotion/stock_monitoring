import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import time
import os
from datetime import datetime, timedelta

# Page Config
st.set_page_config(
    page_title="Stock Monitoring Dashboard",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Stock Monitoring Dashboard")

import shutil

# ... (Previous imports)

def get_db_connection(db_path):
    """
    DuckDB 동시성 문제(Lock)를 회피하기 위해 
    DB 파일을 임시 경로로 복사(Snapshot)하여 연결합니다.
    """
    if not os.path.exists(db_path):
        return None
        
    # Create a temp filename based on original filename
    filename = os.path.basename(db_path)
    temp_path = f"/tmp/{filename}"
    
    try:
        # Copy the file to temp location
        # shutil.copy2 preserves metadata, copyfile is faster
        # Copying .wal file might be needed if checkpoint hasn't happened, 
        # but let's try just the main db file first.
        # Archiver holds the lock, so direct read fails. File copy usually works.
        shutil.copyfile(db_path, temp_path)
        
        # Connect to the temp file
        conn = duckdb.connect(temp_path, read_only=True)
        return conn
    except Exception as e:
        st.error(f"Snapshot creation failed: {e}")
        return None

@st.cache_data(ttl=5)
def load_ticks_data(hours=1):
    """Load tick data from DuckDB Snapshot"""
    try:
        conn = get_db_connection(TICKS_DB)
        if not conn:
            return pd.DataFrame()
            
        query = f"""
            SELECT * 
            FROM ticks 
            ORDER BY timestamp DESC 
            LIMIT 10000
        """
        df = conn.execute(query).fetchdf()
        conn.close()
        
        # Convert timestamp to datetime
        if not df.empty:
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            
        return df
    except Exception as e:
        st.error(f"Error loading ticks: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_news_data():
    """Load news data from DuckDB Snapshot"""
    try:
        conn = get_db_connection(NEWS_DB)
        if not conn:
            return pd.DataFrame()

        query = "SELECT * FROM news ORDER BY published_at DESC LIMIT 50"
        df = conn.execute(query).fetchdf()
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()


# Main Layout
col1, col2 = st.columns([2, 1])

# Placeholder for auto-refresh
placeholder = st.empty()

# Main Loop for Dashboard
while True:
    with placeholder.container():
        # Load Data
        df_ticks = load_ticks_data()
        df_news = load_news_data()
        
        # --- Left Column: Ticks & Charts ---
        with col1:
            st.subheader("Real-time Price Engine")
            
            if not df_ticks.empty:
                # Key Metrics
                latest = df_ticks.iloc[0]
                symbols = df_ticks['symbol'].unique()
                
                # Metrics Row
                m_cols = st.columns(len(symbols))
                for idx, sym in enumerate(symbols):
                    sym_data = df_ticks[df_ticks['symbol'] == sym]
                    if not sym_data.empty:
                        last_price = sym_data.iloc[0]['price']
                        prev_price = sym_data.iloc[1]['price'] if len(sym_data) > 1 else last_price
                        delta = last_price - prev_price
                        
                        with m_cols[idx]:
                            st.metric(
                                label=sym, 
                                value=f"{last_price:,.0f} KRW", 
                                delta=f"{delta:,.0f} KRW"
                            )
                
                # Chart
                tab1, tab2 = st.tabs(["Price Chart", "Raw Data"])
                
                with tab1:
                    fig = px.line(
                        df_ticks, 
                        x='datetime', 
                        y='price', 
                        color='symbol',
                        title="Real-time Price Movement",
                        template="plotly_dark"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab2:
                    st.dataframe(df_ticks.head(20), use_container_width=True)
            else:
                st.info("Waiting for tick data...")

        # --- Right Column: News ---
        with col2:
            st.subheader("Latest News Feed")
            
            if not df_news.empty:
                for _, row in df_news.iterrows():
                    with st.expander(f"{row['title'][:50]}...", expanded=True):
                        st.caption(f"{row['source']} | {row['published']}")
                        st.write(f"[{row['title']}]({row['link']})")
                        if row['keywords']:
                            st.info(f"Tags: {row['keywords']}")
            else:
                st.info("Waiting for news data...")
                
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
        
    time.sleep(REFRESH_INTERVAL)
