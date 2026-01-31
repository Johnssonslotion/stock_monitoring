
import pytest
import asyncio
import json
import redis.asyncio as redis
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from src.api.main import app
from src.api.routes.realtime import manager

# Use TestClient for WebSocket testing
client = TestClient(app)

@pytest.mark.asyncio
async def test_websocket_orderbook_stream():
    """
    통합 테스트: Redis Pub -> StreamManager -> WebSocket Client
    """
    # Initialize Manager Manually for test environment
    # start_listening is an infinite loop, so use create_task
    asyncio.create_task(manager.start_listening())
    await asyncio.sleep(0.1) # Wait for subscription
    
    symbol = "005930"
    channel = f"orderbook.kiwoom.{symbol}"
    
    # Use TestClient as context manager
    with client.websocket_connect(f"/ws/orderbook/{symbol}") as websocket:
        # 2. Publish Mock Data to Redis
        r = redis.from_url("redis://localhost:6379/0", decode_responses=True)
        
        mock_data = {
            "symbol": symbol,
            "ask_prices": [100.0] * 10,
            "type": "orderbook"
        }
        
        # We need to wait a bit for the background listener to pick up?
        # Actually StreamManager starts listener on app startup. 
        # TestClient triggers startup events.
        
        # Publish
        await r.publish(channel, json.dumps(mock_data))
        
        # 3. Receive from WebSocket
        # Wait with timeout
        data = websocket.receive_json()
        
        assert data['symbol'] == symbol
        assert data['ask_prices'][0] == 100.0
        
        await r.aclose()
