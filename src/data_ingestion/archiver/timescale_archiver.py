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

    async def init_db(self):
        """틱 데이터용 하이퍼테이블(Hypertable) 초기화"""
        conn = await asyncpg.connect(
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        try:
            # Create Table (Normal)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS market_ticks (
                    time TIMESTAMPTZ NOT NULL,
                    symbol TEXT NOT NULL,
                    price DOUBLE PRECISION NOT NULL,
                    volume DOUBLE PRECISION NOT NULL,
                    change DOUBLE PRECISION
                );
            """)
            
            # Convert to Hypertable (TimescaleDB unique function)
            # If already hypertable, this might warn/error in some versions, but 'IF NOT EXISTS' logic is usually handled by create_hypertable's if_not_exists arg in newer versions or catching error
            try:
                await conn.execute("SELECT create_hypertable('market_ticks', 'time', if_not_exists => TRUE);")
                logger.info("Hypertable 'market_ticks' ensured.")
            except Exception as e:
                logger.warning(f"Hypertable creation msg: {e}")
                
            # Create system_metrics table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    time TIMESTAMPTZ NOT NULL,
                    type TEXT NOT NULL,
                    value DOUBLE PRECISION NOT NULL,
                    meta JSONB
                );
            """)
            try:
                await conn.execute("SELECT create_hypertable('system_metrics', 'time', if_not_exists => TRUE);")
                logger.info("Hypertable 'system_metrics' ensured.")
            except Exception as e:
                logger.warning(f"Hypertable creation msg (system_metrics): {e}")

            # Create market_ticks_validation table (ISSUE-029)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS market_ticks_validation (
                    bucket_time TIMESTAMPTZ NOT NULL,
                    symbol TEXT NOT NULL,
                    tick_count_collected INTEGER,
                    volume_sum DOUBLE PRECISION,
                    price_open DOUBLE PRECISION,
                    price_high DOUBLE PRECISION,
                    price_low DOUBLE PRECISION,
                    price_close DOUBLE PRECISION,
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    validation_status TEXT,
                    UNIQUE (bucket_time, symbol)
                );
            """)
            try:
                await conn.execute("SELECT create_hypertable('market_ticks_validation', 'bucket_time', if_not_exists => TRUE);")
                logger.info("Hypertable 'market_ticks_validation' ensured.")
            except Exception as e:
                logger.warning(f"Hypertable creation msg (validation): {e}")
            try:
                await conn.execute("SELECT create_hypertable('system_metrics', 'time', if_not_exists => TRUE);")
                logger.info("Hypertable 'system_metrics' ensured.")
            except Exception as e:
                logger.warning(f"Hypertable creation msg (system_metrics): {e}")

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
                        row = (ts, data['symbol'], source, float(data['price']), float(data.get('volume', 0)), float(data.get('change', 0)))
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
                    columns=['time', 'symbol', 'source', 'price', 'volume', 'change']
                )
                logger.info(f"Flushed {len(self.batch)} ticks to TimescaleDB")
                self.batch = []
            except Exception as e:
                logger.error(f"DB Flush Error: {e}")
                # In production, might want retry logic or DLQ

if __name__ == "__main__":
    archiver = TimescaleArchiver()
    asyncio.run(archiver.start())
