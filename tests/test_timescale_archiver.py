import pytest
import asyncio
import json
import asyncpg
import redis.asyncio as redis
from datetime import datetime
from src.data_ingestion.archiver.timescale_archiver import TimescaleArchiver, DB_USER, DB_PASSWORD, DB_NAME, DB_HOST, DB_PORT

@pytest.fixture
async def db_pool():
    # Use a small pool for testing to avoid connection leaks
    pool = await asyncpg.create_pool(
        user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT,
        min_size=1, max_size=2
    )
    yield pool
    await pool.close()

@pytest.fixture
def archiver(db_pool):
    arch = TimescaleArchiver()
    arch.db_pool = db_pool
    return arch

@pytest.mark.asyncio
async def test_save_tick_to_timescale(archiver):
    """
    TimescaleArchiver의 틱 데이터 저장(flush) 루틴 검증
    """
    # 1. Prepare Batch (10 columns: time, symbol, price, volume, change, broker, broker_time, received_time, sequence_number, source)
    now = datetime.now()
    archiver.batch = [
        (now, "TEST_TICK", 50000.0, 100.0, 0.0, "TEST_BROKER", now, now, 1, "KIS")
    ]
    
    # 2. Flush
    await archiver.flush()
    
    # 3. Verify
    async with archiver.db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM market_ticks WHERE symbol = 'TEST_TICK' ORDER BY time DESC LIMIT 1")
        assert row is not None
        assert row['symbol'] == "TEST_TICK"
        assert row['price'] == 50000.0
        assert row['source'] == "KIS"
        
        # Cleanup
        await conn.execute("DELETE FROM market_ticks WHERE symbol = 'TEST_TICK'")

@pytest.mark.asyncio
async def test_save_orderbook_to_timescale(archiver):
    """
    TimescaleArchiver의 호가 데이터 저장 루틴 검증
    """
    test_data = {
        "symbol": "TEST_OB",
        "timestamp": datetime.now().isoformat(),
        "asks": [{"price": 100.0, "vol": 10}, {"price": 101.0, "vol": 20}, {"price": 102.0, "vol": 30}, {"price": 103.0, "vol": 40}, {"price": 104.0, "vol": 50}],
        "bids": [{"price": 99.0, "vol": 15}, {"price": 98.0, "vol": 25}, {"price": 97.0, "vol": 35}, {"price": 96.0, "vol": 45}, {"price": 95.0, "vol": 55}]
    }
    
    await archiver.save_orderbook(test_data)
    
    async with archiver.db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM market_orderbook WHERE symbol = 'TEST_OB' ORDER BY time DESC LIMIT 1")
        assert row is not None
        assert row['symbol'] == "TEST_OB"
        assert row['ask_price1'] == 100.0
        
        await conn.execute("DELETE FROM market_orderbook WHERE symbol = 'TEST_OB'")

@pytest.mark.asyncio
async def test_save_system_metrics(archiver):
    """
    TimescaleArchiver의 시스템 메트릭 저장 루틴 검증
    """
    test_data = {
        "timestamp": datetime.now().isoformat(),
        "type": "test_metric",
        "value": 42.5,
        "meta": {"test": "label"}
    }
    
    await archiver.save_system_metrics(test_data)
    
    async with archiver.db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM system_metrics WHERE metric_name = 'test_metric' ORDER BY time DESC LIMIT 1")
        assert row is not None
        assert row['value'] == 42.5
        assert json.loads(row['labels']) == {"test": "label"}
        
        await conn.execute("DELETE FROM system_metrics WHERE metric_name = 'test_metric'")

@pytest.mark.asyncio
async def test_handle_pmessage_routing(archiver):
    """
    PubSub 메시지 라우팅(handle_pmessage) 로직 검증
    """
    # 1. Tick message
    tick_msg = {
        "pattern": "tick:*",
        "channel": "tick:KR",
        "data": json.dumps({
            "symbol": "ROUTE_TICK",
            "price": 1000.0,
            "timestamp": datetime.now().isoformat()
        })
    }
    await archiver.handle_pmessage(tick_msg)
    assert len(archiver.batch) == 1
    assert archiver.batch[0][1] == "ROUTE_TICK"
    archiver.batch = [] # Reset
    
    # 2. Orderbook message
    ob_msg = {
        "pattern": "orderbook.*",
        "channel": "orderbook.KR",
        "data": json.dumps({
            "symbol": "ROUTE_OB",
            "timestamp": datetime.now().isoformat(),
            "asks": [{"price": 100, "vol": 1}],
            "bids": [{"price": 99, "vol": 1}]
        })
    }
    await archiver.handle_pmessage(ob_msg)
    
    async with archiver.db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM market_orderbook WHERE symbol = 'ROUTE_OB'")
        assert row is not None
        await conn.execute("DELETE FROM market_orderbook WHERE symbol = 'ROUTE_OB'")

@pytest.mark.asyncio
async def test_init_db_verification(archiver):
    """
    TimescaleArchiver.init_db()의 스키마 검증 로직 확인
    """
    # 정상 케이스: 테이블이 모두 존재하는 경우 예외가 발생하지 않아야 함
    await archiver.init_db()
    
    # 비정상 케이스: 존재하지 않는 테이블을 체크할 경우 RuntimeError 발생 확인
    # (테스트를 위해 잠시 required_tables를 조작하거나, DB에서 테이블 하나를 드롭할 수 있음)
    # 여기서는 간단히 성공 케이스만 확인
