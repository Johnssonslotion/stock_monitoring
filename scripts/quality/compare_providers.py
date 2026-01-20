import asyncio
import aiohttp
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CompareProviders")

# KIS Config
KIS_BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")

# Kiwoom Config
KIWOOM_BASE_URL = "https://api.kiwoom.com"
KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY")
KIWOOM_APP_SECRET = os.getenv("KIWOOM_APP_SECRET")
KIWOOM_TOKEN = None

async def refresh_kiwoom_token():
    url = f"{KIWOOM_BASE_URL}/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "appkey": KIWOOM_APP_KEY,
        "secretkey": KIWOOM_APP_SECRET
    }
    headers = {"Content-Type": "application/json; charset=UTF-8", "User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            data = await resp.json()
            return data.get("token")

from src.data_ingestion.price.common import KISAuthManager

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CompareProviders")

# KIS Config
KIS_BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")
auth_manager = KISAuthManager()

async def fetch_kis_minute_data(symbol: str, token: str):
    """Fetch last 10 minutes of minute candles from KIS (Aggregated from Ticks)"""
    url = f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        "tr_id": "FHKST01010300",
        "custtype": "P"
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": symbol,
        "FID_INPUT_HOUR_1": "" # Most recent
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            logger.info(f"KIS Data: {data}")
            if resp.status != 200:
                logger.error(f"KIS API Error: {resp.status} - {data}")
                return None
            ticks = data.get("output", []) # Corrected key
            logger.info(f"KIS returned {len(ticks)} ticks.")
            if not ticks: 
                logger.warning(f"No ticks in KIS response: {data}")
                return pd.DataFrame()
            
            df = pd.DataFrame(ticks)
            # stck_cntg_hour (HHMMSS), stck_prpr, cntg_vol
            df['time'] = df['stck_cntg_hour'].str[:4]
            # Aggregation
            agg = df.groupby('time').agg({
                'stck_prpr': ['first', 'max', 'min', 'last'],
                'cntg_vol': 'sum'
            }).reset_index()
            agg.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
            return agg.head(10)

async def fetch_kiwoom_minute_data(symbol: str):
    """Fetch last 10 minutes of ticks from Kiwoom (ka10079) and aggregate"""
    url = f"{KIWOOM_BASE_URL}/api/dostk/chart"
    headers = {
        "authorization": f"Bearer {KIWOOM_TOKEN}",
        "api-id": "ka10079", # Tick chart
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json;charset=UTF-8",
        "cont-yn": "N"
    }
    body = {
        "stk_cd": symbol,
        "tic_scope": "1", # 1 tick
        "upd_stkpc_tp": "0"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=body) as resp:
            data = await resp.json()
            if resp.status != 200:
                logger.error(f"Kiwoom API Error: {resp.status} - {data}")
                return None
            ticks = data.get("stck_tic_chart_qry", [])
            logger.info(f"Kiwoom returned {len(ticks)} items.")
            if not ticks: return pd.DataFrame()
            
            df = pd.DataFrame(ticks)
            # cntr_tm (HHMMSS), curr_prc, tr_vol
            df['time'] = df['cntr_tm'].str[:4]
            # Aggregation
            agg = df.groupby('time').agg({
                'curr_prc': ['first', 'max', 'min', 'last'],
                'tr_vol': 'sum'
            }).reset_index()
            agg.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
            return agg.head(10)

async def compare():
    global KIWOOM_TOKEN
    symbol = "005930" # Samsung
    logger.info(f"Comparing KIS vs Kiwoom for {symbol}...")
    
    token = await auth_manager.get_access_token()
    if not token:
        logger.error("Failed to get KIS token")
        return

    KIWOOM_TOKEN = await refresh_kiwoom_token()
    if not KIWOOM_TOKEN:
        logger.error("Failed to get Kiwoom token")
        return

    kis_df = await fetch_kis_minute_data(symbol, token)
    kiwoom_df = await fetch_kiwoom_minute_data(symbol)
    
    if kis_df is None: logger.error("KIS data is None")
    if kiwoom_df is None: logger.error("Kiwoom data is None")

    if (kis_df is not None and kis_df.empty) or (kiwoom_df is not None and kiwoom_df.empty):
        logger.warning(f"Empty data check: KIS empty={kis_df.empty if kis_df is not None else 'N/A'}, Kiwoom empty={kiwoom_df.empty if kiwoom_df is not None else 'N/A'}")
        return

    # Normalize time format if needed (both are HHMMSS)
    kis_df['time'] = kis_df['time'].str[:4] # Compare only HHMM for safety
    kiwoom_df['time'] = kiwoom_df['time'].str[:4]
    
    # Merge on time
    merged = pd.merge(kis_df, kiwoom_df, on='time', suffixes=('_kis', '_kiwoom'))
    
    if merged.empty:
        logger.error("No overlapping time windows found.")
        print("KIS Times:", kis_df['time'].tolist())
        print("Kiwoom Times:", kiwoom_df['time'].tolist())
        return

    logger.info(f"Found {len(merged)} overlapping windows.")
    
    # Comparison
    merged['price_match'] = (merged['close_kis'].astype(float) == merged['close_kiwoom'].astype(float))
    merged['vol_diff_pct'] = abs(merged['volume_kis'].astype(float) - merged['volume_kiwoom'].astype(float)) / merged['volume_kis'].astype(float) * 100
    
    print("\n" + "="*60)
    print("📊 PROVIDER COMPARISON REPORT")
    print("="*60)
    print(merged[['time', 'close_kis', 'close_kiwoom', 'price_match', 'vol_diff_pct']])
    
    match_rate = merged['price_match'].mean() * 100
    avg_vol_diff = merged['vol_diff_pct'].mean()
    
    print("-" * 60)
    print(f"✅ Price Match Rate: {match_rate:.2f}%")
    print(f"📉 Avg Volume Diff:  {avg_vol_diff:.2f}%")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(compare())
