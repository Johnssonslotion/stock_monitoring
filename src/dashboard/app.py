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

# Auto-refresh interval (in seconds)
REFRESH_INTERVAL = st.sidebar.slider("Refresh Interval (s)", 5, 60, 10)

# Database Paths
TICKS_DB = "data/ticks.duckdb"
NEWS_DB = "data/news.duckdb"

@st.cache_data(ttl=5)  # Cache for 5 seconds
def load_ticks_data(hours=1):
    """Load tick data from DuckDB"""
    try:
        if not os.path.exists(TICKS_DB):
            return pd.DataFrame()
            
        conn = duckdb.connect(TICKS_DB, read_only=True)
        # Calculate timestamp for N hours ago
        # timestamp in DB is unix timestamp (ms? no, we need to check schema)
        # In collector, we didn't specify unit, but usually APIs allow ms.
        # Let's check raw data or just load all for now limit 10000
        
        query = f"""
            SELECT * 
            FROM ticks 
            ORDER BY timestamp DESC 
            LIMIT 10000
        """
        df = conn.execute(query).fetchdf()
        conn.close()
        
        # Convert timestamp to datetime
        # Upbit timestamp is ms
        if not df.empty:
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            
        return df
    except Exception as e:
        st.error(f"Error loading ticks: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_news_data():
    """Load news data from DuckDB"""
    try:
        if not os.path.exists(NEWS_DB):
            return pd.DataFrame()
            
        conn = duckdb.connect(NEWS_DB, read_only=True)
        query = "SELECT * FROM news ORDER BY published_at DESC LIMIT 50"
        df = conn.execute(query).fetchdf()
        conn.close()
        return df
    except Exception as e:
        # Table might not exist yet
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
