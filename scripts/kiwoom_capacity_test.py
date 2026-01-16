#!/usr/bin/env python3
"""
Kiwoom WebSocket - 최대 구독 한도(Capacity) 테스트
"""
import asyncio
import os
import json
import logging
from dotenv import load_dotenv
import websockets
import aiohttp

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger("KiwoomCapability")

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
        async with session.post(url, json=payload, headers={"Content-Type": "application/json"}, ssl=False) as resp:
            return (await resp.json()).get("token")

async def main():
    token = await get_token()
    if not token:
        logger.error("❌ Token 발급 실패")
        return

    async with websockets.connect("wss://api.kiwoom.com:10000/api/dostk/websocket") as ws:
        # LOGIN
        await ws.send(json.dumps({"trnm": "LOGIN", "token": token}))
        await ws.recv()
        logger.info("✅ Login 완료")

        # 가상의 종목 코드 생성 (000001 ~ 001000) - 실제 종목이 아니어도 REG는 접수될 수 있음
        # 테스트를 위해 실제 존재하는 코드 일부와 가상 코드를 섞음
        # (실패 시 실제 코드로만 구성된 리스트로 재시도 필요할 수 있음)
        
        # 1000개의 더미 코드 생성
        total_symbols = [f"{i:06d}" for i in range(1, 1001)] 
        chunk_size = 100
        
        logger.info(f"🚀 대량 구독 테스트 시작 (총 {len(total_symbols)}개, 배치 크기 {chunk_size})")

        success_count = 0
        
        for i in range(0, len(total_symbols), chunk_size):
            chunk = total_symbols[i:i + chunk_size]
            grp_no = f"{(i // chunk_size) + 1:04d}"  # 0001, 0002 ...
            
            req = {
                "trnm": "REG",
                "grp_no": grp_no,
                "refresh": "1",  # 누적 등록
                "data": [{
                    "item": chunk,
                    "type": ["0B"]  # 주식체결
                }]
            }
            
            await ws.send(json.dumps(req))
            res = json.loads(await ws.recv())
            
            if res.get("return_code") == 0:
                success_count += len(chunk)
                logger.info(f"✅ Batch {grp_no}: {len(chunk)}개 등록 성공 (누적 {success_count}개)")
            else:
                logger.error(f"❌ Batch {grp_no} 실패: {res}")
                break
                
            await asyncio.sleep(0.1)

        logger.info(f"🏁 테스트 종료. 성공적으로 구독된 총 종목 수: {success_count}")

if __name__ == "__main__":
    asyncio.run(main())
