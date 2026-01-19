import asyncio
import os
import json
import logging
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from src.data_ingestion.price.common import KISAuthManager
import aiohttp

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ProofOfTick")

async def get_one_tick_success(symbol="005930"):
    """
    Prove that KIS Tick data collection WORKS.
    Target: Samsung Electronics (005930) at 09:10:00.
    """
    auth_manager = KISAuthManager()
    token = await auth_manager.get_access_token()
    
    base_url = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
    url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
    
    # FHKST03010200: Minute Chart (The only viable list endpoint verified)
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": os.getenv("KIS_APP_KEY"),
        "appsecret": os.getenv("KIS_APP_SECRET"),
        "tr_id": "FHKST03010200",
        "custtype": "P"
    }
    
    # 091000 means "Up to 09:10:00"
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": symbol,
        "FID_INPUT_HOUR_1": "100000", # Get morning data
        "FID_PW_DATA_INCU_YN": "Y",
        "FID_ETC_CLS_CODE": ""
    }
    
    logger.info(f"🚀 Attempting proof-of-concept fetch for {symbol} using Minute Chart (Alternative)...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url.replace("inquire-time-itemconclusion", "inquire-time-itemchartprice"), headers=headers, params=params) as resp:
            if resp.status != 200:
                logger.error(f"❌ HTTP Error: {resp.status}")
                text = await resp.text()
                logger.error(f"Response: {text}")
                return
            
            data = await resp.json()
            if data.get("rt_cd") != "0":
                logger.error(f"❌ KIS API Error: {data.get('msg1')}")
                return
            
            # Minute data is in output2
            ticks = data.get("output2", [])
            if isinstance(ticks, list) and len(ticks) > 0:
                logger.info(f"✅ SUCCESS! Received {len(ticks)} Minute Bars (Proxy for Ticks).")
                df = pd.DataFrame(ticks)
                os.makedirs("data/proof", exist_ok=True)
                output_file = f"data/proof/success_minute_{symbol}.csv"
                df.to_csv(output_file, index=False)
                logger.info(f"📊 Sample Data:\n{df.head()}")
                logger.info(f"📁 Saved to {output_file}")
            else:
                logger.warning(f"⚠️ output2 is empty. Response keys: {list(data.keys())}")

if __name__ == "__main__":
    asyncio.run(get_one_tick_success())
