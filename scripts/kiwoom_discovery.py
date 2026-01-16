#!/usr/bin/env python3
"""
Kiwoom API Protocol Discovery
모든 요청/응답을 상세히 로깅하여 프로토콜 파악
"""
import asyncio
import os
import json
import logging
import sys
from datetime import datetime
from dotenv import load_dotenv
import aiohttp

# 상세 로깅
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"kiwoom_discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("KiwoomDiscovery")

load_dotenv(".env.backtest")

KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY")
KIWOOM_APP_SECRET = os.getenv("KIWOOM_APP_SECRET")
BASE_DOMAIN = "api.kiwoom.com"

# Test Various Endpoints
ENDPOINTS = {
    "token": f"https://{BASE_DOMAIN}/oauth2/token",
    "ws_10000": f"wss://{BASE_DOMAIN}:10000",
    "ws_10000_dostk": f"wss://{BASE_DOMAIN}:10000/api/dostk/websocket",
    "ws_443": f"wss://{BASE_DOMAIN}/websocket",
    "ws_443_dostk": f"wss://{BASE_DOMAIN}/api/dostk/websocket",
}

async def get_token(session):
    """Token 발급"""
    payload = {
        "grant_type": "client_credentials",
        "appkey": KIWOOM_APP_KEY,
        "secretkey": KIWOOM_APP_SECRET
    }
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0"
    }
    
    logger.info("=" * 80)
    logger.info("TOKEN REQUEST")
    logger.info(f"URL: {ENDPOINTS['token']}")
    logger.info(f"Payload: {json.dumps(payload, indent=2)}")
    logger.info(f"Headers: {json.dumps(headers, indent=2)}")
    
    async with session.post(ENDPOINTS['token'], json=payload, headers=headers, ssl=False) as resp:
        status = resp.status
        text = await resp.text()
        
        logger.info(f"Response Status: {status}")
        logger.info(f"Response Headers: {dict(resp.headers)}")
        logger.info(f"Response Body: {text}")
        
        if status == 200:
            data = json.loads(text)
            token = data.get("access_token") or data.get("token")
            return token
    return None

async def try_websocket_connection(session, url, token, test_name):
    """WebSocket 연결 시도 (다양한 방법)"""
    logger.info("=" * 80)
    logger.info(f"WEBSOCKET TEST: {test_name}")
    logger.info(f"URL: {url}")
    
    # Method 1: No Auth
    logger.info("--- Method 1: No Auth Header ---")
    try:
        async with session.ws_connect(url, ssl=False, timeout=aiohttp.ClientTimeout(total=5)) as ws:
            logger.info("✅ Connected (No Auth)!")
            
            # Try sending subscribe
            payload = {
                "header": {"token": token, "tr_type": "3"},
                "body": {"input": {"tr_id": "H0STCNT0", "tr_key": "005930"}}
            }
            await ws.send_json(payload)
            logger.info(f"📤 Sent: {json.dumps(payload)}")
            
            # Wait for response
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=3)
                logger.info(f"📥 Received: {msg.data}")
            except asyncio.TimeoutError:
                logger.warning("⏰ No response within 3s")
                
    except Exception as e:
        logger.error(f"❌ Method 1 Failed: {e}")
    
    # Method 2: Bearer Token Header
    logger.info("--- Method 2: Bearer Token Header ---")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        async with session.ws_connect(url, headers=headers, ssl=False, timeout=aiohttp.ClientTimeout(total=5)) as ws:
            logger.info("✅ Connected (Bearer Token)!")
            
            payload = {
                "header": {"tr_type": "3"},
                "body": {"input": {"tr_id": "H0STCNT0", "tr_key": "005930"}}
            }
            await ws.send_json(payload)
            logger.info(f"📤 Sent: {json.dumps(payload)}")
            
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=3)
                logger.info(f"📥 Received: {msg.data}")
            except asyncio.TimeoutError:
                logger.warning("⏰ No response within 3s")
                
    except Exception as e:
        logger.error(f"❌ Method 2 Failed: {e}")
    
    # Method 3: AppKey/Secret Header
    logger.info("--- Method 3: AppKey/Secret Header ---")
    try:
        headers = {
            "appkey": KIWOOM_APP_KEY,
            "appsecret": KIWOOM_APP_SECRET,
            "token": token
        }
        async with session.ws_connect(url, headers=headers, ssl=False, timeout=aiohttp.ClientTimeout(total=5)) as ws:
            logger.info("✅ Connected (AppKey/Secret)!")
            
            payload = {
                "header": {"tr_type": "3"},
                "body": {"input": {"tr_id": "H0STCNT0", "tr_key": "005930"}}
            }
            await ws.send_json(payload)
            logger.info(f"📤 Sent: {json.dumps(payload)}")
            
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=3)
                logger.info(f"📥 Received: {msg.data}")
            except asyncio.TimeoutError:
                logger.warning("⏰ No response within 3s")
                
    except Exception as e:
        logger.error(f"❌ Method 3 Failed: {e}")
    
    # Method 4: Query Parameter
    logger.info("--- Method 4: Query Parameter ---")
    try:
        url_with_token = f"{url}?token={token}&appkey={KIWOOM_APP_KEY}"
        async with session.ws_connect(url_with_token, ssl=False, timeout=aiohttp.ClientTimeout(total=5)) as ws:
            logger.info("✅ Connected (Query Param)!")
            
            payload = {
                "header": {"tr_type": "3"},
                "body": {"input": {"tr_id": "H0STCNT0", "tr_key": "005930"}}
            }
            await ws.send_json(payload)
            logger.info(f"📤 Sent: {json.dumps(payload)}")
            
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=3)
                logger.info(f"📥 Received: {msg.data}")
            except asyncio.TimeoutError:
                logger.warning("⏰ No response within 3s")
                
    except Exception as e:
        logger.error(f"❌ Method 4 Failed: {e}")

async def main():
    logger.info("🚀 Kiwoom API Protocol Discovery Started")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Get Token
        token = await get_token(session)
        if not token:
            logger.error("💀 Token Failed - Aborting")
            return
        
        logger.info(f"✅ Token: {token[:20]}...")
        
        # Step 2: Try All WebSocket Endpoints
        for name, url in ENDPOINTS.items():
            if not name.startswith("ws_"):
                continue
            await try_websocket_connection(session, url, token, name)
            await asyncio.sleep(2)
    
    logger.info("=" * 80)
    logger.info("🏁 Discovery Complete - Check log file for details")

if __name__ == "__main__":
    asyncio.run(main())
