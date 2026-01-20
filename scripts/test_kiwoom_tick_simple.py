
import asyncio
import aiohttp
import os
import logging
import sys
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestKiwoomTick")

async def test_tick():
    token_url = "https://api.kiwoom.com/oauth2/token"
    api_url = "https://api.kiwoom.com/api/dostk/chart"
    
    app_key = os.getenv("KIWOOM_APP_KEY")
    app_secret = os.getenv("KIWOOM_APP_SECRET")
    
    async with aiohttp.ClientSession() as session:
        # 1. Get Token
        payload = {
            "grant_type": "client_credentials",
            "appkey": app_key,
            "secretkey": app_secret
        }
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0"
        }
        async with session.post(token_url, json=payload, headers=headers) as resp:
            data = await resp.json()
            token = data.get("token")
            logger.info(f"Token: {token[:10]}...")

        # 2. Get Tick
        headers = {
            "api-id": "ka10079",
            "authorization": f"Bearer {token}",
            "content-yn": "N",
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0"
        }
        # Request for 005930 (Samsung Electronics)
        payload = {
            "stk_cd": "005930",
            "tic_scope": "1", 
            "upd_stkpc_tp": "1"
        }
        
        logger.info("Sending request...")
        async with session.post(api_url, json=payload, headers=headers) as resp:
            logger.info(f"Status: {resp.status}")
            text = await resp.text()
            if resp.status == 200:
                logger.info(f"Response (Prefix): {text[:200]}")
            else:
                logger.error(f"Error: {text}")

if __name__ == "__main__":
    asyncio.run(test_tick())
