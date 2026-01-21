import asyncio
import logging
import json
import os
import asyncpg
import redis.asyncio as redis
from datetime import datetime

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TimescaleArchiver")

# Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")

BATCH_SIZE = 100
FLUSH_INTERVAL = 5  # seconds

class TimescaleArchiver:
    """Redis에서 데이터를 구독하여 TimescaleDB에 시계열로 저장하는 아카이버"""
    def __init__(self):
        self.redis = None
        self.db_pool = None
        self.batch = []
        self.running = True

    async def _record_db_success(self, count: int):
        """
        ISSUE-035: Record successful DB ingestion for monitoring
        Updates Redis key with latest success timestamp and count
        """
        try:
            now = datetime.now().isoformat()
            await self.redis.set("archiver:last_db_success", now)
            await self.redis.set("archiver:last_flush_count", count)
            await self.redis.set("archiver:last_flush_time", now)
        except Exception as e:
            logger.warning(f"Failed to record DB success metric: {e}")

    async def init_db(self):
        """
        [ISSUE-036 Revision] 
        기존 하드코딩된 DDL을 제거하고 마이그레이션 도구(migrate.sh)를 통해 관리하도록 위임합니다.
        여기서는 필수 테이블 존재 여부만 검증합니다.
        """
        conn = await asyncpg.connect(
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        try:
            # 필수 테이블 존재 여부 확인 (SSoT: migrations/)
            required_tables = ['market_ticks', 'market_orderbook', 'system_metrics']
            for table in required_tables:
                exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                    table
                )
                if not exists:
                    logger.error(f"CRITICAL: Table '{table}' not found. Please run 'make migrate-up' first.")
                    # 운영 환경에서는 즉시 중단하여 정합성 훼손 방지
                    raise RuntimeError(f"Database schema incomplete: table '{table}' missing.")
            
            logger.info("Database schema verification completed (SSoT: Migrations).")
        finally:
            await conn.close()

    async def start(self):
        # 1. Connect to Resources
        self.redis = await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        # Create DB Pool
        self.db_pool = await asyncpg.create_pool(
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        
        await self.init_db()
        logger.info("TimescaleArchiver started. Connected to Redis & DB.")


        # 2. Subscribe to pattern (ticker.kr, ticker.us, orderbook.kr, orderbook.us, system.*)
        # [ISSUE-030] Add tick:* for Kiwoom/Standardized channels
        pubsub = self.redis.pubsub()
        await pubsub.psubscribe("ticker.*", "tick:*", "orderbook.*", "system.*")
        logger.info("📡 Subscribed to: ticker.*, tick:*, orderbook.*, system.*")
        
        # 3. Flush Task
        asyncio.create_task(self.periodic_flush())

        # 4. Listen Loop
        logger.info("🔧 DEBUG: Entering listen loop...")
        async for message in pubsub.listen():
            msg_type = message["type"]

            
            if msg_type == "pmessage":  # Pattern message
                try:
                    channel = message["channel"]
                    data = json.loads(message["data"])
                    
                    # Handle both ticker.* (KIS) and tick:* (Kiwoom/Standard)
                    if channel.startswith("ticker.") or channel.startswith("tick:"):
                        # Extract market
                        if channel.startswith("tick:"):
                            # tick:KR:005930 -> KR
                            try:
                                market = channel.split(':')[1].upper()
                            except:
                                market = "KR"
                        else:
                            # ticker.kr -> KR
                            market = channel.split('.')[-1].upper()
                        
                        # Ticks
                        ts = datetime.fromisoformat(data['timestamp']) if 'timestamp' in data else datetime.now()
                        source = data.get('source', 'KIS')
                        broker = data.get('broker')
                        broker_time = datetime.fromisoformat(data['broker_time']) if data.get('broker_time') else None
                        received_time = datetime.fromisoformat(data['received_time']) if data.get('received_time') else datetime.now()
                        seq_no = data.get('sequence_number')
                        
                        row = (
                            ts, 
                            data['symbol'], 
                            float(data['price']), 
                            float(data.get('volume', 0)), 
                            float(data.get('change', 0)),
                            broker,
                            broker_time,
                            received_time,
                            seq_no,
                            source
                        )
                        self.batch.append(row)
                        
                        if len(self.batch) >= BATCH_SIZE:
                            await self.flush()
                    
                    elif channel.startswith("orderbook."):
                        await self.save_orderbook(data)
                        
                    elif channel == "system.metrics":
                        await self.save_system_metrics(data)
                        
                except Exception as e:
                    logger.error(f"Parse/Queue Error (pattern): {e}")
            
            elif msg_type == "message":  # Direct message
                try:
                    channel = message["channel"]
                    data = json.loads(message["data"])
                    
                    if channel == "market_orderbook":
                        await self.save_orderbook(data)
                    elif channel == "system.metrics": # Direct message fallback
                        await self.save_system_metrics(data)
                        
                except Exception as e:
                    logger.error(f"Parse/Queue Error (direct): {e}")

    async def save_system_metrics(self, data):
        """시스템 메트릭 저장 (Generic)"""
        async with self.db_pool.acquire() as conn:
            try:
                ts = datetime.fromisoformat(data['timestamp'])
                
                # Check if data is legacy dict format (cpu, mem, disk) or new generic format (type, value, meta)
                if 'cpu' in data and 'mem' in data:
                     # Handle Legacy (Host Metrics) -> Convert to rows
                     rows = [
                         (ts, 'cpu', float(data['cpu']), None),
                         (ts, 'memory', float(data['mem']), None)
                     ]
                     if 'disk' in data:
                         rows.append((ts, 'disk', float(data['disk']), None))
                     
                     await conn.executemany("INSERT INTO system_metrics (time, type, value, meta) VALUES ($1, $2, $3, $4)", rows)
                
                else:
                    # New Generic Format
                    m_type = data.get('type')
                    val = float(data.get('value'))
                    meta = json.dumps(data.get('meta')) if data.get('meta') else None
                    
                    await conn.execute("INSERT INTO system_metrics (time, type, value, meta) VALUES ($1, $2, $3, $4)", ts, m_type, val, meta)

            except Exception as e:
                logger.error(f"System Metric Save Error: {e}")

    async def save_orderbook(self, data):
        """호가 스냅샷 데이터를 DB에 저장 (10 Depth Support)"""
        async with self.db_pool.acquire() as conn:
            try:
                ts = datetime.fromisoformat(data['timestamp'])
                source = data.get('source', 'KIS')
                
                # Base row: [time, symbol, source]
                row = [ts, data['symbol'], source]
                
                # Add Asks 1~10
                asks = data.get('asks', [])
                for i in range(10):
                    if i < len(asks):
                        row.extend([asks[i]['price'], asks[i]['vol']])
                    else:
                        row.extend([None, None]) # Fill with NULL if depth < 10

                # Add Bids 1~10
                bids = data.get('bids', [])
                for i in range(10):
                    if i < len(bids):
                        row.extend([bids[i]['price'], bids[i]['vol']])
                    else:
                        row.extend([None, None])

                # Total params: 3 + 20 + 20 = 43 params
                # Generate placeholders $1..$43
                placeholders = ",".join([f"${i+1}" for i in range(len(row))])
                
                query = f"""
                    INSERT INTO market_orderbook (
                        time, symbol, source,
                        ask_price1, ask_vol1, ask_price2, ask_vol2, ask_price3, ask_vol3, ask_price4, ask_vol4, ask_price5, ask_vol5,
                        ask_price6, ask_vol6, ask_price7, ask_vol7, ask_price8, ask_vol8, ask_price9, ask_vol9, ask_price10, ask_vol10,
                        bid_price1, bid_vol1, bid_price2, bid_vol2, bid_price3, bid_vol3, bid_price4, bid_vol4, bid_price5, bid_vol5,
                        bid_price6, bid_vol6, bid_price7, bid_vol7, bid_price8, bid_vol8, bid_price9, bid_vol9, bid_price10, bid_vol10
                    ) VALUES ({placeholders})
                """
                
                await conn.execute(query, *row)
            except Exception as e:
                logger.error(f"Orderbook Save Error: {e}")

    async def periodic_flush(self):
        """지정된 기간(FLUSH_INTERVAL)마다 주기적으로 배치 데이터 적재"""
        while self.running:
            await asyncio.sleep(FLUSH_INTERVAL)
            if self.batch:
                await self.flush()

    async def flush(self):
        """메모리 버퍼에 쌓인 틱 데이터를 DB에 벌크 인서트"""
        if not self.batch:
            return

        async with self.db_pool.acquire() as conn:
            try:
                # asyncpg copy_records_to_table is fast
                await conn.copy_records_to_table(
                    'market_ticks',
                    records=self.batch,
                    columns=['time', 'symbol', 'price', 'volume', 'change', 'broker', 'broker_time', 'received_time', 'sequence_number', 'source']
                )
                logger.info(f"Flushed {len(self.batch)} ticks to TimescaleDB")

                # ISSUE-035: Record successful DB ingestion
                await self._record_db_success(len(self.batch))

                self.batch = []
            except Exception as e:
                logger.error(f"DB Flush Error: {e}")
                # In production, might want retry logic or DLQ

if __name__ == "__main__":
    archiver = TimescaleArchiver()
    asyncio.run(archiver.start())
