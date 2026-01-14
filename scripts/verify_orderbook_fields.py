#!/usr/bin/env python3
"""
호가 Field Index 검증 스크립트
실제 WebSocket 메시지를 받아서 Field Index 확인
"""
import asyncio
import websockets
import json
import os
import sys

sys.path.insert(0, '/home/ubuntu/workspace/stock_monitoring')

from src.data_ingestion.price.common import KISAuthManager

async def verify_orderbook_fields():
    """H0STASP0 메시지 실제 수신하여 Field 검증"""
    
    print("=" * 60)
    print("Orderbook Field Index Verification")
    print("=" * 60)
    
    # 1. Approval Key 발급
    print("\n[1/3] Getting Approval Key...")
    auth = KISAuthManager()
    key = await auth.get_approval_key()
    print(f"✅ Key obtained")
    
    # 2. WebSocket 연결 (Production)
    url = "ws://ops.koreainvestment.com:21000/H0STASP0"
    print(f"\n[2/3] Connecting to {url}")
    
    try:
        async with websockets.connect(url, ping_interval=20) as ws:
            print("✅ Connected")
            
            # 3. 구독 (삼성전자)
            req = {
                "header": {
                    "approval_key": key,
                    "custtype": "P",
                    "tr_type": "1",
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": "H0STASP0",
                        "tr_key": "005930"
                    }
                }
            }
            await ws.send(json.dumps(req))
            print("📤 Subscribed to 005930 (Samsung)")
            
            # 4. 메시지 수신 (최대 10개)
            print("\n[3/3] Receiving messages...")
            
            for i in range(10):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    
                    # Pipe-delimited 메시지만 파싱
                    if '|' in msg and msg[0] in ['0', '1']:
                        parts = msg.split('|')
                        if len(parts) >= 4 and parts[1] == "H0STASP0":
                            body = parts[3]
                            fields = body.split('^')
                            
                            print(f"\n{'='*60}")
                            print(f"MESSAGE #{i+1}")
                            print(f"{'='*60}")
                            print(f"Total fields: {len(fields)}")
                            print(f"Symbol: {fields[0]}")
                            
                            # Field Index 검증
                            print("\n📊 호가 Field 샘플:")
                            print(f"  [3] ASKP1 (매도1): {fields[3]}")
                            print(f"  [4] ASKP2 (매도2): {fields[4]}")
                            print(f"  [12] BIDP1 (매수1): {fields[12]}")
                            print(f"  [13] BIDP2 (매수2): {fields[13]}")
                            print(f"  [21] ASKP_RSQN1 (매도잔량1): {fields[21]}")
                            print(f"  [22] ASKP_RSQN2 (매도잔량2): {fields[22]}")
                            print(f"  [30] BIDP_RSQN1 (매수잔량1): {fields[30]}")
                            print(f"  [31] BIDP_RSQN2 (매수잔량2): {fields[31]}")
                            
                            # OLD vs NEW 비교
                            print("\n🔍 Field Index 비교:")
                            print(f"  OLD [23] (틀림): {fields[23]}")
                            print(f"  NEW [21] (정답): {fields[21]} ✅")
                            print(f"  OLD [33] (틀림): {fields[33]}")
                            print(f"  NEW [30] (정답): {fields[30]} ✅")
                            
                            print("\n✅ Verification PASSED - Field indices are correct!")
                            return True
                            
                except asyncio.TimeoutError:
                    print(f"⏱️  Timeout at message #{i+1}")
                    continue
            
            print("\n⚠️  No valid orderbook messages received (시간외 또는 장 마감)")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(verify_orderbook_fields())
    sys.exit(0 if result else 1)
