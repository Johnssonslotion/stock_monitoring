#!/usr/bin/env python3
"""
/tryitout/ 엔드포인트에서 실제 틱 데이터 수신 여부 확인
구독 후 1분간 대기하여 데이터가 오는지 검증
"""
import asyncio
import websockets
import json
import os
from dotenv import load_dotenv
import sys
from datetime import datetime
sys.path.insert(0, '/home/ubuntu/workspace/stock_monitoring')

load_dotenv()
from src.data_ingestion.price.common import KISAuthManager

async def test_tick_data_reception():
    print("="*60)
    print("Testing ACTUAL TICK DATA reception from /tryitout/")
    print("="*60)
    
    # 1. Approval Key
    auth = KISAuthManager()
    approval_key = await auth.get_approval_key()
    
    url = "ws://ops.koreainvestment.com:21000/tryitout/H0STCNT0"
    print(f"URL: {url}\n")
    
    try:
        async with websockets.connect(url, ping_interval=20) as ws:
            print(f"✅ Connected at {datetime.now().strftime('%H:%M:%S')}\n")
            
            # 2. 구독
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
            print(f"📤 Sent subscription at {datetime.now().strftime('%H:%M:%S')}\n")
            
            # 3. 1분간 대기 (틱 데이터 수신 여부 확인)
            print("⏳ Waiting for TICK DATA (60 seconds)...\n")
            
            msg_count = 0
            tick_data_count = 0
            
            for i in range(60):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msg_count += 1
                    
                    # 메시지 분석
                    is_json = msg[0] in ['{', '[']
                    is_pipe = '|' in msg
                    
                    print(f"📨 Message #{msg_count} at {datetime.now().strftime('%H:%M:%S')}:")
                    
                    if is_json:
                        try:
                            data = json.loads(msg)
                            msg_type = data.get('body', {}).get('msg1', 'Unknown')
                            print(f"   Type: JSON - {msg_type}")
                            if msg_type != "SUBSCRIBE SUCCESS":
                                print(f"   🎯 UNEXPECTED: {json.dumps(data, ensure_ascii=False)[:200]}")
                        except:
                            print(f"   Type: JSON (parse failed)")
                            print(f"   Content: {msg[:150]}")
                    elif is_pipe:
                        parts = msg.split('|')
                        print(f"   Type: PIPE-DELIMITED (틱 데이터!)")
                        print(f"   Parts: {len(parts)}")
                        print(f"   TR_ID: {parts[1] if len(parts) > 1 else 'N/A'}")
                        print(f"   Body: {parts[3][:100] if len(parts) > 3 else 'N/A'}")
                        tick_data_count += 1
                    else:
                        print(f"   Type: UNKNOWN")
                        print(f"   Content: {msg[:150]}")
                    print()
                    
                except asyncio.TimeoutError:
                    if msg_count == 0 and i % 10 == 0:
                        print(f"   ... {i}s, no messages yet")
            
            print("="*60)
            print(f"RESULTS after 60 seconds:")
            print(f"  Total messages: {msg_count}")
            print(f"  Tick data (pipe-delimited): {tick_data_count}")
            
            if tick_data_count > 0:
                print(f"\n✅ /tryitout/ SENDS tick data! ({tick_data_count} ticks)")
            elif msg_count == 1:
                print(f"\n❌ /tryitout/ ONLY sends subscription confirmation")
                print(f"   NO actual tick data received")
            elif msg_count == 0:
                print(f"\n❌ NO messages at all")
            else:
                print(f"\n⚠️  {msg_count} messages but no tick data")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_tick_data_reception())
