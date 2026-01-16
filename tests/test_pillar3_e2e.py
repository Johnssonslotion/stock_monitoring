import pytest
import redis.asyncio as redis
import json
import asyncio
import os
import asyncpg
from fastapi.testclient import TestClient
from src.api.main import app
from datetime import datetime, timezone

# 설정 (Docker 환경과 Local 환경 모두 지원)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
API_AUTH_SECRET = os.getenv("API_AUTH_SECRET", "super-secret-key")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "stockval")

@pytest.mark.asyncio
async def test_full_pipeline_e2e():
    """수집기(시뮬레이션) -> Redis -> Archiver -> DB -> API 전 과정 검증"""
    
    test_symbol = "E2E_FINAL_TEST"
    test_price = 99999.0
    
    # 1. Redis에 데이터 발행 (수집기 역할)
    r = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    payload = {
        "type": "ticker",
        "symbol": test_symbol,
        "price": test_price,
        "volume": 10,
        "change": 0.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await r.publish("market_ticker", json.dumps(payload))
    await r.close()
    
    # 2. Archiver가 DB에 저장할 때까지 대기 (최대 5초)
    # 아카이버는 Redis를 구독하고 즉시 DB에 Insert함.
    # 하지만 비동기 처리 및 DB I/O 지연을 고려하여 폴링하며 확인.
    
    conn = await asyncpg.connect(
        user="postgres", password="password", database=DB_NAME, host=DB_HOST
    )
    
    found = False
    for _ in range(10):  # 5초간 시도
        row = await conn.fetchrow("SELECT * FROM market_ticks WHERE symbol = $1", test_symbol)
        if row:
            found = True
            break
        await asyncio.sleep(0.5)
    
    await conn.close()
    assert found, "Data did not reach DB via Archiver pipeline"
    
    # 3. API를 통해 최종 데이터 조회 (대시보드 역할)
    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/ticks/{test_symbol}",
            headers={"x-api-key": API_AUTH_SECRET}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert data[0]["symbol"] == test_symbol
        assert data[0]["price"] == test_price

@pytest.mark.asyncio
async def test_websocket_broadcast_e2e():
    """수집기 -> Redis -> API WebSocket 브로드캐스트 검증"""
    # 이 테스트는 WebSocket을 직접 연결하여 메시지가 전송되는지 확인해야 함.
    # TestClient.websocket_connect를 사용.
    
    test_symbol = "WS_E2E_TEST"
    
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            # Redis에 데이터 발행
            r = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
            payload = {
                "type": "ticker",
                "symbol": test_symbol,
                "price": 55555.0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await r.publish("market_ticker", json.dumps(payload))
            await r.close()
            
            # WebSocket으로부터 메시지 수신 (최대 2초)
            # 수신 대기하는 동안 Redis Subscriber가 메시지를 가로챌 시간을 주어야 함.
            message = websocket.receive_text()
            data = json.loads(message)
            
            assert data["symbol"] == test_symbol
            assert data["price"] == 55555.0
