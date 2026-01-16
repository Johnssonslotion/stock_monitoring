#!/usr/bin/env python3
"""
Kiwoom WebSocket using websockets library (not aiohttp)
"""
import asyncio
import os
import json
import logging
from dotenv import load_dotenv
import websockets
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KiwoomWS")

load_dotenv(".env.backtest")

KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY")
KIWOOM_APP_SECRET = os.getenv("KIWOOM_APP_SECRET")

async def get_token():
    """Get Token via REST"""
    async with aiohttp.ClientSession() as session:
        url = "https://api.kiwoom.com/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "appkey": KIWOOM_APP_KEY,
            "secretkey": KIWOOM_APP_SECRET
        }
        headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
        
        async with session.post(url, json=payload, headers=headers, ssl=False) as resp:
            data = await resp.json()
            return data.get("token")

async def test_websockets_lib():
    """Use websockets library instead of aiohttp"""
    
    # 1. Get Token
    token = await get_token()
    logger.info(f"✅ Token: {token[:10]}...")
    
    # 2. Connect WebSocket
    ws_url = "wss://api.kiwoom.com:10000/api/dostk/websocket"
    logger.info(f"🔌 Connecting to {ws_url}...")
    
    try:
        async with websockets.connect(ws_url) as ws:
            logger.info("✅ Connected!")
            
            # 3. Send Auth
            auth_msg = {"header": {"token": token, "tr_type": "1"}}
            await ws.send(json.dumps(auth_msg))
            logger.info(f"📤 Auth Sent")
            
            # 4. Receive Auth Response
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            logger.info(f"📥 Auth Response: {response}")
            
            # 5. Subscribe
            subscribe_msg = {
                "header": {"token": token, "tr_type": "3", "content-type": "utf-8"},
                "body": {"input": {"tr_id": "H0STCNT0", "tr_key": "005930"}}
            }
            await ws.send(json.dumps(subscribe_msg))
            logger.info("📤 Subscribe Sent")
            
            # 6. Receive Data
            logger.info("⏰ Waiting for data...")
            for i in range(10):
                try:
                    data = await asyncio.wait_for(ws.recv(), timeout=3)
                    logger.info(f"📊 [{i+1}] {data[:200]}...")
                except asyncio.TimeoutError:
                    logger.info(f"⏰ Timeout {i+1}/10")
                    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_websockets_lib())
