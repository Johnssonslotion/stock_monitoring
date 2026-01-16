#!/usr/bin/env python3
"""
Kiwoom WebSocket - 시간외 호가 (0E) 테스트
참고: 0E는 '주식시간외호가' TR입니다.
"""
import asyncio
import os
import json
import logging
from dotenv import load_dotenv
import websockets
import aiohttp

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Kiwoom-0E")

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
    logger.info(f"✅ Token Obtained")
    
    ws_url = "wss://api.kiwoom.com:10000/api/dostk/websocket"
    
    async with websockets.connect(ws_url) as ws:
        logger.info("✅ Connected to WebSocket")
        
        # 1. LOGIN
        await ws.send(json.dumps({"trnm": "LOGIN", "token": token}))
        login_res = json.loads(await ws.recv())
        logger.info(f"📥 LOGIN: {login_res}")
        
        if login_res.get("return_code") != 0:
            logger.error("Login failed")
            return

        # 2. REG - 0E (시간외호가)
        # 삼성전자(005930), SK하이닉스(000660)
        symbols = ["005930", "000660"]
        tr_code = "0E" 
        
        reg_msg = {
            "trnm": "REG",
            "grp_no": "0100",
            "refresh": "1",
            "data": [
                {
                    "item": symbols,
                    "type": [tr_code]
                }
            ]
        }
        
        logger.info(f"📤 Subscribing to {tr_code} (주식시간외호가) for {symbols}")
        await ws.send(json.dumps(reg_msg))
        
        reg_res = json.loads(await ws.recv())
        logger.info(f"📥 REG Response: {reg_res}")
        
        # 3. Listen for data
        logger.info("🎧 Listening for data (30 seconds)...")
        logger.info("   (현재 시각이 장 운영 시간이 아니라면 데이터가 오지 않을 수 있습니다)")
        
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                data = json.loads(msg)
                
                trnm = data.get("trnm")
                
                if trnm == "PING":
                    logger.info("💓 PING received")
                elif trnm == "REAL":
                    # 데이터 파싱 시도
                    values = data.get("data", [{}])[0].get("values", {})
                    # 시간외 호가 관련 주요 FID로 추정되는 값들 출력
                    # 10: 현재가, 15: 거래량, ETC...
                    logger.info(f"📊 REAL DATA ({data.get('data')[0].get('type')}): {data.get('data')[0].get('item')}")
                    logger.info(f"   Values Sample: {list(values.items())[:5]}...") 
                else:
                    logger.info(f"📥 Message: {msg}")
                    
        except asyncio.TimeoutError:
            logger.info("⏰ Timeout: No data received for 30 seconds.")
        except KeyboardInterrupt:
            logger.info("🛑 Stopped by user")

if __name__ == "__main__":
    asyncio.run(main())
