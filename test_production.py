#!/usr/bin/env python3
"""
.env에서 KIS 키를 읽어 프로덕션 엔드포인트 검증
"""
import asyncio
import websockets
import json
import os
from dotenv import load_dotenv
import sys
sys.path.insert(0, '/home/ubuntu/workspace/stock_monitoring')

# .env 로드
load_dotenv()

from src.data_ingestion.price.common import KISAuthManager

async def test_production_endpoint():
    print("="*60)
    print("Testing PRODUCTION endpoint with .env credentials")
    print("="*60)
    
    # 1. .env 확인
    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    
    if not app_key or not app_secret:
        print("❌ KIS_APP_KEY or KIS_APP_SECRET not found in .env")
        return
    
    print(f"✅ KIS_APP_KEY: {app_key[:10]}...")
    print(f"✅ KIS_APP_SECRET: {app_secret[:10]}...\n")
    
    # 2. Approval Key 발급
    print("🔑 Getting Approval Key...")
    auth = KISAuthManager()
    try:
        approval_key = await auth.get_approval_key()
        print(f"✅ Approval Key: {approval_key[:20]}...\n")
    except Exception as e:
        print(f"❌ Approval Key Failed: {e}\n")
        return
    
    # 3. PRODUCTION endpoint 테스트
    url = "ws://ops.koreainvestment.com:21000/H0STCNT0"  # NO /tryitout/
    
    print(f"🔌 Connecting to: {url}\n")
    
    try:
        async with websockets.connect(url, ping_interval=20) as ws:
            print("✅ Connected to PRODUCTION endpoint\n")
            
            # 4. 구독 요청
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
                        "tr_key": "005930"  # 삼성전자
                    }
                }
            }
            
            await ws.send(json.dumps(req))
            print(f"📤 Sent subscription request\n")
            
            # 5. 응답 대기
            print("⏳ Waiting for messages (10 seconds)...\n")
            
            msg_count = 0
            for i in range(10):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msg_count += 1
                    
                    print(f"📨 Message #{msg_count}:")
                    print(f"   Length: {len(msg)}")
                    
                    # JSON 파싱 시도
                    if msg[0] in ['{', '[']:
                        try:
                            data = json.loads(msg)
                            print(f"   Type: JSON")
                            print(f"   Content: {json.dumps(data, ensure_ascii=False, indent=2)[:300]}")
                        except:
                            print(f"   Content: {msg[:200]}")
                    else:
                        print(f"   Type: Pipe-delimited")
                        parts = msg.split('|')
                        print(f"   Parts: {len(parts)}")
                        if len(parts) >= 2:
                            print(f"   TR_ID: {parts[1]}")
                        if len(parts) >= 4:
                            print(f"   Body: {parts[3][:100]}")
                    print()
                    
                except asyncio.TimeoutError:
                    if msg_count == 0:
                        print(f"   ... no messages at {i+1}s")
            
            print("="*60)
            print(f"Total messages: {msg_count}")
            
            if msg_count == 0:
                print("❌ NO messages - 장 마감 또는 연결 문제")
            elif msg_count == 1:
                print("⚠️  1 message - 구독 확인만 받음")
            else:
                print(f"✅ {msg_count} messages - 데이터 수신 중!")
                
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_production_endpoint())
