import pytest
import asyncio
import json
import asyncpg
import redis.asyncio as redis
from datetime import datetime
from src.data_ingestion.archiver.timescale_archiver import TimescaleArchiver, DB_USER, DB_PASSWORD, DB_NAME, DB_HOST, DB_PORT

@pytest.fixture(scope="module")
def archiver():
    return TimescaleArchiver()

@pytest.mark.asyncio
async def test_save_tick_to_timescale(archiver):
    """
    TimescaleArchiver의 틱 데이터 저장(flush) 루틴 검증
    """
    archiver.db_pool = await asyncpg.create_pool(
        user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
    )
    
    # 1. Prepare Batch
    archiver.batch = [
        (datetime.now(), "TEST_TICK", 50000.0, 100.0, 0.0)
    ]
    
    try:
        # 2. Flush
        await archiver.flush()
        
        # 3. Verify
        async with archiver.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM market_ticks WHERE symbol = 'TEST_TICK' ORDER BY time DESC LIMIT 1")
            assert row is not None
            assert row['symbol'] == "TEST_TICK"
            assert row['price'] == 50000.0
            
            # Cleanup
            await conn.execute("DELETE FROM market_ticks WHERE symbol = 'TEST_TICK'")
    finally:
        await archiver.db_pool.close()

@pytest.mark.asyncio
async def test_save_orderbook_to_timescale(archiver):
    """
    TimescaleArchiver의 호가 데이터 저장 루틴 검증
    """
    archiver.db_pool = await asyncpg.create_pool(
        user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
    )
    
    test_data = {
        "symbol": "TEST_OB",
        "timestamp": datetime.now().isoformat(),
        "asks": [{"price": 100.0, "vol": 10}, {"price": 101.0, "vol": 20}, {"price": 102.0, "vol": 30}, {"price": 103.0, "vol": 40}, {"price": 104.0, "vol": 50}],
        "bids": [{"price": 99.0, "vol": 15}, {"price": 98.0, "vol": 25}, {"price": 97.0, "vol": 35}, {"price": 96.0, "vol": 45}, {"price": 95.0, "vol": 55}]
    }
    
    try:
        await archiver.save_orderbook(test_data)
        
        async with archiver.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM market_orderbook WHERE symbol = 'TEST_OB' ORDER BY time DESC LIMIT 1")
            assert row is not None
            assert row['symbol'] == "TEST_OB"
            assert row['ask_price1'] == 100.0
            
            await conn.execute("DELETE FROM market_orderbook WHERE symbol = 'TEST_OB'")
    finally:
        await archiver.db_pool.close()
