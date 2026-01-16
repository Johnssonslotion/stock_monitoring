#!/usr/bin/env python3
"""
Kiwoom WebSocket - Correct Authentication Flow
발견: 연결 후 즉시 토큰 전송 필요
"""
import asyncio
import os
import json
import logging
import sys
from dotenv import load_dotenv
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KiwoomAuth")

load_dotenv(".env.backtest")

KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY")
KIWOOM_APP_SECRET = os.getenv("KIWOOM_APP_SECRET")

async def test_correct_auth():
    """올바른 인증 플로우 테스트"""
    
    # 1. Get Token
    async with aiohttp.ClientSession() as session:
        token_url = "https://api.kiwoom.com/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "appkey": KIWOOM_APP_KEY,
            "secretkey": KIWOOM_APP_SECRET
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        
        async with session.post(token_url, json=payload, headers=headers, ssl=False) as resp:
            data = await resp.json()
            token = data.get("token")
            logger.info(f"✅ Token: {token[:10]}...")
        
        # 2. Connect WebSocket
        ws_url = "wss://api.kiwoom.com:10000/api/dostk/websocket"
        logger.info(f"🔌 Connecting to {ws_url}...")
        
        async with session.ws_connect(ws_url, ssl=False) as ws:
            logger.info("✅ WebSocket Connected!")
            
            # 3. IMMEDIATELY Send Auth Message (허용요청)
            auth_msg = {
                "header": {
                    "token": token,
                    "tr_type": "1"  # 1: 허용요청 (추정)
                }
            }
            
            await ws.send_json(auth_msg)
            logger.info(f"📤 Sent Auth: {json.dumps(auth_msg)}")
            
            # 4. Wait for Auth Response
            msg = await asyncio.wait_for(ws.receive(), timeout=5)
            logger.info(f"📥 Auth Response: {msg.data}")
            
            # 5. Send Subscribe
            subscribe_msg = {
                "header": {
                    "token": token,
                    "tr_type": "3",  # 3: 실시간 등록
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": "H0STCNT0",  # 주식체결
                        "tr_key": "005930"  # 삼성전자
                    }
                }
            }
            
            await ws.send_json(subscribe_msg)
            logger.info(f"📤 Sent Subscribe: {json.dumps(subscribe_msg)}")
            
            # 6. Wait for Data
            logger.info("⏰ Waiting for real-time data...")
            for _ in range(10):
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=2)
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        logger.info(f"📊 DATA: {json.dumps(data, indent=2, ensure_ascii=False)[:300]}...")
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        logger.warning("⚠️ Connection Closed")
                        break
                except asyncio.TimeoutError:
                    continue

if __name__ == "__main__":
    asyncio.run(test_correct_auth())
