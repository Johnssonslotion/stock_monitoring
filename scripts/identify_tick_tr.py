import asyncio
import os
import json
import logging
import aiohttp
from dotenv import load_dotenv
from src.data_ingestion.price.common import KISAuthManager

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TRScanner")

async def scan_trs(symbol="005930", t_time="140000"):
    auth_manager = KISAuthManager()
    token = await auth_manager.get_access_token()
    
    base_url = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
    url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
    
    # Candidate TR IDs for "Time Item Conclusion" or related
    # 01010100: Price?
    # 01010200: Conclusion? (Gave Orderbook?)
    # 01010300: ?
    # 01010400: Orderbook?
    # 01010500: ?
    # 01010600: ?
    candidate_trs = [
        "FHKST01010100", 
        "FHKST01010200", 
        "FHKST01010300", 
        "FHKST01010400",
        "FHKST01010500",
        "FHKST01010600"
    ]
    
    async with aiohttp.ClientSession() as session:
        for tr_id in candidate_trs:
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "authorization": f"Bearer {token}",
                "appkey": os.getenv("KIS_APP_KEY"),
                "appsecret": os.getenv("KIS_APP_SECRET"),
                "tr_id": tr_id,
                "custtype": "P"
            }
            
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": symbol,
                "fid_input_hour_1": t_time
            }
            
            logger.info(f"🔍 Testing TR ID: {tr_id}")
            try:
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status != 200:
                        logger.warning(f"   ❌ HTTP {resp.status}")
                        continue
                        
                    data = await resp.json()
                    rt_cd = data.get('rt_cd')
                    msg = data.get('msg1')
                    logger.info(f"   Status: {rt_cd} ({msg})")
                    
                    found_list = False
                    for out_key in ["output1", "output2", "output3"]:
                        val = data.get(out_key)
                        if isinstance(val, list) and len(val) > 0:
                            logger.info(f"   🌟 {out_key} is a LIST with {len(val)} items!")
                            sample = val[0] # First item
                            keys = list(sample.keys()) if isinstance(sample, dict) else str(sample)
                            logger.info(f"      Keys: {keys}")
                            
                            # Check for Tick specific keys
                            if "stck_cntg_hour" in keys and "stck_prpr" in keys:
                                logger.info("      ✅ FOUND TICK DATA CANDIDATE!")
                            
                            found_list = True
                        elif isinstance(val, dict):
                            logger.info(f"   ℹ️ {out_key} is a DICT. Keys: {list(val.keys())[:5]}...")
                        else:
                            pass # Empty or None
                            
                    if not found_list:
                        logger.warning("   ⚠️ No list found in outputs.")
                        
            except Exception as e:
                logger.error(f"Error scanning {tr_id}: {e}")
                
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(scan_trs())
