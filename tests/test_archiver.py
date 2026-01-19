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
    sample_ticks = [
        {"source": "upbit", "symbol": "KRW-BTC", "timestamp": 100, "price": 100.0, "volume": 1.0, "side": "ask", "id": "1"},
        {"source": "upbit", "symbol": "KRW-BTC", "timestamp": 200, "price": 101.0, "volume": 2.0, "side": "bid", "id": "2"}
    ]
    
    # 1. Fill Buffer
    archiver.buffer.extend(sample_ticks)
    
    # 2. Flush
    await archiver.flush_buffer()
    
    # 3. Verify
    conn = duckdb.connect(TEST_DB_PATH)
    result = conn.execute("SELECT * FROM ticks ORDER BY id").fetchall()
    conn.close()
    
    # (source, symbol, timestamp, price, volume, side, id, ingested_at)
    assert len(result) == 2
    assert result[0][1] == "KRW-BTC"
    assert result[0][3] == 100.0 # Price
    assert result[1][5] == "bid" # Side
    
    # Cleanup
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_duckdb_schema(archiver):
    """테이블 스키마가 의도한 대로 생성되었는지 확인"""
    conn = duckdb.connect(TEST_DB_PATH)
    columns = conn.execute("DESCRIBE ticks").fetchall()
    conn.close()
    
    col_names = [col[0] for col in columns]
    assert "source" in col_names
    assert "price" in col_names
    assert "ingested_at" in col_names
