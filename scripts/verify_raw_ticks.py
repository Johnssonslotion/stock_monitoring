import asyncio
import os
import json
import logging
from dotenv import load_dotenv
from src.data_ingestion.price.common import KISAuthManager
import aiohttp

# Load Environment
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyTicks")

async def verify_raw_ticks(symbol="005930"):
    auth_manager = KISAuthManager()
    token = await auth_manager.get_access_token()
    
    base_url = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
    url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": os.getenv("KIS_APP_KEY"),
        "appsecret": os.getenv("KIS_APP_SECRET"),
        "tr_id": "FHKST01010400",
        "custtype": "P"
    }
    
    # Try 09:10:00 to get opening data
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": symbol,
        "fid_input_hour_1": "091000"
    }
    
    logger.info(f"🚀 Fetching Ticks for {symbol} at 09:10:00...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            logger.info(f"Status: {resp.status}")
            logger.info(f"Response Keys: {list(data.keys())}")
            
            if "output1" in data:
                output1 = data["output1"]
                if isinstance(output1, list) and len(output1) > 0:
                    logger.info(f"✅ output1 is a LIST with {len(output1)} items.")
                    logger.info(f"FULL Sample Item: {json.dumps(output1[0], indent=2)}")
                else:
                    logger.warning(f"⚠️ output1 is NOT a list or is empty. Value: {output1}")
                    logger.info(f"Full Response: {json.dumps(data, indent=2)}")
            
            if "output2" in data:
                logger.info(f"output2 type: {type(data['output2'])}")
                if isinstance(data['output2'], dict):
                    logger.info(f"output2 keys: {list(data['output2'].keys())}")

if __name__ == "__main__":
    asyncio.run(verify_raw_ticks())
