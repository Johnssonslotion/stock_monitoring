#!/usr/bin/env python3
"""
Kiwoom WebSocket - 공식 문서 기반 구현
"""
import asyncio
import os
import json
import logging
from dotenv import load_dotenv
import websockets
import aiohttp

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("Kiwoom")

load_dotenv(".env.backtest")

KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY")
KIWOOM_APP_SECRET = os.getenv("KIWOOM_APP_SECRET")

async def get_token():
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

async def main():
    token = await get_token()
    logger.info(f"✅ Token: {token[:15]}...")
    
    ws_url = "wss://api.kiwoom.com:10000/api/dostk/websocket"
    
    async with websockets.connect(ws_url) as ws:
        logger.info("✅ WebSocket Connected!")
        
        # Step 1: LOGIN
        login_msg = {
            "trnm": "LOGIN",
            "token": token
        }
        
        await ws.send(json.dumps(login_msg))
        logger.info("📤 LOGIN sent")
        
        response = await ws.recv()
        login_data = json.loads(response)
        logger.info(f"📥 LOGIN Response: {json.dumps(login_data, indent=2, ensure_ascii=False)}")
        
        if login_data.get("return_code") != 0:
            logger.error("❌ LOGIN FAILED")
            return
        
        logger.info("🎉 LOGIN SUCCESS!")
        
        # Step 2: REG (등록) - 공식 문서 스펙
        reg_msg = {
            "trnm": "REG",
            "grp_no": "0001",
            "refresh": "1",
            "data": [
                {
                    "item": ["005930"],  # 삼성전자
                    "type": ["0B"]       # 주식체결
                }
            ]
        }
        
        await ws.send(json.dumps(reg_msg))
        logger.info(f"📤 REG sent: {json.dumps(reg_msg, indent=2, ensure_ascii=False)}")
        
        # Step 3: Receive responses
        logger.info("\n⏰ Waiting for real-time data...\n")
        
        for i in range(30):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2)
                data = json.loads(msg)
                
                # Pretty print
                if i == 0:
                    # First message (REG response)
                    logger.info(f"📥 REG Response:")
                    logger.info(json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    # Real-time data
                    trnm = data.get("trnm")
                    if trnm == "REAL":
                        item = data.get("data", [{}])[0].get("item", "")
                        values = data.get("data", [{}])[0].get("values", {})
                        price = values.get("10", "")  # 현재가
                        logger.info(f"📊 [{i}] {item} 현재가: {price}")
                    else:
                        logger.info(f"📥 [{i}] {msg[:150]}...")
                        
            except asyncio.TimeoutError:
                logger.info(f"⏰ Timeout {i+1}/30")

if __name__ == "__main__":
    asyncio.run(main())
