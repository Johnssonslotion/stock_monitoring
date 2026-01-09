import asyncio
import websockets
import json
import os
import sys

# Add project root to path
sys.path.insert(0, '/home/ubuntu/workspace/stock_monitoring')

async def test_kis_websocket():
    """KIS WebSocket 직접 테스트 - 실제 메시지 포맷 확인"""
    
    print("=" * 60)
    print("KIS WebSocket Direct Test")
    print("=" * 60)
    
    # 1. Approval Key 발급
    print("\n[1/4] Getting Approval Key...")
    from src.data_ingestion.price.common import KISAuthManager
    auth = KISAuthManager()
    try:
        key = await auth.get_approval_key()
        print(f"✅ Key obtained: {key[:20]}...")
    except Exception as e:
        print(f"❌ Key failed: {e}")
        return
    
    # 2. WebSocket 연결
    url = "ws://ops.koreainvestment.com:21000/tryitout/H0STCNT0"
    print(f"\n[2/4] Connecting to {url}...")
    
    try:
        async with websockets.connect(
            url,
            ping_interval=20,
            ping_timeout=10
        ) as ws:
            print("✅ Connected!")
            
            # 3. 구독 요청 (삼성전자)
            print("\n[3/4] Sending subscription request for 005930...")
            req = {
                "header": {
                    "approval_key": key,
                    "custtype": "P",
                    "tr_type": "1",  # Subscribe
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
            print(f"Sent: {json.dumps(req, indent=2)}")
            
            # 4. 메시지 수신 및 분석
            print("\n[4/4] Receiving messages (max 15)...\n")
            
            for i in range(15):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    
                    print(f"\n{'='*60}")
                    print(f"MESSAGE #{i+1}")
                    print(f"{'='*60}")
                    print(f"Type: {type(msg)}")
                    print(f"Length: {len(msg)}")
                    print(f"First char: '{msg[0]}' (ord: {ord(msg[0])})")
                    
                    # JSON 시도
                    if msg[0] in ['{', '[']:
                        try:
                            parsed = json.loads(msg)
                            print(f"Format: JSON")
                            print(f"Content: {json.dumps(parsed, indent=2, ensure_ascii=False)}")
                        except:
                            print(f"Format: JSON-like but invalid")
                            print(f"Content: {msg[:300]}")
                    # Pipe 구분
                    elif '|' in msg:
                        parts = msg.split('|')
                        print(f"Format: Pipe-delimited")
                        print(f"Parts: {len(parts)}")
                        for idx, part in enumerate(parts[:5]):
                            print(f"  Part[{idx}]: {part[:100]}")
                    else:
                        print(f"Format: Unknown")
                        print(f"Content: {msg[:300]}")
                    
                except asyncio.TimeoutError:
                    print(f"\n⏱️  Timeout waiting for message #{i+1}")
                    break
                except Exception as e:
                    print(f"\n❌ Error receiving message: {e}")
                    break
            
            print(f"\n{'='*60}")
            print("Test Complete")
            print(f"{'='*60}")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    print("\n🔍 Starting KIS WebSocket Direct Test...\n")
    asyncio.run(test_kis_websocket())
