import asyncio
import logging
import os
import yaml
import asyncpg
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
from datetime import datetime, timedelta

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HistoryLoader")

# Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "configs", "market_symbols.yaml")

# KIS API Config
KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")
KIS_BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")

class HistoryLoader:
    def __init__(self):
        self.db_pool = None
        self.kiss_token = None

    async def get_kis_token(self):
        """Fetch KIS REST API token with retry for rate limits"""
        import aiohttp
        url = f"{KIS_BASE_URL}/oauth2/tokenP"
        body = {
            "grant_type": "client_credentials",
            "appkey": KIS_APP_KEY,
            "appsecret": KIS_APP_SECRET
        }
        for attempt in range(3):
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=body) as resp:
                    data = await resp.json()
                    self.kiss_token = data.get("access_token")
                    if self.kiss_token:
                        logger.info(f"KIS Token initialized. (Length: {len(self.kiss_token)})")
                        return
                    else:
                        logger.warning(f"Failed to get KIS Token (Attempt {attempt+1}): {data}")
                        if "EGW00133" in str(data): # Rate limit
                            logger.info("Waiting 65s for token rate limit reset...")
                            await asyncio.sleep(65)
                        else:
                            await asyncio.sleep(5)
        logger.error("Final failure initializing KIS Token.")

    async def init_db(self):
        self.db_pool = await asyncpg.create_pool(
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        async with self.db_pool.acquire() as conn:
            # Create Candles Table
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
            # Convert to Hypertable (Dimensions: time, symbol)
            # Note: space_partitioning by symbol is optional but good for many symbols. keeping simple time for now.
            try:
                await conn.execute("SELECT create_hypertable('market_candles', 'time', if_not_exists => TRUE);")
                logger.info("Hypertable 'market_candles' ensured.")
            except Exception as e:
                logger.warning(f"Hypertable info: {e}")

    def load_config(self):
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        
        targets = []
        
        def process_region(region_key, data):
            # Indices & Leverage
            for item in data.get('indices', []) + data.get('leverage', []):
                targets.append({'symbol': item['symbol'], 'region': region_key})
            # Sectors
            for sector in data.get('sectors', {}).values():
                targets.append({'symbol': sector['etf']['symbol'], 'region': region_key})
                for stock in sector['top3']:
                    targets.append({'symbol': stock['symbol'], 'region': region_key})

        market = config.get('market_data', {})
        if 'kr' in market: process_region('kr', market['kr'])
        if 'us' in market: process_region('us', market['us'])
        
        return targets

    def fetch_data(self, target):
        symbol = target['symbol']
        region = target['region']
        
        results = []
        
        # 1. Daily Data (1 Year)
        try:
            if region == 'us':
                # yfinance
                df = yf.download(symbol, period="1y", interval="1d", progress=False)
                if not df.empty:
                    results.append(('1d', df))
            else:
                # KR (FDR)
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                df = fdr.DataReader(symbol, start=start_date)
                if not df.empty:
                    results.append(('1d', df))
        except Exception as e:
            logger.error(f"Failed Daily fetch for {symbol}: {e}")

        # 2. 1-min Data (Recent)
        try:
            if region == 'us':
                # yfinance max is usually 7 days for 1m, or 30 days? "1mo" often works for 2-5m. "max" for 1m is 7d.
                # User asked for "2 months" if possible. yfinance 1m is limited.
                # Let's try '1mo' with '15m' or '5m'? User said "1 minute".
                # yfinance limitation: 1m data is only available for last 7 days.
                # We will fetch 'max' (7d) for 1m.
                df = yf.download(symbol, period="5d", interval="1m", progress=False)
                if not df.empty:
                    results.append(('1m', df))
            else:
                # KR 1m data via KIS REST API (Max possible: ~30 blocks)
                logger.info(f"Attempting KR 1m fetch for {symbol} (Token: {bool(self.kiss_token)})")
                if self.kiss_token:
                    import requests
                    url = f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
                    headers = {
                        "content-type": "application/json; charset=utf-8",
                        "authorization": f"Bearer {self.kiss_token}",
                        "appkey": KIS_APP_KEY,
                        "appsecret": KIS_APP_SECRET,
                        "tr_id": "FHKST03010200", # Default to Stock
                        "custtype": "P"
                    }
                    # For ETFs, KIS sometimes prefers FHKSB03010200
                    # Quick heuristic: ETFs are often mixed. 
                    # If it fails, we will log.
                    
                    all_dfs = []
                    last_hour = ""
                    for i in range(10): # Fetch last 10 blocks
                        params = {
                            "FID_COND_MRKT_DIV_CODE": "J",
                            "FID_INPUT_ISCD": symbol,
                            "FID_INPUT_HOUR_1": last_hour,
                            "FID_PW_RESV_RE3": "",
                            "FID_ETC_CLS_CODE": ""
                        }
                        res = requests.get(url, headers=headers, params=params)
                        if res.status_code != 200:
                            logger.error(f"HTTP {res.status_code} for {symbol}: {res.text}")
                            break
                        data = res.json()
                        if data.get("rt_cd") == "0":
                            output = data.get("output2", [])
                            if not output: 
                                logger.info(f"Empty output2 for {symbol}")
                                break
                            df_block = pd.DataFrame(output)
                            df_block['time'] = pd.to_datetime(df_block['stck_bsop_date'] + df_block['stck_cntg_hour'], format='%Y%m%d%H%M%S')
                            all_dfs.append(df_block)
                            last_hour = output[-1]['stck_cntg_hour']
                        else:
                            # Try ETF ID if Stock ID fails with no msg
                            if i == 0 and headers["tr_id"] == "FHKST03010200":
                                logger.info(f"Retrying {symbol} with ETF ID FHKSB03010200...")
                                headers["tr_id"] = "FHKSB03010200"
                                continue 
                            logger.error(f"KIS 1m Error for {symbol} ({headers['tr_id']}): {data}")
                            break
                        import time
                        time.sleep(0.1)

                    if all_dfs:
                        df = pd.concat(all_dfs).drop_duplicates('time')
                        df = df.rename(columns={
                            'stck_oprc': 'Open',
                            'stck_hgpr': 'High',
                            'stck_lwpr': 'Low',
                            'stck_prpr': 'Close',
                            'cntg_vol': 'Volume'
                        })
                        df = df.set_index('time')
                        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
                        results.append(('1m', df))
        except Exception as e:
            logger.error(f"Failed 1m fetch for {symbol}: {e}")
            
        return results

    async def save_data(self, symbol, interval, df):
        if df.empty: return
        
        # Convert DataFrame to list of tuples
        records = []
        for index, row in df.iterrows():
            # Robustly convert index to UTC Timestamp
            ts = pd.to_datetime(index, utc=True)
            
            # Normalize columns (Lower case, handle Close/Adj Close)
            # yfinance: Open, High, Low, Close, Adj Close, Volume
            # FDR: Open, High, Low, Close, Volume, Change
            
            # Use 'Close' (Raw) or 'Adj Close'? For backtest, Adj Close is better for Day.
            # But standard OHLCv usually uses raw.
            # Let's use 'Close'.
            
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
                logger.info(f"Saved {len(records)} rows for {symbol} ({interval})")
            except Exception as e:
                logger.error(f"DB Error for {symbol}: {e}")

    async def run(self):
        await self.init_db()
        # Initialize KIS Token if keys are available
        if KIS_APP_KEY and KIS_APP_SECRET:
            await self.get_kis_token()
            
        targets = self.load_config()
        logger.info(f"Loaded {len(targets)} symbols. Starting fetch...")
        
        # Requests Session for YF to avoid 429? 
        # Actually YF creates its own session but we can try to be slower.
        import time
        
        for target in targets:
            logger.info(f"Processing {target['symbol']}...")
            data_list = await asyncio.to_thread(self.fetch_data, target)
            
            for interval, df in data_list:
                await self.save_data(target['symbol'], interval, df)
            
            # Rate Limit: Sleep 2 seconds between symbols
            time.sleep(2)
                
        logger.info("History Load Complete.")

if __name__ == "__main__":
    loader = HistoryLoader()
    asyncio.run(loader.run())
