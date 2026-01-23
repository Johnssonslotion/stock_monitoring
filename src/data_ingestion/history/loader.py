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

# RFC-009: Centralized API Rate Limiting
from src.api_gateway.rate_limiter import gatekeeper

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HistoryLoader")

# Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "configs")
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

    def get_max_req_per_sec(self):
        return self.max_req_per_sec

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
        # [RFC-009] SmartThrottler 제거, gatekeeper로 중앙 집중 Rate Limiting
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
        """[ISSUE-036] 필수 테이블 존재 여부 검증 (DDL은 migrations/에서 관리)"""
        self.db_pool = await asyncpg.create_pool(
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        async with self.db_pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'market_candles')"
            )
            if not exists:
                logger.error("CRITICAL: Table 'market_candles' not found. Please run 'make migrate-up' first.")
                raise RuntimeError("Database schema incomplete: table 'market_candles' missing.")
            
            logger.info("Database schema verification completed (SSoT: market_candles).")

    def load_targets(self):
        targets = []
        # KR
        kr_path = os.path.join(CONFIG_DIR, "kr_symbols.yaml")
        if os.path.exists(kr_path):
            with open(kr_path, "r") as f:
                config = yaml.safe_load(f)
                symbols_data = config.get('symbols', {})
                # Flatten symbols from indices, leverage, sectors
                flat = []
                for k in ['indices', 'leverage']:
                    flat.extend(symbols_data.get(k, []))
                for sector in symbols_data.get('sectors', {}).values():
                    if 'etf' in sector: flat.append(sector['etf'])
                    flat.extend(sector.get('top3', []))
                
                for item in flat:
                    targets.append({'symbol': item['symbol'], 'region': 'kr'})

        # US
        us_path = os.path.join(CONFIG_DIR, "us_symbols.yaml")
        if os.path.exists(us_path):
            with open(us_path, "r") as f:
                config = yaml.safe_load(f)
                symbols_data = config.get('symbols', {})
                flat = []
                for k in ['indices', 'leverage']:
                    flat.extend(symbols_data.get(k, []))
                for sector in symbols_data.get('sectors', {}).values():
                    if 'etf' in sector: flat.append(sector['etf'])
                    flat.extend(sector.get('top3', []))
                
                for item in flat:
                    targets.append({'symbol': item['symbol'], 'region': 'us'})
        
        return targets

    async def get_last_date(self, symbol, interval='1d'):
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT MAX(time) FROM market_candles WHERE symbol = $1 AND interval = $2",
                symbol, interval
            )
            return row[0] if row else None

    async def fetch_daily_data(self, symbol, region):
        """Fetch Daily data (Initial 2Y or Sync)"""
        last_date = await self.get_last_date(symbol, '1d')
        
        if last_date:
            # Sync mode: from last_date to today
            # If last_date is today, skip
            if last_date.date() >= datetime.now().date():
                logger.info(f"Daily for {symbol} is up to date ({last_date.date()})")
                return
            start_date_str = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
            logger.info(f"Syncing Daily for {symbol} from {start_date_str}...")
        else:
            # Full mode: last 2 years
            start_date_str = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
            logger.info(f"Fetching Initial 2Y Daily for {symbol}...")

        try:
            # fdr.DataReader usually works with symbol directly for KR.
            # US symbols might need special handling.
            fetch_symbol = symbol
            if region == 'us':
                # US symbols: AAPL, NVDA etc work with fdr.
                pass
            
            df = await asyncio.to_thread(fdr.DataReader, fetch_symbol, start_date_str)
            
            if not df.empty:
                await self.save_data(symbol, '1d', df)
                logger.info(f"Saved {len(df)} daily rows for {symbol}")
            else:
                logger.warning(f"No daily data found for {symbol} since {start_date_str}")
                
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
            # RFC-009: Use gatekeeper for centralized rate limiting
            if not await gatekeeper.wait_acquire("KIS", timeout=10.0):
                logger.warning("Rate limit exceeded for KIS API, skipping...")
                continue
            
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

    async def fetch_us_minute_backfill(self, symbol):
        """
        US Minute Backfill Strategy:
        1. Try KIS API (HHDFS76200200) - Consistent with real-time
        2. Fallback to yfinance - Robustness
        """
        success = await self._fetch_us_minute_kis(symbol)
        if not success:
            logger.warning(f"⚠️ KIS Backfill failed for {symbol}. Falling back to yfinance...")
            await self._fetch_us_minute_kf(symbol)

    async def _fetch_us_minute_kis(self, symbol):
        import requests
        url = f"{KIS_BASE_URL}/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice"
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.kiss_token}",
            "appkey": KIS_APP_KEY,
            "appsecret": KIS_APP_SECRET,
            "tr_id": "HHDFS76200200",
            "custtype": "P"
        }
        
        # KIS US symbol might need exchange code (e.g. NASD, NYSE, AMEX)
        # Assuming typical major stocks are NAS/NYS.
        # Simple lookup or trial?
        # For now, let's try 'NAS' first (most tech stocks) or 'NYS'.
        # Actually KIS uses specific exchange codes: NAS, NYS, AMS.
        # We need a mapper or Try-Error.
        exchanges = ["NAS", "NYS", "AMS"] 
        
        df_final = pd.DataFrame()
        
        for exch in exchanges:
            await self.throttler.acquire()
            params = {
                "AUTH": "",
                "EXCD": exch,
                "SYMB": symbol,
                "NMIN": "1", # 1 minute
                "PINC": "1", # 1 means no gap?
                "NEXT": "",  # Next key
                "NREC": "120", # Max 120?
                "FILL": "",
                "KEYB": ""
            }
            
            def _req():
                return requests.get(url, headers=headers, params=params)
            
            res = await asyncio.to_thread(_req)
            data = res.json()
            
            if data.get("rt_cd") == "0":
                output2 = data.get("output2", [])
                if output2:
                    df = pd.DataFrame(output2)
                    # KIS US format: kymd(date), khms(time), last(close), open, high, low, svol(vol)
                    # Time is local or KST? Typically KST or Local.
                    # US market in KST: 22:30 ~ 05:00.
                    # kymd: 20240112, khms: 050000
                    df['time'] = pd.to_datetime(df['kymd'] + df['khms'], format='%Y%m%d%H%M%S')
                    
                    # Convert column names
                    df = df.rename(columns={
                        'open': 'Open', 'high': 'High', 'low': 'Low', 'last': 'Close', 'svol': 'Volume'
                    })
                    df = df[['time', 'Open', 'High', 'Low', 'Close', 'Volume']]
                    df_final = df
                    break # Success
            else:
                 logger.debug(f"KIS Backfill Debug {symbol}/{exch}: {data.get('msg1')}")
        
        if not df_final.empty:
            df_final.set_index('time', inplace=True)
            # Remove duplicated index just in case
            df_final = df_final[~df_final.index.duplicated(keep='first')]
            await self.save_data(symbol, '1m', df_final)
            logger.info(f"✅ KIS US Backfill success: {symbol} ({len(df_final)} rows)")
            return True
            
        return False

    async def _fetch_us_minute_kf(self, symbol):
        """Fallback using yfinance"""
        try:
            # yfinance creates a new thread for download usually
            df = await asyncio.to_thread(
                yf.download, 
                tickers=symbol, 
                period="5d", # Max for 1m is 7d usually
                interval="1m", 
                progress=False,
                auto_adjust=False # We want raw OHLC
            )
            
            if not df.empty:
                # yfinance returns MultiIndex if 1 symbol? No, usually simple index if 1 symbol.
                # Columns: Open, High, Low, Close, Adj Close, Volume
                # Timezone: localized to US/Eastern usually.
                
                # Check index timezone
                if df.index.tz is None:
                    # Assume NYC
                    df.index = df.index.tz_localize('America/New_York')
                
                # Convert to UTC for DB consistency
                df.index = df.index.tz_convert('UTC')
                
                await self.save_data(symbol, '1m', df)
                logger.info(f"✅ yfinance Backfill success: {symbol} ({len(df)} rows)")
                return True
        except Exception as e:
            logger.error(f"yfinance fallback failed for {symbol}: {e}")
            
        return False

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
                # [Fix] Filter out duplicates to prevent batch failure
                last_time = await self.get_last_date(symbol, interval)
                if last_time:
                     # Ensure timezone awareness (UTC)
                    if last_time.tzinfo is None:
                        last_time = last_time.replace(tzinfo=datetime.timezone.utc)
                    
                    original_len = len(df)
                    df = df[df.index > last_time]
                    if len(df) < original_len:
                        logger.info(f"Filtered {original_len - len(df)} duplicate rows for {symbol} (Last: {last_time})")
                
                if df.empty:
                    logger.info(f"No new data to save for {symbol}")
                    return

                # Re-generate records after filtering (RFC-009: source_type 추가)
                records = []
                # [Ground Truth Policy] REST API 분봉 = 참값
                source_type = 'REST_API_KIS'
                for index, row in df.iterrows():
                    ts = pd.to_datetime(index, utc=True)
                    o = row.get('Open', 0)
                    h = row.get('High', 0)
                    l = row.get('Low', 0)
                    c = row.get('Close', 0)
                    v = row.get('Volume', 0)
                    records.append((ts, symbol, interval, float(o), float(h), float(l), float(c), float(v), source_type))

                await conn.copy_records_to_table(
                    'market_candles',
                    records=records,
                    columns=['time', 'symbol', 'interval', 'open', 'high', 'low', 'close', 'volume', 'source_type']
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
            region = target['region']
            logger.info(f"[{idx+1}/{len(targets)}] Processing {symbol} ({region})...")
            
            # 1. Daily Sync (Incremental)
            await self.fetch_daily_data(symbol, region)
            
            # 2. Minute Backfill (KR Only for now via KIS)
            if region == 'kr' and self.kiss_token:
                await self.fetch_minute_backfill(symbol)
            elif region == 'us':
                # US Backfill (Hybrid)
                if self.kiss_token:
                    await self.fetch_us_minute_backfill(symbol)
                else:
                    # Even if KIS token missing, try yfinance
                    await self._fetch_us_minute_kf(symbol)
                
            # Extra sleep for US symbols to avoid 429
            sleep_time = 2.0 if region == 'us' else 0.5
            await asyncio.sleep(sleep_time)

        logger.info("🎉 2-Year Backfill & Recovery Complete!")

if __name__ == "__main__":
    loader = HistoryLoader()
    asyncio.run(loader.run())
