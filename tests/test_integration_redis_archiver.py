import pytest
import pytest_asyncio
import asyncio
import redis.asyncio as redis
import duckdb
import os
import json
from src.data_ingestion.ticks.archiver import TickArchiver
from src.core.config import settings

# Integration Test requires creating actual Redis connection
# and checking if data lands in DuckDB

TEST_DB_PATH = "data/test_integration_ticks.duckdb"
# Localhost access for tests running on host
REDIS_URL = "redis://localhost:6379/0" 

@pytest_asyncio.fixture
async def redis_client():
    client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    yield client
    await client.close()

@pytest.fixture
def clean_db():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

@pytest.mark.asyncio
async def test_archiver_integration_with_redis(redis_client, clean_db):
    """
    [Integration Test]
    Redis에 'tick.upbit.KRW-BTC'로 메시지를 쏘면,
    Archiver가 'tick.*' 패턴으로 받아서 DuckDB에 저장하는지 검증.
    (이 테스트가 있었으면 psubscribe 버그를 잡았을 것임)
    """
    
    # 1. Setup Archiver with Test DB Path
    # Dependency Injection allows us to use a test database
    archiver = TickArchiver(batch_size=1, flush_interval=1, db_path=TEST_DB_PATH)
    # archiver._init_db() is called in __init__, so no need to call it again or set path manually

    
    # Start Archiver in background task
    task = asyncio.create_task(archiver.run())
    
    # Wait for subscription (allow some time for connection)
    await asyncio.sleep(1.0) 
    
    # 2. Publish Message to Redis (Real Scenario)
    test_message = {
        "source": "upbit", 
        "symbol": "KRW-BTC", 
        "timestamp": 1234567890, 
        "price": 50000000.0, 
        "volume": 0.1, 
        "side": "bid", 
        "id": "integration_test_1"
    }
    
    # Channel matching the pattern tick.*
    channel = "tick.upbit.KRW-BTC"
    
    await redis_client.publish(channel, json.dumps(test_message))
    
    # 3. Wait for processing (flush_interval is 1s, gives buffer)
    await asyncio.sleep(2.0)
    
    # Stop Archiver
    archiver.running = False
    await task
    
    # 4. Verify DuckDB
    conn = duckdb.connect(TEST_DB_PATH, read_only=True)
    result = conn.execute("SELECT symbol, price FROM ticks WHERE id='integration_test_1'").fetchone()
    conn.close()
    
    assert result is not None, "Data not found in DuckDB! Archiver probably didn't receive the message."
    assert result[0] == "KRW-BTC"
    assert result[1] == 50000000.0
