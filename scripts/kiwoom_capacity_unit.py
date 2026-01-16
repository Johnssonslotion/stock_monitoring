#!/usr/bin/env python3
"""
Kiwoom WebSocket - Capacity Unit Test
목표: 100개 제한이 '종목 수'인지 '종목*TR 수'인지 확인
시나리오: 60개 종목에 대해 ["0B", "0D"] 동시 등록 시도.
- 성공하면 제한은 '종목 수' 기준.
- 실패하면 제한은 'TR 등록 건수' 기준.
"""
import asyncio
import os
import json
import logging
from dotenv import load_dotenv
import websockets
import aiohttp
import ssl

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger("KiwoomUnit")

load_dotenv(".env.backtest")
KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY")
KIWOOM_APP_SECRET = os.getenv("KIWOOM_APP_SECRET")

async def get_token():
    try:
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
                return data.get("access_token") or data.get("token")
    except Exception as e:
        logger.error(f"❌ Token error: {e}")
        return None

async def main():
    token = await get_token()
    if not token:
        return

    ssl_context = ssl._create_unverified_context()
    async with websockets.connect("wss://api.kiwoom.com:10000/api/dostk/websocket", ssl=ssl_context) as ws:
        # LOGIN
        await ws.send(json.dumps({"trnm": "LOGIN", "token": token}))
        await ws.recv()
        logger.info("✅ Login")

        # 60개 종목 생성
        targets = [f"{i:06d}" for i in range(1, 61)] # 60 items
        
        # 0B(체결) + 0D(호가) 동시 등록
        req = {
            "trnm": "REG",
            "grp_no": "0001",
            "refresh": "1",
            "data": [{
                "item": targets,
                "type": ["0B", "0D"] 
            }]
        }
        
        logger.info(f"🚀 60개 종목에 대해 [0B, 0D] 동시 등록 시도 (Total TR Count: 120 vs Symbol Count: 60)")
        await ws.send(json.dumps(req))
        res = json.loads(await ws.recv())
        
        if res.get("return_code") == 0:
            logger.info("✅ 성공! 제한은 '종목 수' 기준입니다. (60종목 OK)")
        else:
            logger.error(f"❌ 실패! 제한은 'TR 건수' 기준일 가능성이 높습니다. (120 > 100) \nMsg: {res.get('return_msg')}")

if __name__ == "__main__":
    asyncio.run(main())
