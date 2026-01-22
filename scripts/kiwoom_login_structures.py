#!/usr/bin/env python3
"""
Kiwoom WebSocket - 올바른 로그인 구조
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

load_dotenv(".env.prod")

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
        headers = {"Content-Type": "application/json; charset=UTF-8", "User-Agent": "Mozilla/5.0"}
        
        async with session.post(url, json=payload, headers=headers, ssl=False) as resp:
            data = await resp.json()
            return data.get("token")

async def test_login_structures():
    token = await get_token()
    logger.info(f"✅ Token: {token[:15]}...")
    
    ws_url = "wss://api.kiwoom.com:10000/api/dostk/websocket"
    
    # Test different login message structures
    test_cases = [
        {
            "name": "Structure 1: token in body",
            "msg": {
                "trnm": "LOGIN",
                "body": {
                    "token": token
                }
            }
        },
        {
            "name": "Structure 2: token at root",
            "msg": {
                "trnm": "LOGIN",
                "token": token
            }
        },
        {
            "name": "Structure 3: header with token",
            "msg": {
                "trnm": "LOGIN",
                "header": {
                    "token": token
                },
                "body": {}
            }
        },
        {
            "name": "Structure 4: appkey/token",
            "msg": {
                "trnm": "LOGIN",
                "appkey": KIWOOM_APP_KEY,
                "token": token
            }
        }
    ]
    
    for test in test_cases:
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 Testing: {test['name']}")
        logger.info(f"{'='*60}")
        
        try:
            async with websockets.connect(ws_url) as ws:
                logger.info("✅ Connected!")
                
                # Send login
                await ws.send(json.dumps(test['msg']))
                logger.info(f"📤 Sent: {json.dumps(test['msg'], indent=2, ensure_ascii=False)}")
                
                # Receive response
                response = await asyncio.wait_for(ws.recv(), timeout=3)
                data = json.loads(response)
                
                logger.info(f"📥 Response:")
                logger.info(json.dumps(data, indent=2, ensure_ascii=False))
                
                # Check success
                return_code = data.get("return_code")
                if return_code == 0:
                    logger.info(f"\n🎉🎉🎉 SUCCESS! 🎉🎉🎉")
                    logger.info(f"Correct structure: {test['name']}")
                    
                    # Try to subscribe
                    sub_msg = {
                        "trnm": "H0STCNT0",
                        "header": {"token": token, "tr_type": "3"},
                        "body": {"input": {"tr_id": "H0STCNT0", "tr_key": "005930"}}
                    }
                    
                    await ws.send(json.dumps(sub_msg))
                    logger.info("\n📤 Subscribe sent!")
                    
                    for i in range(5):
                        msg = await asyncio.wait_for(ws.recv(), timeout=3)
                        logger.info(f"📊 [{i+1}] {msg[:200]}...")
                    
                    return
                    
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(test_login_structures())
