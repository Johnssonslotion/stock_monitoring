import pytest
import os
import duckdb
import asyncio
from src.data_ingestion.ticks.archiver import TickArchiver

# Test Config
TEST_DB_PATH = "data/test_market_data.duckdb"

@pytest.fixture
def archiver():
    # Ensure data directory exists
    os.makedirs(os.path.dirname(TEST_DB_PATH), exist_ok=True)
    
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except:
            pass
            
    archiver = TickArchiver(batch_size=2, flush_interval=10, db_path=TEST_DB_PATH) # 2개만 모여도 저장
    return archiver

@pytest.mark.asyncio
async def test_flush_buffer(archiver):
    """버퍼에 데이터가 찼을 때 DuckDB에 저장이 잘 되는지 테스트"""
    from datetime import datetime
    sample_ticks = [
        {"source": "upbit", "symbol": "KRW-BTC", "timestamp": datetime.now(), "price": 100.0, "volume": 1.0, "side": "ask", "execution_no": "1"},
        {"source": "upbit", "symbol": "KRW-BTC", "timestamp": datetime.now(), "price": 101.0, "volume": 2.0, "side": "bid", "execution_no": "2"}
    ]
    
    # 1. Fill Buffer
    archiver.buffer.extend(sample_ticks)
    
    # 2. Flush
    await archiver.flush_buffer()
    
    # 3. Verify
    conn = duckdb.connect(TEST_DB_PATH)
    # Schema: symbol, timestamp, price, volume, source, execution_no, created_at
    result = conn.execute("SELECT * FROM market_ticks ORDER BY execution_no").fetchall()
    conn.close()
    
    # (symbol, timestamp, price, volume, source, execution_no, created_at)
    assert len(result) == 2
    assert result[0][0] == "KRW-BTC"   # symbol is col 0
    assert result[0][2] == 100.0       # price is col 2
    assert result[0][5] == "1"         # execution_no is col 5
    
    # Cleanup
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_duckdb_schema(archiver):
    """테이블 스키마가 의도한 대로 생성되었는지 확인"""
    conn = duckdb.connect(TEST_DB_PATH)
    columns = conn.execute("DESCRIBE market_ticks").fetchall()
    conn.close()
    
    col_names = [col[0] for col in columns]
    assert "source" in col_names
    assert "price" in col_names
    assert "created_at" in col_names
    assert "execution_no" in col_names
