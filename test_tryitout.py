#!/usr/bin/env python3
"""
테스트 엔드포인트 검증 - 실제로 로그가 찍히는지 확인
"""
import asyncio
import websockets
import json
import sys
sys.path.insert(0, '/home/ubuntu/workspace/stock_monitoring')

from src.data_ingestion.price.common import KISAuthManager

async def test_tryitout_endpoint():
    print("🧪 Testing /tryitout/ endpoint...")
    
    # Approval Key
    auth = KISAuthManager()
    key = await auth.get_approval_key()
    
    # TEST endpoint
    url = "ws://ops.koreainvestment.com:21000/tryitout/H0STCNT0"
    
    print(f"Connecting to: {url}\n")
    
    async with websockets.connect(url, ping_interval=20) as ws:
        print("✅ Connected to TEST endpoint\n")
        
        # Subscribe
        req = {
            "header": {"approval_key": key, "custtype": "P", "tr_type": "1", "content-type": "utf-8"},
            "body": {"input": {"tr_id": "H0STCNT0", "tr_key": "005930"}}
        }
        await ws.send(json.dumps(req))
        print(f"📤 Sent subscription request\n")
        
        # Wait for messages
        print("⏳ Waiting for messages (10 seconds)...\n")
        msg_count = 0
        
        try:
            for i in range(10):
                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                msg_count += 1
                print(f"📨 Message #{msg_count}:")
                print(f"   Length: {len(msg)}")
                print(f"   First 200 chars: {msg[:200]}\n")
        except asyncio.TimeoutError:
            print(f"⏱️  Timeout after {msg_count} messages\n")
        
        print(f"{'='*60}")
        print(f"Total messages received: {msg_count}")
        if msg_count <= 1:
            print("❌ TEST endpoint: Only subscription confirmation, NO tick data")
        else:
            print("✅ TEST endpoint: Receiving data")

asyncio.run(test_tryitout_endpoint())
