import json
import os
import pytest
from src.data_ingestion.recovery.log_recovery import LogRecoveryManager

@pytest.fixture
def log_manager(tmp_path):
    db_path = str(tmp_path / "test_recovery.duckdb")
    log_dir = str(tmp_path / "logs")
    os.makedirs(log_dir, exist_ok=True)
    return LogRecoveryManager(db_path=db_path, log_dir=log_dir)

def test_parse_kiwoom_log_line(log_manager):
    """
    Test parsing a single Kiwoom WebSocket JSONL log line.
    """
    # Sample line from LogRecoveryManager._parse_line logic
    # Raw log format: {"ts": "2026-01-20T09:00:01.123456", "dir": "RX", "msg": "...JSON..."}
    
    # Kiwoom 'REAL' payload
    kiwoom_payload = {
        "trnm": "REAL",
        "data": [
            {
                "item": "005930",
                "type": "0B", # Tick
                "values": {
                    "10": "70000", # Price
                    "15": "100",   # Volume
                    "20": "090001" # Time (HHMMSS)
                }
            }
        ]
    }
    
    raw_line = {
        "ts": "2026-01-20T09:00:01.500000",
        "dir": "RX",
        "msg": json.dumps(kiwoom_payload)
    }
    
    line_str = json.dumps(raw_line)
    
    rows = log_manager._parse_line(line_str)
    
    assert rows is not None
    assert len(rows) == 1
    # Row format: (symbol, full_ts, abs(price), volume, "KIWOOM_LOG", execution_no)
    row = rows[0]
    assert row[0] == "005930"
    assert "09:00:01" in row[1]
    assert row[2] == 70000.0
    assert row[3] == 100
    assert row[4] == "KIWOOM_LOG"
    assert "09:00:01" in row[5] # execution_no contains timestamp

def test_parse_non_tick_message(log_manager):
    """
    Verify that non-tick (e.g., Orderbook 0A) messages are ignored.
    """
    kiwoom_payload = {
        "trnm": "REAL",
        "data": [
            {
                "item": "005930",
                "type": "0A", # Orderbook
                "values": {"10": "70000"} 
            }
        ]
    }
    raw_line = {"ts": "...", "msg": json.dumps(kiwoom_payload)}
    rows = log_manager._parse_line(json.dumps(raw_line))
    assert rows == [] # Empty list for non-matching type

def test_parse_invalid_json(log_manager):
    """
    Verify stability on invalid JSON.
    """
    assert log_manager._parse_line("invalid json") is None

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
