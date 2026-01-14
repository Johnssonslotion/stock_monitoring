"""데이터 로더 (DataLoader)

TimescaleDB에서 백테스팅에 필요한 과거 데이터를 로드합니다.
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, AsyncGenerator
import asyncpg

logger = logging.getLogger(__name__)

class DataLoader:
    """백테스팅 데이터 로더
    
    TimescaleDB에 구축된 틱 데이터를 쿼리하여 전략에 공급합니다.
    """
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        self.pool = None

    async def connect(self):
        """DB 연결 풀 생성"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                user=self.db_config.get('user', 'postgres'),
                password=self.db_config.get('password', 'password'),
                database=self.db_config.get('database', 'backtest_db'),
                host=self.db_config.get('host', 'localhost'),
                port=self.db_config.get('port', 5433)
            )
            logger.info("Connected to TimescaleDB for data loading")

    async def close(self):
        """DB 연결 종료"""
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def init_db(self):
        """백테스팅 DB 스키마 초기화 (Hypertable 포함)"""
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as conn:
            # market_ticks 테이블 생성
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS market_ticks (
                    time TIMESTAMPTZ NOT NULL,
                    symbol TEXT NOT NULL,
                    price DOUBLE PRECISION NOT NULL,
                    volume DOUBLE PRECISION NOT NULL,
                    change DOUBLE PRECISION
                );
            """)
            
            # Hypertable 변환
            try:
                await conn.execute("SELECT create_hypertable('market_ticks', 'time', if_not_exists => TRUE);")
                logger.info("Hypertable 'market_ticks' ensured in backtest_db.")
            except Exception as e:
                logger.warning(f"Hypertable creation msg: {e}")

    async def fetch_ticks(
        self, 
        symbols: List[str], 
        start_date: datetime, 
        end_date: datetime,
        batch_size: int = 10000
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """과거 틱 데이터를 스트리밍 방식으로 가져옵니다."""
        if not self.pool:
            await self.connect()

        # 실제 스키마(market_ticks, time)에 맞게 쿼리 수정
        query = """
            SELECT time as timestamp, symbol, price, volume
            FROM market_ticks
            WHERE symbol = ANY($1) 
              AND time >= $2 
              AND time <= $3
            ORDER BY time ASC
        """
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                async for record in conn.cursor(query, symbols, start_date, end_date):
                    yield {
                        'timestamp': record['timestamp'],
                        'symbol': record['symbol'],
                        'price': float(record['price']),
                        'volume': int(record['volume']),
                        'market': 'UNKNOWN'  # market 정보는 테이블에 없음
                    }

    async def get_total_tick_count(self, symbols: List[str], start_date: datetime, end_date: datetime) -> int:
        """조건에 해당하는 전체 틱 수 조회"""
        if not self.pool:
            await self.connect()
            
        query = """
            SELECT COUNT(*) 
            FROM market_ticks
            WHERE symbol = ANY($1) 
              AND time >= $2 
              AND time <= $3
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, symbols, start_date, end_date)
