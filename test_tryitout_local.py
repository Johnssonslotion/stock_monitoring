#!/usr/bin/env python3
"""
/tryitout/ 엔드포인트 실제 동작 검증
"""
import asyncio
import websockets
import json

async def test_tryitout():
    url = "ws://ops.koreainvestment.com:21000/tryitout/H0STCNT0"
    
    print("="*60)
    print("Testing /tryitout/ endpoint")
    print("="*60)
    print(f"URL: {url}\n")
    
    try:
        async with websockets.connect(url, ping_interval=None) as ws:
            print("✅ Connected\n")
            
            # 단순 구독 (인증 없이)
            req = {
                "header": {"custtype": "P", "tr_type": "1"},
                "body": {"input": {"tr_id": "H0STCNT0", "tr_key": "005930"}}
            }
            
            await ws.send(json.dumps(req))
            print(f"📤 Sent: {json.dumps(req, ensure_ascii=False)}\n")
            
            print("⏳ Waiting for messages (5 seconds)...\n")
            
            msg_count = 0
            for i in range(5):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msg_count += 1
                    print(f"📨 Message #{msg_count}:")
                    print(f"   Length: {len(msg)}")
                    print(f"   Content: {msg[:200]}\n")
                except asyncio.TimeoutError:
                    print(f"   ... timeout at {i+1}s")
            
            print("="*60)
            print(f"Total messages: {msg_count}")
            
            if msg_count == 0:
                print("❌ NO messages received")
                print("   → Connection failed or rejected")
            elif msg_count == 1:
                print("⚠️  Only 1 message (subscription confirmation)")
                print("   → /tryitout/ accepts subscription but sends NO tick data")
            else:
                print(f"✅ {msg_count} messages received")
                print("   → Endpoint is working")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_tryitout())
