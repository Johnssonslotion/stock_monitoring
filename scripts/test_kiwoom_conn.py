import asyncio
import os
import json
import logging
import sys
import traceback
from dotenv import load_dotenv
import aiohttp

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("KiwoomTest")

# .env.backtest 로드
load_dotenv(".env.backtest")

KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY")
KIWOOM_APP_SECRET = os.getenv("KIWOOM_APP_SECRET")
KIWOOM_MOCK = os.getenv("KIWOOM_MOCK", "True").lower() == "true"

# Domain Selection
BASE_DOMAIN = "mockapi.kiwoom.com" if KIWOOM_MOCK else "api.kiwoom.com"
REST_URL = f"https://{BASE_DOMAIN}/oauth2/token"
WS_URL = f"wss://{BASE_DOMAIN}:10000/api/dostk/websocket"

async def get_access_token(session):
    """REST API를 통해 Access Token 발급"""
    
    # Try using 'secretkey' and standard JSON
    payload = {
        "grant_type": "client_credentials",
        "appkey": KIWOOM_APP_KEY,
        "secretkey": KIWOOM_APP_SECRET
    }
    
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    logger.info(f"🔑 Requesting Token from {REST_URL}...")
    try:
        async with session.post(REST_URL, headers=headers, json=payload, ssl=False) as resp:
            text = await resp.text()
            if resp.status == 200:
                data = json.loads(text)
                logger.info(f"🔍 Full Response Data: {data}")
                token = data.get("access_token") or data.get("token")
                if token:
                    logger.info(f"✅ Token Received: {token[:10]}...")
                else:
                    logger.error("❌ 'token' or 'access_token' field missing in response!")
                return token
            else:
                logger.error(f"❌ Token Failed ({resp.status}): {text}")
                return None
    except Exception as e:
        logger.error(f"❌ Token Request Error: {e}")
        logger.error(traceback.format_exc())
        return None

async def test_connection():
    if not KIWOOM_APP_KEY or not KIWOOM_APP_SECRET:
        logger.error("❌ .env.backtest에 KIWOOM_APP_KEY/SECRET이 없습니다.")
        return

    logger.info(f"🚀 Target Env: {'MOCK' if KIWOOM_MOCK else 'REAL'}")
    
    async with aiohttp.ClientSession() as session:
        # 1. Get Token
        token = await get_access_token(session)
        if not token:
            return

        # 2. Connect WS (Without Header first, assume Auth in Body)
        # headers = { "Authorization": f"Bearer {token}" } 
        
        logger.info(f"🚀 Connecting to {WS_URL}...")
        try:
            async with session.ws_connect(WS_URL, ssl=False) as ws:
                logger.info("✅ Connected! Sending Subscribe...")
                
                # 3. Subscribe
                payload = {
                    "header": {
                        "token": token,
                        "tr_type": "3",
                        "content-type": "utf-8"
                    },
                    "body": {
                        "input": {
                            "tr_id": "H0STCNT0", 
                            "tr_key": "005930"
                        }
                    }
                }
                
                await ws.send_json(payload)
                logger.info("📤 Sent Subscribe Payload")
                
                # 4. Wait for Response
                start_time = asyncio.get_event_loop().time()
                while (asyncio.get_event_loop().time() - start_time) < 10:
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=1.0)
                        
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            logger.info(f"📥 Received: {json.dumps(data, indent=2, ensure_ascii=False)}")
                            
                            # Check body for data
                            if "body" in data:
                                logger.info(f"📊 Body Data: {str(data['body'])[:100]}...")
                                    
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            logger.warning("⚠️ Connection Closed")
                            break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error("❌ WebSocket Error")
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                        
        except Exception as e:
            logger.error(f"❌ Connection Failed: {e}")
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_connection())
