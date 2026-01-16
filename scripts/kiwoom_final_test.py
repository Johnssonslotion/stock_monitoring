#!/usr/bin/env python3
"""
Kiwoom WebSocket - trnm 파라미터 추가
"""
import asyncio
import os
import json
import logging
from dotenv import load_dotenv
import websockets
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KiwoomFinal")

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

async def test_with_trnm():
    token = await get_token()
    logger.info(f"✅ Token: {token[:10]}...")
    
    ws_url = "wss://api.kiwoom.com:10000/api/dostk/websocket"
    logger.info(f"🔌 Connecting...")
    
    async with websockets.connect(ws_url) as ws:
        logger.info("✅ Connected!")
        
        # Try different trnm values for auth
        possible_trnm = [
            "AUTH",
            "LOGIN",
            "CONNECT",
            "ALLOW",
            "APPROVE",
            "TOKEN",
            "INIT"
        ]
        
        for trnm_value in possible_trnm:
            logger.info(f"🔍 Trying trnm={trnm_value}...")
            
            auth_msg = {
                "trnm": trnm_value,
                "header": {
                    "token": token,
                    "tr_type": "1"
                }
            }
            
            await ws.send(json.dumps(auth_msg))
            
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=2)
                data = json.loads(response)
                
                logger.info(f"📥 Response: {json.dumps(data, ensure_ascii=False)}")
                
                # Check if success
                return_code = data.get("return_code")
                if return_code == 0 or "성공" in data.get("return_msg", ""):
                    logger.info(f"🎉 SUCCESS with trnm={trnm_value}!")
                    
                    # Now try to subscribe
                    subscribe_msg = {
                        "trnm": "H0STCNT0",  # 주식체결
                        "header": {
                            "token": token,
                            "tr_type": "3"
                        },
                        "body": {
                            "input": {
                                "tr_id": "H0STCNT0",
                                "tr_key": "005930"
                            }
                        }
                    }
                    
                    await ws.send(json.dumps(subscribe_msg))
                    logger.info("📤 Subscribe sent!")
                    
                    # Wait for data
                    for i in range(5):
                        data = await asyncio.wait_for(ws.recv(), timeout=3)
                        logger.info(f"📊 Data [{i+1}]: {data[:150]}...")
                    
                    return
                    
            except asyncio.TimeoutError:
                logger.warning(f"⏰ No response for {trnm_value}")
            except websockets.exceptions.ConnectionClosed:
                logger.error(f"❌ Connection closed for {trnm_value}")
                break

if __name__ == "__main__":
    asyncio.run(test_with_trnm())
