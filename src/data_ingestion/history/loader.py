import asyncio
import logging
import os
import yaml
import asyncpg
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import json
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HistoryLoader")

# Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "configs", "market_symbols.yaml")
CHECKPOINT_FILE = "/app/data/history_checkpoint.json"

# KIS API Config
KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")
KIS_BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")

class SmartThrottler:
    """API Rate Limit Admin"""
    def __init__(self, max_req_per_sec=10):
        self.max_req_per_sec = max_req_per_sec
        self.timestamps = []
    
    async def acquire(self):
        now = time.time()
        # Remove timestamps older than 1 second
        self.timestamps = [t for t in self.timestamps if now - t < 1.0]
        
        if len(self.timestamps) >= self.max_req_per_sec:
            sleep_time = 1.0 - (now - self.timestamps[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            # Re-check after sleep
            return await self.acquire()
            
        self.timestamps.append(time.time())

class CheckpointManager:
    """Save/Load progress"""
    def __init__(self, filepath=CHECKPOINT_FILE):
        self.filepath = filepath
        self.data = self.load()
        
    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
        return {"daily_done": [], "minute_last_date": {}}

    def save(self):
        try:
            # Ensure dir exists
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def is_daily_done(self, symbol):
        return symbol in self.data["daily_done"]

    def mark_daily_done(self, symbol):
        if symbol not in self.data["daily_done"]:
            self.data["daily_done"].append(symbol)
            self.save()

class HistoryLoader:
    def __init__(self):
        self.db_pool = None
        self.kiss_token = None
        self.throttler = SmartThrottler(max_req_per_sec=10)
        self.checkpoint = CheckpointManager()

    async def get_kis_token(self):
        """Fetch KIS REST API token"""
        import aiohttp
        url = f"{KIS_BASE_URL}/oauth2/tokenP"
        body = {
            "grant_type": "client_credentials",
            "appkey": KIS_APP_KEY,
            "appsecret": KIS_APP_SECRET
        }
        await self.throttler.acquire()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body) as resp:
                data = await resp.json()
                self.kiss_token = data.get("access_token")
                if self.kiss_token:
                    logger.info(f"KEYS INITIALIZED: {KIS_APP_KEY[:5]}... (Token Len: {len(self.kiss_token)})")
                else:
                    logger.error(f"Failed to get KIS Token: {data}")
                    raise Exception("KIS Token Init Failed")

    async def init_db(self):
        self.db_pool = await asyncpg.create_pool(
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS market_candles (
                    time TIMESTAMPTZ NOT NULL,
                    symbol TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    open DOUBLE PRECISION,
                    high DOUBLE PRECISION,
                    low DOUBLE PRECISION,
                    close DOUBLE PRECISION,
                    volume DOUBLE PRECISION
                );
            """)
            try:
                await conn.execute("SELECT create_hypertable('market_candles', 'time', if_not_exists => TRUE);")
            except Exception:
                pass

    def load_targets(self):
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        
        targets = []
        # KR Market Only for KIS Logic
        market = config.get('market_data', {})
        if 'kr' in market:
            data = market['kr']
            for item in data.get('indices', []) + data.get('leverage', []):
                targets.append({'symbol': item['symbol'], 'region': 'kr'})
            for sector in data.get('sectors', {}).values():
                targets.append({'symbol': sector['etf']['symbol'], 'region': 'kr'})
                for stock in sector['top3']:
                    targets.append({'symbol': stock['symbol'], 'region': 'kr'})
        return targets

    async def fetch_daily_2years(self, symbol):
        if self.checkpoint.is_daily_done(symbol):
            logger.info(f"Creating Daily for {symbol} (Skipping - Already Done)")
            return

        logger.info(f"Fetching Daily 2Y for {symbol}...")
        try:
            start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
            # Use threading for sync call
            df = await asyncio.to_thread(fdr.DataReader, symbol, start_date)
            
            if not df.empty:
                await self.save_data(symbol, '1d', df)
                self.checkpoint.mark_daily_done(symbol)
                logger.info(f"Saved {len(df)} daily rows for {symbol}")
            else:
                logger.warning(f"No daily data found for {symbol}")
                
        except Exception as e:
            logger.error(f"Daily fetch failed for {symbol}: {e}")

    async def fetch_minute_backfill(self, symbol):
        import requests
        url = f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.kiss_token}",
            "appkey": KIS_APP_KEY,
            "appsecret": KIS_APP_SECRET,
            "tr_id": "FHKST03010200",
            "custtype": "P"
        }
        
        all_dfs = []
        last_hour = "" 
        
        for i in range(20): 
            await self.throttler.acquire()
            
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_HOUR_1": last_hour,
                "FID_PW_RESV_RE3": "",
                "FID_ETC_CLS_CODE": ""
            }
            
            def _req():
                return requests.get(url, headers=headers, params=params)
                
            res = await asyncio.to_thread(_req)
            
            if res.status_code != 200:
                logger.error(f"KIS Minute Req Failed: {res.text}")
                break
                
            data = res.json()
            if data.get("rt_cd") != "0":
                if i == 0 and headers["tr_id"] == "FHKST03010200":
                    headers["tr_id"] = "FHKSB03010200"
                    continue
                break
            
            output = data.get("output2", [])
            if not output:
                break
                
            df_block = pd.DataFrame(output)
            df_block['time'] = pd.to_datetime(df_block['stck_bsop_date'] + df_block['stck_cntg_hour'], format='%Y%m%d%H%M%S')
            all_dfs.append(df_block)
            last_hour = output[-1]['stck_cntg_hour']
            
        if all_dfs:
            df = pd.concat(all_dfs).drop_duplicates('time')
            df = df.rename(columns={'stck_oprc': 'Open', 'stck_hgpr': 'High', 'stck_lwpr': 'Low', 'stck_prpr': 'Close', 'cntg_vol': 'Volume'})
            df = df.set_index('time')
            await self.save_data(symbol, '1m', df)
            logger.info(f"Backfilled {len(df)} minute rows for {symbol} (Recent)")

    async def save_data(self, symbol, interval, df):
        if df.empty: return
        records = []
        for index, row in df.iterrows():
            ts = pd.to_datetime(index, utc=True)
            o = row.get('Open', 0)
            h = row.get('High', 0)
            l = row.get('Low', 0)
            c = row.get('Close', 0)
            v = row.get('Volume', 0)
            records.append((ts, symbol, interval, float(o), float(h), float(l), float(c), float(v)))

        async with self.db_pool.acquire() as conn:
            try:
                await conn.copy_records_to_table(
                    'market_candles',
                    records=records,
                    columns=['time', 'symbol', 'interval', 'open', 'high', 'low', 'close', 'volume']
                )
            except Exception as e:
                logger.error(f"DB Save Error {symbol}: {e}")

    async def run(self):
        await self.init_db()
        if KIS_APP_KEY and KIS_APP_SECRET:
            try:
                await self.get_kis_token()
            except Exception as e:
                logger.error(f"KIS Init Failed: {e}")
            
        targets = self.load_targets()
        logger.info(f"Target Symbols (KR Only): {len(targets)}")
        
        for idx, target in enumerate(targets):
            symbol = target['symbol']
            logger.info(f"[{idx+1}/{len(targets)}] Processing {symbol}...")
            
            # 1. Daily Backfill (Priority)
            await self.fetch_daily_2years(symbol)
            
            # 2. Minute Backfill (Best Effort)
            if self.kiss_token:
                await self.fetch_minute_backfill(symbol)
                
            await asyncio.sleep(0.5)

        logger.info("🎉 2-Year Backfill & Recovery Complete!")

if __name__ == "__main__":
    loader = HistoryLoader()
    asyncio.run(loader.run())
