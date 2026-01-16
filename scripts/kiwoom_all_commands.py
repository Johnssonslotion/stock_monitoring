#!/usr/bin/env python3
"""
Kiwoom WebSocket - 다양한 TR 타입 테스트
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
        logger.info("✅ Connected!")
        
        # LOGIN
        await ws.send(json.dumps({"trnm": "LOGIN", "token": token}))
        response = await ws.recv()
        logger.info(f"📥 LOGIN: {response}")
        
        # 문서의 모든 TR 타입 등록 시도
        tr_types = {
            "0B": "주식체결",
            "0D": "주식호가잔량",
            "0A": "주식기세",
            "0C": "주식우선호가",
            "0H": "주식예상체결",
            "0J": "업종지수",
            "0g": "주식종목정보",
            "0s": "장시작시간"
        }
        
        symbols = ["005930", "000660", "035720"]  # 삼성전자, SK하이닉스, 카카오
        
        for tr_code, tr_name in tr_types.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing: {tr_code} - {tr_name}")
            logger.info(f"{'='*60}")
            
            reg_msg = {
                "trnm": "REG",
                "grp_no": f"{int(tr_code, 16):04d}",  # Unique group number
                "refresh": "1",
                "data": [
                    {
                        "item": symbols,
                        "type": [tr_code]
                    }
                ]
            }
            
            await ws.send(json.dumps(reg_msg))
            logger.info(f"📤 REG {tr_code} sent for {len(symbols)} symbols")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=3)
                data = json.loads(response)
                logger.info(f"📥 Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            except asyncio.TimeoutError:
                logger.warning(f"⏰ No response for {tr_code}")
            
            await asyncio.sleep(0.5)
        
        # Listen for any data
        logger.info(f"\n{'='*60}")
        logger.info("⏰ Listening for real-time data (20 seconds)...")
        logger.info(f"{'='*60}\n")
        
        for i in range(20):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1)
                data = json.loads(msg)
                
                trnm = data.get("trnm")
                if trnm == "PING":
                    logger.info(f"💓 PING")
                elif trnm == "REAL":
                    logger.info(f"📊 REAL DATA: {json.dumps(data, indent=2, ensure_ascii=False)}")
                else:
                    logger.info(f"📥 {msg[:200]}...")
                    
            except asyncio.TimeoutError:
                pass

if __name__ == "__main__":
    asyncio.run(main())
