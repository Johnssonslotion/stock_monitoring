
import asyncio
import os
import json
import logging
import glob
import duckdb
import asyncpg
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import pandas as pd
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LogRecovery")

# Config
DUCKDB_PATH = "data/ticks.duckdb"
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")

# Schema Mappings
KIWOOM_FID = {
    "20": "time",      # STCK_CNTG_HOUR (HHMMSS)
    "10": "price",     # STCK_PRPR
    "13": "volume",    # ACML_VOL (Cumulative)
    "15": "tick_vol",  # CNTG_VOL (Tick Volume)
    "11": "change"     # PRDY_VRSS
}

class LogRecovery:
    def __init__(self, date_str: str = None):
        self.date_str = date_str or datetime.now().strftime("%Y%m%d")
        self.duck_conn = None
        self.pg_pool = None
        self.stats = {"kis": 0, "kiwoom": 0, "errors": 0}

    async def connect_db(self):
        # DuckDB
        self.duck_conn = duckdb.connect(DUCKDB_PATH)
        # Ensure Table Exists
        self.duck_conn.execute("""
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
        
        # TimescaleDB
        try:
            self.pg_pool = await asyncpg.create_pool(
                user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
            )
            
            # Ensure Table Exists in Postgres
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS market_ticks (
                        time TIMESTAMPTZ NOT NULL,
                        symbol TEXT NOT NULL,
                        price DOUBLE PRECISION,
                        volume DOUBLE PRECISION,
                        change DOUBLE PRECISION
                    );
                """)
                # Try creating hypertable (ignore if exists)
                try:
                    await conn.execute("SELECT create_hypertable('market_ticks', 'time', if_not_exists => TRUE);")
                except Exception as e:
                    logger.warning(f"Hypertable creation failed (usually harmless if exists): {e}")

            logger.info("Connected to Databases & Schema Verified")
        except Exception as e:
            logger.error(f"Failed to connect to TimescaleDB: {e}")
            raise

    async def run(self):
        await self.connect_db()
        
        logger.info(f"🚀 Starting Recovery for Date: {self.date_str}")
        
        # 1. Recover KIS
        await self.recover_kis()
        
        # 2. Recover Kiwoom
        await self.recover_kiwoom()
        
        logger.info(f"✅ Recovery Completed. Stats: {self.stats}")
        self.duck_conn.close()
        await self.pg_pool.close()

    async def recover_kis(self):
        logger.info("--- Recovering KIS Data ---")
        files = glob.glob(f"data/raw/ws_raw_{self.date_str}_*.jsonl")
        
        batch = []
        BATCH_SIZE = 5000
        
        for filepath in files:
            logger.info(f"Processing KIS Log: {filepath}")
            try:
                with open(filepath, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            msg = data.get('msg', '')
                            # Expected: "0|H0STCNT0|001|SYMBOL^TIME^PRICE..."
                            if not msg.startswith("0|H0STCNT0"):
                                continue
                                
                            parts = msg.split('|')
                            if len(parts) < 4:
                                continue
                                
                            content = parts[3]
                            fields = content.split('^')
                            
                            symbol = fields[0]
                            time_str = fields[1] # HHMMSS
                            price = float(fields[2])
                            
                            # Construct Timestamp
                            dt_str = f"{self.date_str} {time_str}"
                            try:
                                ts = datetime.strptime(dt_str, "%Y%m%d %H%M%S")
                            except:
                                ts = datetime.now()

                            # KIS Volume Handling
                            try:
                                volume = int(fields[12]) 
                            except:
                                volume = 0
                            
                            record = {
                                "symbol": symbol,
                                "timestamp": ts,
                                "price": price,
                                "volume": volume,
                                "source": "KIS_RECOVERED"
                            }
                            batch.append(record)
                            self.stats["kis"] += 1
                            
                            if len(batch) >= BATCH_SIZE:
                                await self.insert_batch(batch)
                                batch = []
                                
                        except Exception as e:
                            self.stats["errors"] += 1
                            continue
                            
                # Flush Remaining for File
                if batch:
                    await self.insert_batch(batch)
                    batch = []
                    
            except Exception as e:
                logger.error(f"File Error {filepath}: {e}")

    async def recover_kiwoom(self):
        logger.info("--- Recovering Kiwoom Data ---")
        files = glob.glob(f"data/raw/kiwoom/ws_raw_{self.date_str}_*.jsonl")
        
        batch = []
        BATCH_SIZE = 5000
        
        for filepath in files:
            logger.info(f"Processing Kiwoom Log: {filepath}")
            try:
                with open(filepath, 'r') as f:
                    for line in f:
                        try:
                            # Log structure: {"ts": "...", "msg": "[{...}]"}
                            row = json.loads(line)
                            msg_str = row.get('msg', '[]')
                            
                            try:
                                ticks = json.loads(msg_str)
                            except:
                                continue
                                
                            if not isinstance(ticks, list):
                                ticks = [ticks]
                                
                            for tick in ticks:
                                if tick.get('type') != '0B': # Only '0B' is Tick
                                    continue
                                    
                                item_code = tick.get('item', '')
                                values = tick.get('values', {})
                                
                                # Parse Fields
                                time_str = values.get('20', '') # HHMMSS
                                if len(time_str) != 6:
                                    continue
                                    
                                dt_str = f"{self.date_str} {time_str}"
                                try:
                                    ts = datetime.strptime(dt_str, "%Y%m%d %H%M%S")
                                except:
                                    ts = datetime.now() # Fallback
                                    
                                price = abs(float(values.get('10', 0))) # Remove sign
                                volume = int(values.get('13', 0)) # Accum Vol
                                
                                record = {
                                    "symbol": item_code,
                                    "timestamp": ts,
                                    "price": price,
                                    "volume": volume,
                                    "source": "KIWOOM_RECOVERED"
                                }
                                batch.append(record)
                                self.stats["kiwoom"] += 1
                                
                            if len(batch) >= BATCH_SIZE:
                                await self.insert_batch(batch)
                                batch = []
                                
                        except Exception as e:
                            self.stats["errors"] += 1
                
                # Flush Remaining
                if batch:
                    await self.insert_batch(batch)
                    batch = []
                    
            except Exception as e:
                logger.error(f"File Error {filepath}: {e}")

    async def insert_batch(self, batch: List[Dict]):
        # 1. TimescaleDB (AsyncPG)
        try:
            async with self.pg_pool.acquire() as conn:
                # Prepare rows for copy
                rows = [
                    (r['timestamp'], r['symbol'], r['price'], float(r['volume']), 0.0)
                    for r in batch
                ]
                await conn.copy_records_to_table(
                    'market_ticks',
                    records=rows,
                    columns=['time', 'symbol', 'price', 'volume', 'change']
                    # Note: We skip 'source' in this table schema if it doesn't exist?
                    # TimescaleArchiver schema: time, symbol, price, volume, change.
                    # It DOES NOT have source in schema definition in archiver code (Step 1146 view).
                )
        except Exception as e:
            logger.error(f"PG Insert Error: {e}")

        # 2. DuckDB (Sync)
        try:
            # DuckDB accepts list of tuples
            # Schema: symbol, timestamp, price, volume, source, execution_no
            duck_rows = [
                (r['symbol'], r['timestamp'].isoformat(), r['price'], r['volume'], r['source'], 
                 f"{r['timestamp'].timestamp()}_{r['symbol']}")
                for r in batch
            ]
            self.duck_conn.executemany("""
                INSERT INTO market_ticks (symbol, timestamp, price, volume, source, execution_no)
                VALUES (?, CAST(? AS TIMESTAMP), ?, ?, ?, ?)
            """, duck_rows)
            
        except Exception as e:
            logger.error(f"DuckDB Insert Error: {e}")

if __name__ == "__main__":
    recovery = LogRecovery()
    asyncio.run(recovery.run())
