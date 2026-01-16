#!/usr/bin/env python3
"""
Kiwoom WebSocket - Capacity Test (Retry)
목표: 1,000개 종목 등록 시도
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
logger = logging.getLogger("KiwoomTest")

load_dotenv(".env.backtest")
# .env.backtest가 없을 경우를 대비해 직접 로드 시도 (또는 환경변수 확인)
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
            # 헤더와 SSL 비활성화 중요
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            }
            async with session.post(url, json=payload, headers=headers, ssl=False) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"❌ Token 요청 실패: {resp.status} - {text}")
                    return None
                    
                data = await resp.json()
                return data.get("access_token") or data.get("token")
    except Exception as e:
        logger.error(f"❌ Token 예외: {e}")
        return None

async def main():
    if not KIWOOM_APP_KEY:
        logger.error("❌ 환경변수 KIWOOM_APP_KEY 없음")
        return

    logger.info("🔑 Token 발급 시도...")
    token = await get_token()
    if not token:
        logger.error("❌ Token 확보 실패. 중단.")
        return
    logger.info(f"✅ Token 확보 완료: {token[:10]}...")

    ws_url = "wss://api.kiwoom.com:10000/api/dostk/websocket"
    ssl_context = ssl._create_unverified_context()

    async with websockets.connect(ws_url, ssl=ssl_context) as ws:
        # LOGIN
        await ws.send(json.dumps({"trnm": "LOGIN", "token": token}))
        login_res = json.loads(await ws.recv())
        logger.info(f"📥 LOGIN: {login_res}")
        
        if login_res.get("return_code") != 0:
            logger.error("로그인 실패")
            return

        # 1000개의 종목 코드 생성 (실제 종목 005930 포함하여 섞음)
        # Kiwoom은 존재하지 않는 종목코드도 등록은 받아주는 경우가 많음 (또는 무시)
        # 실제 한도를 보기 위해 요청을 보냄
        
        targets = [f"{i:06d}" for i in range(1, 1001)]
        # 앞부분에 삼성전자 등 실제 종목 포함
        targets[0] = "005930"
        targets[1] = "000660"
        
        batch_size = 50
        total_registered = 0
        
        logger.info(f"🚀 Capacity Test 시작: {len(targets)}개 종목 (Batch {batch_size})")

        for i in range(0, len(targets), batch_size):
            batch = targets[i:i+batch_size]
            
            req = {
                "trnm": "REG",
                "grp_no": f"{(i//batch_size)+1:04d}",
                "refresh": "1",  # 1=추가 등록
                "data": [{
                    "item": batch,
                    "type": ["0B"] # 주식체결
                }]
            }
            
            await ws.send(json.dumps(req))
            res = json.loads(await ws.recv())
            
            if res.get("return_code") == 0:
                total_registered += len(batch)
                logger.info(f"✅ Registered {len(batch)} items. Total: {total_registered}")
            else:
                logger.error(f"❌ Failed at {total_registered}: {res}")
                break
            
            await asyncio.sleep(0.2) # 너무 빠르면 도배로 차단될 수 있음

        logger.info(f"🏁 Final Count: {total_registered} / {len(targets)}")

if __name__ == "__main__":
    asyncio.run(main())
