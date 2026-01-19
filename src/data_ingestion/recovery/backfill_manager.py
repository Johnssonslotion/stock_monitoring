import asyncio
import os
import yaml
import logging
from datetime import datetime
import aiohttp
import pandas as pd
from typing import List, Dict
from dotenv import load_dotenv

# Load Environment Variables FIRST
load_dotenv()

from src.data_ingestion.price.common import KISAuthManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BackfillManager")

# Constants
BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
OUTPUT_DIR = "data/recovery"
SYMBOLS_FILE = "configs/kr_symbols.yaml"

class BackfillManager:
    def __init__(self):
        self.auth_manager = KISAuthManager()
        self.symbols = self._load_symbols()
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def _load_symbols(self) -> List[str]:
        def extract_symbols(data):
            symbols = []
            if isinstance(data, dict):
                for k, v in data.items():
                    if k == 'symbol' and isinstance(v, str):
                        symbols.append(v)
                    else:
                        symbols.extend(extract_symbols(v))
            elif isinstance(data, list):
                for item in data:
                    symbols.extend(extract_symbols(item))
            return symbols

        try:
            with open(SYMBOLS_FILE, 'r') as f:
                config = yaml.safe_load(f)
                all_symbols = extract_symbols(config)
                return sorted(list(set(all_symbols))) # Unique and sorted
        except Exception as e:
            logger.error(f"Failed to load symbols: {e}")
            return []

    async def fetch_ticks(self, symbol: str, token: str):
        """Fetch minute candles for today using inquire-time-itemchartprice (TR: FHKST03010200)"""
        # Note: User agreed to use Minute Candles as Tick Proxy for recovery
        base_url = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
        url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
        
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": os.getenv("KIS_APP_KEY"),
            "appsecret": os.getenv("KIS_APP_SECRET"),
            "tr_id": "FHKST03010200", 
            "custtype": "P"
        }
        
        # Backward search from market close (15:30) to open (09:00)
        # KIS returns 30 items per call. We need to cover ~390 minutes.
        # 153000 -> 1500~1530
        # 150000 -> 1430~1500
        # ...
        # 093000 -> 0900~0930
        target_times = [
            "153000", "150000", "143000", "140000", 
            "133000", "130000", "123000", "120000", 
            "113000", "110000", "103000", "100000", 
            "093000", "090000" # Just in case
        ]
        all_items = []

        async with aiohttp.ClientSession() as session:
            for t_time in target_times:
                params = {
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol,
                    "FID_INPUT_HOUR_1": t_time,
                    "FID_PW_DATA_INCU_YN": "Y", # Include password data? No, this is PW_DATA? Usually Y/N
                    "FID_ETC_CLS_CODE": ""
                }
                try:
                    async with session.get(url, headers=headers, params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get('rt_cd') != '0':
                                logger.error(f"❌ KIS API Error for {symbol} at {t_time}: {data.get('msg1')}")
                                continue
                                
                            # Candles are in output2
                            items = data.get('output2', [])
                            if isinstance(items, list) and len(items) > 0:
                                all_items.extend(items)
                                logger.info(f"   - Fetched {len(items)} minute bars at {t_time} for {symbol}")
                            else:
                                logger.debug(f"   - [{symbol}] {t_time} output2 is empty.")
                        else:
                            logger.error(f"Failed to fetch {symbol} at {t_time}: {resp.status}")
                except Exception as e:
                    logger.error(f"Error fetching {symbol}: {e}")
                
                await asyncio.sleep(0.5) # TPS limit

        if not all_items:
            logger.warning(f"⚠️ No data found for {symbol}")
            return

        # Deduplicate and Save
        df = pd.DataFrame(all_items).drop_duplicates(subset=['stck_cntg_hour'])
        if not df.empty:
            df = df.sort_values('stck_cntg_hour')
            output_file = f"{OUTPUT_DIR}/backfill_minute_{symbol}_{datetime.now().strftime('%Y%m%d')}.csv"
            df.to_csv(output_file, index=False)
            logger.info(f"✅ Saved {len(df)} minute rows for {symbol} to {output_file}")

    async def run(self):
        logger.info(f"🚀 Starting Backfill for {len(self.symbols)} symbols...")
        
        token = None
        max_retries = 3
        for i in range(max_retries):
            try:
                token = await self.auth_manager.get_access_token()
                if token: break
            except Exception as e:
                if "EGW00133" in str(e):
                    wait_time = 65
                    logger.warning(f"⏳ KIS Token Limit (EGW00133). Waiting {wait_time}s... (Retry {i+1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    raise e
        
        if not token:
            logger.error("❌ Failed to obtain KIS token after retries.")
            return
        
        for symbol in self.symbols:
            await self.fetch_ticks(symbol, token)
            await asyncio.sleep(1) # KIS TPS is sensitive

if __name__ == "__main__":
    manager = BackfillManager()
    asyncio.run(manager.run())
