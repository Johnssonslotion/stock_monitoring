
import os
import duckdb
import pytest
from datetime import datetime, timedelta
from src.data_ingestion.ticks.validation_job import ValidationJob

# Helper to init DB for test
def init_test_db(db_path):
    conn = duckdb.connect(db_path)
    conn.execute("""
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_ticks_validation (
            bucket_time TIMESTAMP,
            symbol VARCHAR,
            tick_count_collected INT,
            volume_sum BIGINT,
            price_open DOUBLE,
            price_high DOUBLE,
            price_low DOUBLE,
            price_close DOUBLE,
            updated_at TIMESTAMP,
            validation_status VARCHAR,
            UNIQUE(bucket_time, symbol)
        )
    """)
    conn.close()

def test_validation_upsert():
    db_path = "data/test_validation.duckdb"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    init_test_db(db_path)
    
    conn = duckdb.connect(db_path)
    
    # 1. Insert Initial Data (09:00 - 3 ticks)
    ts_base = datetime(2026, 1, 20, 9, 0, 0)
    initial_data = [
        ('AAPL', ts_base + timedelta(seconds=10), 100.0, 10, 'TEST', '1'),
        ('AAPL', ts_base + timedelta(seconds=20), 101.0, 10, 'TEST', '2'),
        ('AAPL', ts_base + timedelta(seconds=30), 102.0, 10, 'TEST', '3'),
    ]
    conn.executemany("INSERT INTO market_ticks VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", initial_data)
    
    # 2. Run Validation Job
    job = ValidationJob(db_path=db_path)
    job.run_aggregation()
    
    # Verify Initial Count
    row = conn.execute("SELECT tick_count_collected, volume_sum FROM market_ticks_validation").fetchone()
    assert row[0] == 3
    assert row[1] == 30
    
    print(f"Initial Validation: Count={row[0]}, Vol={row[1]}")
    
    # 3. Add Late Data (Same Bucket - 2 more ticks) -> Simulating Recovery
    late_data = [
        ('AAPL', ts_base + timedelta(seconds=40), 103.0, 10, 'RECOVERY', '4'),
        ('AAPL', ts_base + timedelta(seconds=50), 104.0, 10, 'RECOVERY', '5'),
    ]
    conn.executemany("INSERT INTO market_ticks VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", late_data)
    
    # 4. Run Validation Job Again (Should Upsert)
    job.run_aggregation()
    
    # Verify Updated Count
    row_updated = conn.execute("SELECT tick_count_collected, volume_sum FROM market_ticks_validation").fetchone()
    assert row_updated[0] == 5  # 3 + 2
    assert row_updated[1] == 50 # 30 + 20
    
    print(f"Updated Validation: Count={row_updated[0]}, Vol={row_updated[1]}")
    
    conn.close()
    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    test_validation_upsert()
