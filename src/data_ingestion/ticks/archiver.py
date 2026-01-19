import asyncio
import json
import logging
import os
import glob
from datetime import datetime
from typing import List, Dict, Any
import duckdb
import redis.asyncio as redis
from src.core.config import settings

logger = logging.getLogger(__name__)

class TickArchiver:
    """
    틱 데이터 아카이버 (Tick Archiver)
    
    1. Redis Pub/Sub -> DuckDB (Realtime)
    2. Recovery Files -> DuckDB (Merge Worker)
    """
    
    def __init__(self, batch_size: int = 100, flush_interval: int = 1, db_path: str = "data/ticks.duckdb"):
        self.redis_url = settings.data.redis_url
        self.db_path = db_path

        self.redis_client = None
        self.running = False
        
        self.batch_size = batch_size 
        self.flush_interval = flush_interval
        self.buffer: List[Dict[str, Any]] = []
        self.last_flush_time = datetime.now()
        self.last_merge_check = datetime.now()
        
        # Recovery Config
        self.recovery_dir = "data/recovery"
        
        # DuckDB Connection (Persistent)
        self._init_db()

    def _init_db(self):
        """DuckDB 초기화 및 테이블 생성"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = duckdb.connect(self.db_path)
        
        # Unified Schema (matched with BackfillManager)
        # Table name: market_ticks
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
        
        # Create unique index for deduplication if possible, 
        # but DuckDB indexes are limited. We use INSERT INSERT/SELECT strategies.
        logger.info(f"Connected to DuckDB: {self.db_path}")

    async def connect_redis(self):
        self.redis_client = redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
        await self.redis_client.ping()

    async def flush_buffer(self):
        """버퍼에 있는 데이터를 DuckDB에 저장"""
        if not self.buffer:
            return

        try:
            # Buffer -> List of Tuples
            # Schema: symbol, timestamp, price, volume, source, execution_no
            data_to_insert = []
            for d in self.buffer:
                # Redis message format might vary, standardize it
                # Assuming data object from Pydantic model dump
                symbol = d.get("symbol")
                timestamp = d.get("timestamp") or d.get("dt") # Handle alias
                price = d.get("price")
                volume = d.get("volume")
                source = d.get("source", "REALTIME")
                execution_no = str(d.get("execution_no", "")) # execution_id?
                
                # Timestamp conversion if string
                # DuckDB handles ISO strings well usually
                
                data_to_insert.append((symbol, timestamp, price, volume, source, execution_no))
            
            self.conn.executemany("""
                INSERT INTO market_ticks (symbol, timestamp, price, volume, source, execution_no)
                VALUES (?, ?, ?, ?, ?, ?)
            """, data_to_insert)
            
            self.buffer.clear()
            self.last_flush_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to flush to DuckDB: {e}")

    def merge_recovery_files(self):
        """
        [Hybird Architecture]
        Checks 'data/recovery' for new temp DB files and merges them.
        Executed within the main process to allow Shared Lock / Owner Access.
        """
        pattern = os.path.join(self.recovery_dir, "recovery_temp_*.duckdb")
        temp_files = glob.glob(pattern)
        
        if not temp_files:
            return

        logger.info(f"🔄 Discovered {len(temp_files)} recovery files. Merging...")
        
        for temp_file in temp_files:
            try:
                # 1. ATTACH
                # Use a unique alias based on file hash or simply temp_db_{timestamp}
                # But since we do one by one, 'temp_rec' is fine.
                self.conn.execute(f"ATTACH '{temp_file}' AS temp_rec")
                
                # 2. MERGE (Deduplication)
                # Select only rows that don't exist in main table
                query = """
                    INSERT INTO market_ticks 
                    SELECT * FROM temp_rec.market_ticks t1
                    WHERE NOT EXISTS (
                        SELECT 1 FROM market_ticks t2 
                        WHERE t2.execution_no = t1.execution_no
                        AND t2.symbol = t1.symbol
                    )
                """
                self.conn.execute(query)
                
                # 3. DETACH
                self.conn.execute("DETACH temp_rec")
                
                # 4. DELETE
                os.remove(temp_file)
                logger.info(f"✅ Merged and deleted: {os.path.basename(temp_file)}")
                
            except Exception as e:
                logger.error(f"❌ Failed to merge {temp_file}: {e}")
                try: self.conn.execute("DETACH temp_rec") 
                except: pass

    async def run(self):
        self.running = True
        await self.connect_redis()
        
        pubsub = self.redis_client.pubsub()
        await pubsub.psubscribe("market:ticks", "tick.*") # Updated channel name
        logger.info("Subscribed to market:ticks / tick.*")

        try:
            while self.running:
                # 1. Message Handling
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
                
                if message:
                    try:
                        data = json.loads(message["data"])
                        self.buffer.append(data)
                    except: 
                        pass
                
                now = datetime.now()
                
                # 2. Flush Check
                time_diff = (now - self.last_flush_time).total_seconds()
                if len(self.buffer) >= self.batch_size or time_diff >= self.flush_interval:
                    await self.flush_buffer()
                
                # 3. Recovery Merge Check (Every 5 seconds)
                merge_diff = (now - self.last_merge_check).total_seconds()
                if merge_diff >= 5.0:
                    # Run sync blocking IO in main loop? 
                    # Merging is disk-heavy. Ideally thread pool, but DuckDB connection isn't thread-safe?
                    # DuckDB connection IS thread-safe but we must be careful.
                    # For simplicty in Python Asyncio: it will block the event loop.
                    # Given low frequency of recovery (on-demand), blocking for 100-200ms is Acceptable.
                    self.merge_recovery_files()
                    self.last_merge_check = now
                    
                await asyncio.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Archiver Error: {e}")
        finally:
            self.conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        archiver = TickArchiver()
        asyncio.run(archiver.run())
    except KeyboardInterrupt:
        pass
