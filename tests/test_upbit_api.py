#!/usr/bin/env python3
"""
Upbit WebSocket API 테스트
실제로 데이터를 받을 수 있는지 확인
"""
import asyncio
import json
import aiohttp

async def test_upbit_websocket():
    url = "wss://api.upbit.com/websocket/v1"
    
    print(f"Connecting to {url}...")
    
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url) as ws:
            print("✅ Connected!")
            
            # Subscribe to KRW-BTC trades
            subscribe_data = [
                {"ticket": "test-ticket"},
                {"type": "trade", "codes": ["KRW-BTC"]}
            ]
            
            await ws.send_json(subscribe_data)
            print(f"📤 Sent subscription: {subscribe_data}")
            
            # Wait for messages (10 seconds)
            count = 0
            async for msg in ws:
                print(f"\n📥 Message #{count + 1}:")
                print(f"   Type: {msg.type}")
                
                if msg.type == aiohttp.WSMsgType.TEXT:
                    print(f"   TEXT: {msg.data[:200]}")
                elif msg.type == aiohttp.WSMsgType.BINARY:
                    data = json.loads(msg.data)
                    print(f"   BINARY (parsed): {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f"   ERROR: {msg.data}")
                    break
                
                count += 1
                if count >= 5:  # Stop after 5 messages
                    print("\n✅ Test successful! Received 5 messages.")
                    break
            
            if count == 0:
                print("❌ No messages received!")

if __name__ == "__main__":
    asyncio.run(test_upbit_websocket())
