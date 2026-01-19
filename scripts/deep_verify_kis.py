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
logger = logging.getLogger("DeepVerify")

async def deep_verify(symbol="005930"):
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
    
    # Try different times. Some times might return nothing if it's too early or after hours in certain contexts.
    # But 1월 19일 09:10:00 should work.
    test_times = ["090500", "091000", "093000", "140000"]
    
    async with aiohttp.ClientSession() as session:
        for t_time in test_times:
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": symbol,
                "fid_input_hour_1": t_time
            }
            logger.info(f"🔍 Testing {symbol} at {t_time} with FHKST01010200...")
            async with session.get(url, headers=headers, params=params) as resp:
                data = await resp.json()
                logger.info(f"   Response rt_cd: {data.get('rt_cd')}, msg: {data.get('msg1')}")
                
                for out_key in ["output1", "output2"]:
                    val = data.get(out_key)
                    if isinstance(val, list) and len(val) > 0:
                        logger.info(f"   🌟 SUCCESS! {out_key} is a list with {len(val)} items.")
                        logger.info(f"   First Item: {val[0]}")
                        return True
                    elif isinstance(val, dict):
                        logger.info(f"   💡 {out_key} is a dict with keys: {list(val.keys())}")
            await asyncio.sleep(0.5)
            
    return False

if __name__ == "__main__":
    asyncio.run(deep_verify())
