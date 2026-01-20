import asyncio
import os
import yaml
import logging
import aiohttp
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from src.data_ingestion.price.common import KISAuthManager

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RecoverAllTicks")

SYMBOLS_FILE = "configs/kr_symbols.yaml"
OUTPUT_DIR = "data/recovery"

def load_symbols():
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
            return sorted(list(set(extract_symbols(config))))
    except Exception as e:
        logger.error(f"Failed to load symbols: {e}")
        return []

async def recover():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    symbols = load_symbols()
    auth_manager = KISAuthManager()
    token = await auth_manager.get_access_token()
    
    base_url = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
    url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": os.getenv("KIS_APP_KEY"),
        "appsecret": os.getenv("KIS_APP_SECRET"),
        "tr_id": "FHKST01010200",
        "custtype": "P"
    }

    logger.info(f"🚀 Starting tick recovery for {len(symbols)} symbols...")
    
    for symbol in symbols:
        all_ticks = []
        # Opening coverage: 09:10:00 gives the first 30 ticks
        # 09:30:00 gives another 30 ticks if needed
        for t_time in ["091000", "093000"]:
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": symbol,
                "fid_input_hour_1": t_time
            }
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, params=params) as resp:
                        data = await resp.json()
                        if data.get('rt_cd') == '0':
                            ticks = data.get('output1', [])
                            if isinstance(ticks, list):
                                all_ticks.extend(ticks)
                        else:
                            logger.warning(f"⚠️ KIS Error for {symbol} at {t_time}: {data.get('msg1')}")
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
            await asyncio.sleep(0.5) # TPS limit

        if all_ticks:
            df = pd.DataFrame(all_ticks).drop_duplicates(subset=['stck_cntg_hour'])
            output_file = f"{OUTPUT_DIR}/backfill_{symbol}_{datetime.now().strftime('%Y%m%d')}.csv"
            df.to_csv(output_file, index=False)
            logger.info(f"✅ Saved {len(df)} ticks for {symbol}")
        else:
            logger.warning(f"⚠️ No ticks found for {symbol}")
        
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(recover())
