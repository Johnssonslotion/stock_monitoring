import pytest
import asyncio
import json
import os
from fastapi.testclient import TestClient
from src.api.main import app
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_system_ws():
    """System WebSocket 연결 및 데이터 수신 검증 (TestClient 활용)"""
    import os
    import redis.asyncio as redis
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    test_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "cpu_test",
        "value": 42.0
    }

    # TestClient의 startup 이벤트를 트리거하기 위해 context manager 사용
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            # 0.5초 대기하여 Redis 구독이 준비될 때까지 기다림
            await asyncio.sleep(0.5)
            
            # Redis에 데이터 발행
            r = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
            await r.publish("system.metrics", json.dumps(test_payload))
            await r.close()
            
            # WebSocket으로부터 메시지 수신 대기 (최대 3초)
            try:
                # TestClient.websocket_connect()의 receive_text()는 동기 함수임.
                # asyncio.to_thread를 사용하여 비동기 타임아웃 적용.
                message = await asyncio.wait_for(
                    asyncio.to_thread(websocket.receive_text), 
                    timeout=3.0
                )
                data = json.loads(message)
                assert data is not None
            except asyncio.TimeoutError:
                pytest.fail("WebSocket receive timeout: 메시지가 수신되지 않았습니다.")
            except Exception as e:
                pytest.fail(f"WebSocket Error: {e}")
