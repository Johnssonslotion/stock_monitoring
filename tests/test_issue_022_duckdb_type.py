
import asyncio
import os
import duckdb
import pytest
from datetime import datetime
from src.data_ingestion.ticks.archiver import TickArchiver

# Mock Settings for Testing
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

class TestTickArchiver(TickArchiver):
    def __init__(self, db_path=":memory:"):
        self.db_path = db_path
        # Skip os.makedirs for memory db
        self.conn = duckdb.connect(self.db_path)
        self._create_table()
        
        self.redis_client = None
        self.running = False
        self.batch_size = 10
        self.flush_interval = 1
        self.buffer = []
        self.last_flush_time = datetime.now()

    def _create_table(self):
        # Copied from original _init_db
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS market_ticks (
                symbol VARCHAR,
                timestamp TIMESTAMP,
                price DOUBLE,
                volume INT,
                source VARCHAR,
                execution_no VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


@pytest.mark.asyncio
async def test_duckdb_type_conversion():
    archiver = TestTickArchiver()
    
    # CASE 1: Unix Timestamp (int) - Seconds
    # 2026-01-20 00:00:00 UTC = 1768867200 (approx)
    ts_int = 1768867200
    
    # CASE 2: Unix Timestamp (float) - With milliseconds
    ts_float = 1768867200.123
    
    # CASE 3: ISO Format String
    ts_str = "2026-01-20T12:00:00.000000"
    
    # Add data to buffer
    archiver.buffer = [
        # int timestamp
        {
            "symbol": "KRW-BTC",
            "timestamp": ts_int,
            "price": 100000000.0,
            "volume": 1.0,
            "source": "TEST",
            "execution_no": "1"
        },
        # float timestamp
        {
            "symbol": "KRW-ETH",
            "timestamp": ts_float,
            "price": 5000000.0,
            "volume": 10.0,
            "source": "TEST",
            "execution_no": "2"
        },
        # string timestamp
        {
            "symbol": "AAPL",
            "timestamp": ts_str,
            "price": 150.0,
            "volume": 100.0,
            "source": "TEST",
            "execution_no": "3"
        }
    ]
    
    # Try Flush - This should FAIL before the fix, PASS after the fix
    try:
        await archiver.flush_buffer()
        print("Flush successful")
    except Exception as e:
        pytest.fail(f"Flush failed with error: {e}")
        
    # Verify Data
    result = archiver.conn.execute("SELECT symbol, timestamp FROM market_ticks ORDER BY execution_no").fetchall()
    
    assert len(result) == 3
    
    # Verify Types in DuckDB (should be datetime objects)
    print(f"Result 1 Timestamp Type: {type(result[0][1])} Value: {result[0][1]}")
    print(f"Result 2 Timestamp Type: {type(result[1][1])} Value: {result[1][1]}")
    print(f"Result 3 Timestamp Type: {type(result[2][1])} Value: {result[2][1]}")

    assert isinstance(result[0][1], datetime)
    assert isinstance(result[1][1], datetime)
    assert isinstance(result[2][1], datetime)

if __name__ == "__main__":
    # Manually run for quick check
    asyncio.run(test_duckdb_type_conversion())
