import asyncio
import websockets
import json
import os

async def test_system_ws():
    uri = "ws://localhost:8000/ws"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Waiting for metrics...")
            # Sentinel usually sends metrics every 5s now
            for _ in range(3):
                message = await websocket.recv()
                data = json.loads(message)
                print(f"Received: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_system_ws())
