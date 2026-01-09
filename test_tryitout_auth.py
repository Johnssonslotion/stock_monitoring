#!/usr/bin/env python3
"""
테스트 엔드포인트에 실제 키로 연결 검증
"""
import asyncio
import websockets
import json
import os
from dotenv import load_dotenv
import sys
sys.path.insert(0, '/home/ubuntu/workspace/stock_monitoring')

load_dotenv()
from src.data_ingestion.price.common import KISAuthManager

async def test_tryitout_with_real_key():
    print("="*60)
    print("Testing /tryitout/ endpoint WITH real credentials")
    print("="*60)
    
    # 1. Approval Key
    print("🔑 Getting Approval Key...")
    auth = KISAuthManager()
    try:
        approval_key = await auth.get_approval_key()
        print(f"✅ Approval Key obtained\n")
    except Exception as e:
        print(f"❌ Failed: {e}\n")
        return
    
    # 2. /tryitout/ with FULL auth
    url = "ws://ops.koreainvestment.com:21000/tryitout/H0STCNT0"
    
    print(f"🔌 Connecting to: {url}\n")
    
    try:
        async with websockets.connect(url, ping_interval=20) as ws:
            print("✅ Connected\n")
            
            # 3. 완전한 구독 요청
            req = {
                "header": {
                    "approval_key": approval_key,
                    "custtype": "P",
                    "tr_type": "1",
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": "H0STCNT0",
                        "tr_key": "005930"
                    }
                }
            }
            
            await ws.send(json.dumps(req))
            print(f"📤 Sent FULL auth subscription\n")
            
            # 4. 응답 대기 (장 마감이므로 SUBSCRIBE SUCCESS만 올 것)
            print("⏳ Waiting for messages (10 seconds)...\n")
            
            msg_count = 0
            for i in range(10):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msg_count += 1
                    
                    print(f"📨 Message #{msg_count}:")
                    print(f"   {msg[:300]}\n")
                    
                except asyncio.TimeoutError:
                    if msg_count == 0 and i < 3:
                        print(f"   ... waiting ({i+1}s)")
            
            print("="*60)
            print(f"Total: {msg_count} messages")
            
            if msg_count == 0:
                print("❌ NO messages")
            elif msg_count == 1:
                print("⚠️  구독 확인만 받음 (정상 - 장 마감)")
                print("✅ /tryitout/ 엔드포인트 인증 성공!")
            else:
                print(f"✅ {msg_count} messages")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_tryitout_with_real_key())
