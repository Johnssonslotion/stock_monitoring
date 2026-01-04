import asyncio
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any
import duckdb
import redis.asyncio as redis
from src.core.config import settings

logger = logging.getLogger(__name__)

class TickArchiver:
    """
    틱 데이터 아카이버 (Tick Archiver)
    
    Redis Pub/Sub에서 실시간 틱 데이터를 구독(Subscribe)하여,
    DuckDB를 통해 로컬 파일 시스템에 Parquet 포맷으로 영구 저장합니다.
    
    Strategies:
    1. **Batch Insert**: 매 건마다 DB에 쓰지 않고, 일정 수량(Batch)이나 주기에 따라 모아서 저장.
    2. **Partitioning**: 날짜별(Year/Month/Day)로 폴더를 구분하여 저장.
    """
    
    def __init__(self, batch_size: int = 100, flush_interval: int = 1):
        self.redis_url = settings.data.redis_url
        self.db_path = "data/market_data.duckdb"
        self.redis_client = None
        self.running = False
        
        self.batch_size = batch_size # 몇 개 모이면 저장할지
        self.flush_interval = flush_interval # 몇 초마다 저장할지 (Time-based flush)
        self.buffer: List[Dict[str, Any]] = []
        self.last_flush_time = datetime.now()
        
        # DuckDB Connection (Persistent)
        self._init_db()

    def _init_db(self):
        """DuckDB 초기화 및 테이블 생성"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = duckdb.connect(self.db_path)
        
        # 틱 데이터 테이블 (Raw Ticks)
        # Partitioning은 Parquet Export 시점에 수행하거나, 
        # DuckDB의 Hive Partitioning 기능을 활용.
        # 여기서는 일단 Hot Table(Insert용)을 만듦.
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ticks (
                source VARCHAR,
                symbol VARCHAR,
                timestamp BIGINT,
                price DOUBLE,
                volume DOUBLE,
                side VARCHAR,
                id VARCHAR,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info(f"Connected to DuckDB: {self.db_path}")

    async def connect_redis(self):
        self.redis_client = redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
        await self.redis_client.ping()

    async def flush_buffer(self):
        """버퍼에 있는 데이터를 DuckDB에 저장"""
        if not self.buffer:
            return

        try:
            # Bulk Insert using Appender or Insert Statement
            # DuckDB is fast enough for single-threaded batch inserts
            # Convert list of dicts to manageable format or Insert row by row?
            # Executemany is better.
            
            data_to_insert = [
                (
                    d.get("source"), d.get("symbol"), d.get("timestamp"),
                    d.get("price"), d.get("volume"), d.get("side"), d.get("id")
                )
                for d in self.buffer
            ]
            
            self.conn.executemany("""
                INSERT INTO ticks (source, symbol, timestamp, price, volume, side, id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, data_to_insert)
            
            # Simple Check
            count = self.conn.execute("SELECT count(*) FROM ticks").fetchone()[0]
            logger.info(f"Flushed {len(self.buffer)} ticks. Total: {count}")
            
            self.buffer.clear()
            self.last_flush_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to flush to DuckDB: {e}")

    async def run(self):
        self.running = True
        await self.connect_redis()
        
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("tick.*") # Pattern Subscribe
        logger.info("Subscribed to tick.* channels")

        try:
            while self.running:
                # 1. Message Handling (Non-blocking with timeout)
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
                
                if message:
                    data = json.loads(message["data"])
                    self.buffer.append(data)
                
                # 2. Flush Condition Check
                time_diff = (datetime.now() - self.last_flush_time).total_seconds()
                if len(self.buffer) >= self.batch_size or time_diff >= self.flush_interval:
                    await self.flush_buffer()
                    
                await asyncio.sleep(0.01) # Yield control
                
        except Exception as e:
            logger.error(f"Archiver Error: {e}")
        finally:
            self.conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    archiver = TickArchiver()
    asyncio.run(archiver.run())
