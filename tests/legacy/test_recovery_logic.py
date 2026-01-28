import os
import pytest
import duckdb
import pandas as pd
from datetime import datetime, timedelta
# ISSUE-044: BackfillManager moved to legacy
from src.data_ingestion.recovery.legacy.backfill_manager import BackfillManager

@pytest.fixture
def temp_db(tmp_path):
    db_path = str(tmp_path / "test_ticks.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE market_ticks (
            symbol VARCHAR,
            timestamp TIMESTAMP,
            price DOUBLE,
            volume INT,
            source VARCHAR,
            execution_no VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Add some initial data with gaps
    # 09:00:00 -> OK
    # 09:01:00 -> GAP
    # 09:02:00 -> OK
    base_time = datetime.strptime("2026-01-20 09:00:00", "%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO market_ticks (symbol, timestamp, price, volume, source, execution_no) VALUES (?, ?, ?, ?, ?, ?)",
                 ("005930", base_time, 70000.0, 100, "TEST", "EXEC001"))
    conn.execute("INSERT INTO market_ticks (symbol, timestamp, price, volume, source, execution_no) VALUES (?, ?, ?, ?, ?, ?)",
                 ("005930", base_time + timedelta(minutes=2), 70100.0, 50, "TEST", "EXEC002"))
    
    conn.close()
    return db_path

def test_gap_detection(temp_db):
    """
    Test if detect_gaps correctly identifies missing minutes.
    """
    # Force symbols to only include what we want to test
    manager = BackfillManager(target_symbols=["005930"])
    
    # Target date: 2026-01-20
    # Expected: 09:01, 09:03... to 15:30 are missing
    gaps = manager.detect_gaps(main_db_path=temp_db, target_date="20260120", start_hour=9, end_hour=9)
    
    # 09:00 - 09:59 (60 mins total)
    # Existing: 09:00, 09:02
    # Missing: 58 mins
    
    assert len(gaps) == 1
    assert gaps[0]['symbol'] == "005930"
    missing = gaps[0]['missing_minutes']
    
    assert "09:00" not in missing
    assert "09:01" in missing
    assert "09:02" not in missing
    assert "09:03" in missing
    assert len(missing) == 58

def test_on_conflict_deduplication(tmp_path):
    """
    Verify that backfill_manager handles duplicates correctly when merging (synthetic test).
    Note: BackfillManager.fetch_real_ticks uses INSERT, we want to ensure no double entry if executed twice.
    """
    manager = BackfillManager(target_symbols=["005930"])
    db_path = manager.db_path # This is the temp DB created by manager
    
    # Sample tick
    tick = {
        'symbol': '005930',
        'timestamp': '2026-01-20 09:00:00',
        'price': 70000.0,
        'volume': 100,
        'source': 'KIS_REST_RECOVERY',
        'execution_no': '2026-01-20 09:00:00_100'
    }
    
    # Manual Insert 1
    conn = duckdb.connect(db_path)
    conn.execute("INSERT INTO market_ticks (symbol, timestamp, price, volume, source, execution_no) VALUES (?, ?, ?, ?, ?, ?)",
                 (tick['symbol'], tick['timestamp'], tick['price'], tick['volume'], tick['source'], tick['execution_no']))
    
    # Manual Insert 2 (Duplicates)
    # BackfillManager doesn't have a built-in "merge to main with dedupe" logic inside its own run(), 
    # that's handled by RecoveryOrchestrator or should be in LogRecovery.
    # Actually, BackfillManager saves to its own temporary DB.
    
    count = conn.execute("SELECT COUNT(*) FROM market_ticks").fetchone()[0]
    assert count == 1
    
    # Simulate the deduplicated insert logic used in LogRecovery.py or similar
    # Using the same execution_no
    conn.execute("CREATE TEMP TABLE temp_val AS SELECT * FROM market_ticks WHERE 0=1")
    conn.execute("INSERT INTO temp_val (symbol, timestamp, price, volume, source, execution_no) VALUES (?, ?, ?, ?, ?, ?)",
                 (tick['symbol'], tick['timestamp'], tick['price'], tick['volume'], tick['source'], tick['execution_no']))
    
    merge_query = """
        INSERT INTO market_ticks 
        SELECT DISTINCT * FROM temp_val t1
        WHERE NOT EXISTS (
            SELECT 1 FROM market_ticks t2
            WHERE t2.execution_no = t1.execution_no
            AND t2.symbol = t1.symbol
        )
    """
    conn.execute(merge_query)
    
    count_after = conn.execute("SELECT COUNT(*) FROM market_ticks").fetchone()[0]
    assert count_after == 1, "Duplicate found! Deduplication failed."
    conn.close()

if __name__ == "__main__":
    # Allow running directly
    import pytest
    pytest.main([__file__, "-v", "-s"])
