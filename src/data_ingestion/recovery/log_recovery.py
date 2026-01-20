import os
import json
import logging
import glob
import duckdb
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LogRecoveryManager")

class LogRecoveryManager:
    """
    [ISSUE-031] Primary Recovery: Log Recovery Manager
    Parses raw JSONL logs and bulk inserts them into DuckDB Market Ticks table.
    """

    def __init__(self, db_path: str = "data/ticks.duckdb", log_dir: str = "data/raw/kiwoom"):
        self.db_path = db_path
        self.log_dir = log_dir
        self.conn = None
        
    def connect(self):
        """Connect to DuckDB"""
        try:
            self.conn = duckdb.connect(self.db_path)
            # Ensure table exists (Idempotent)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS market_ticks (
                    symbol VARCHAR,
                    timestamp TIMESTAMP,
                    price DOUBLE,
                    volume INTEGER,
                    source VARCHAR,
                    execution_no VARCHAR
                )
            """)
            logger.info(f"✅ Connected to DuckDB: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ DB Connection Failed: {e}")
            raise

    def close(self):
        """Close DB Connection"""
        if self.conn:
            self.conn.close()
            logger.info("🔌 DB Connection Closed")

    def _parse_line(self, line: str) -> Optional[Tuple]:
        """Parse a single JSONL line into a tuple for DuckDB"""
        try:
            data = json.loads(line)
            # Supporting multiple potential formats from different loggers
            
            # 1. Standard Kiwoom WS Log Format
            # Kiwoom WS logic might wrap data. Structure depends on `RawWebSocketLogger`
            # Typically: {"timestamp": "...", "data": "..."} or direct message
            
            # Let's assume the raw log contains the direct WebSocket message or a wrapped version
            # Based on `kiwoom_ws.py`, it logs `raw_data`. 
            # `RawWebSocketLogger` typically logs: {"timestamp": ..., "direction": "RX", "data": ...}
            
            payload = data.get("data")
            if not payload:
                # Try direct if not wrapped
                payload = data
            
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except:
                    return None # Non-JSON string

            # Kiwoom 'REAL' Message Only
            trnm = payload.get("trnm")
            if trnm != "REAL":
                return None

            real_data = payload.get("data", [])
            extracted_rows = []
            
            for item in real_data:
                # values: { '10': '000660', '20': '145000', ... } or mapped keys
                # `KiwoomTickData.from_ws_json` uses fields. 
                # Raw logs might be 'mapped' or 'raw fid'. 
                # Assuming `kiwoom_ws.py` logic: It receives JSON with mapped keys if coming from mock
                # OR if coming from API, it is parsed then logged? 
                # Wait, `RawWebSocketLogger` logs `raw_data` passed to `_handle_message`.
                # In `kiwoom_ws.py`: `data = json.loads(raw_data)`. 
                # So the log contains the JSON structure from Kiwoom.
                
                # Kiwoom JSON format (assumed based on previous view):
                # { "trnm": "REAL", "data": [ { "item": "005930", "values": { ... } } ] }
                
                symbol = item.get("item")
                values = item.get("values", {})
                msg_type = item.get("type")
                
                if msg_type != "0B": # Only process Ticks (0B)
                    continue

                # Parse Fields (standardized keys or FID?)
                # Kiwoom WS usually sends FIDs (20: price, 15: volume, 16: time, etc.)
                # But `kiwoom_ws.py` (mock/wrapper) uses keys like 'st_price', 'cvolume' etc?
                # Let's look at `KiwoomTickData.from_ws_json` if possible, but safe to assume keys
                # might be varying. Implementation plan didn't specify strict schema.
                # Use basic parsing logic.
                
                # Try common keys
                price = float(values.get("cprice") or values.get("20") or values.get("10") or 0) # 10 is current price usually, 20? 
                # Let's rely on standard names if available, else FID.
                # Kiwoom FIDs: 20(ChegyeolTime), 10(CurrentPrice), 15(Vol)
                
                # Actually, `kiwoom_ws` Mock sends: `stck_cntg_hour` etc? 
                # Safe bet: `KiwoomTickData` schema.
                
                # If we don't have the schema, we parse defensively.
                
                # Time
                tick_time = values.get("cntg_hour") or values.get("20") # 20 is time in real
                today = datetime.now().strftime("%Y-%m-%d") # Log doesn't have date usually?
                # Actually `RawWebSocketLogger` wrapper has outer timestamp. Use that if possible.
                
                outer_ts = data.get("timestamp") # ISO string from wrapper
                if outer_ts:
                    # Prefer outer timestamp for consistency with log time
                    # But tick time is more accurate for market data.
                    # Mix: Date from outer, Time from tick.
                    try:
                        dt_obj = datetime.fromisoformat(outer_ts)
                        date_str = dt_obj.strftime("%Y-%m-%d")
                    except:
                        date_str = datetime.now().strftime("%Y-%m-%d")
                else:
                    date_str = datetime.now().strftime("%Y-%m-%d")

                if tick_time:
                    # Format HHMMSS
                    full_ts = f"{date_str} {tick_time[:2]}:{tick_time[2:4]}:{tick_time[4:6]}.000000"
                elif outer_ts:
                    full_ts = outer_ts.replace("T", " ")
                else:
                    full_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.000000")

                volume = int(values.get("cntg_vol") or values.get("15") or 0)
                
                # Execution NO: Synthetic (Time + Vol + Symbol)
                execution_no = f"{full_ts}_{volume}_{symbol}"
                
                extracted_rows.append((symbol, full_ts, abs(price), volume, "KIWOOM_LOG", execution_no))
                
            return extracted_rows

        except Exception as e:
            # logger.debug(f"Parse Error line: {e}") 
            return None

    def recover_from_date(self, target_date: str):
        """
        Recover ticks from logs for a specific date (YYYYMMDD).
        Files: ws_raw_{date}_*.jsonl
        """
        pattern = os.path.join(self.log_dir, f"ws_raw_{target_date}_*.jsonl")
        files = glob.glob(pattern)
        
        if not files:
            logger.warning(f"No log files found for date {target_date} in {self.log_dir}")
            return

        logger.info(f"📂 Found {len(files)} log files for {target_date}. Starting recovery...")
        
        all_ticks = []
        
        for file_path in files:
            logger.info(f"Programming {file_path}...")
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    parsed_list = self._parse_line(line)
                    if parsed_list:
                        all_ticks.extend(parsed_list)

        if not all_ticks:
            logger.warning("No valid ticks parsed from logs.")
            return

        # Deduplication (Python side or SQL side)
        # SQL SIDE: INSERT OR IGNORE / WHERE NOT EXISTS
        # DuckDB doesn't have INSERT OR IGNORE in older versions? 
        # Use ON CONFLICT DO NOTHING if key exists? No PK defined in standard schema usually.
        # Use `INSERT INTO ... SELECT ... WHERE NOT EXISTS ...`
        
        logger.info(f"💾 Inserting {len(all_ticks)} ticks into DuckDB...")
        
        # Temp Table approach for bulk insert & dedupe
        self.conn.execute("CREATE TEMP TABLE temp_recovery AS SELECT * FROM market_ticks WHERE 0=1")
        
        # Bulk Insert to Temp
        self.conn.executemany("INSERT INTO temp_recovery VALUES (?, ?, ?, ?, ?, ?)", all_ticks)
        
        # Merge to Main
        query = """
            INSERT INTO market_ticks 
            SELECT DISTINCT * FROM temp_recovery t1
            WHERE NOT EXISTS (
                SELECT 1 FROM market_ticks t2
                WHERE t2.execution_no = t1.execution_no
                AND t2.symbol = t1.symbol
            )
        """
        result = self.conn.execute(query).fetchall()
        # DuckDB usually returns count of inserted rows
        
        logger.info(f"✅ Recovery Complete. Rows Processed: {len(all_ticks)}")
        self.conn.execute("DROP TABLE temp_recovery")

if __name__ == "__main__":
    # Test Run
    manager = LogRecoveryManager()
    manager.connect()
    # manager.recover_from_date("20260120")
    manager.close()
