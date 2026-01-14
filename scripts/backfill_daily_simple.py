#!/usr/bin/env python3
"""
무료 소스(FinanceDataReader)로 일봉 백필

확실한 2년치 일봉 데이터 확보
"""
import asyncio
import asyncpg
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging
from dotenv import load_dotenv
import yaml

# .env.dev 로드
env_path = Path(__file__).parent.parent / '.env.dev'
load_dotenv(env_path)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class DailyBackfiller:
    def __init__(self):
        self.db_url = 'postgresql://postgres:password@localhost:5432/stockval'
        self.symbols = self._load_symbols()
    
    def _load_symbols(self):
        """configs/kr_symbols.yaml에서 종목 로드"""
        config_path = Path(__file__).parent.parent / 'configs' / 'kr_symbols.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        symbols = []
        for item in config['symbols'].get('indices', []):
            symbols.append(item['symbol'])
        for item in config['symbols'].get('leverage', []):
            symbols.append(item['symbol'])
        
        sectors = config['symbols'].get('sectors', {})
        for sector_name, sector_data in sectors.items():
            for item in sector_data.get('top3', []):
                symbols.append(item['symbol'])
        
        return symbols
    
    async def backfill_daily(self, conn):
        """일봉 2년치 백필"""
        import FinanceDataReader as fdr
        
        start_date = '2024-01-01'
        total_saved = 0
        
        for idx, symbol in enumerate(self.symbols, 1):
            logger.info(f"[{idx}/{len(self.symbols)}] Fetching {symbol}...")
            
            try:
                # FinanceDataReader로 데이터 가져오기
                df = fdr.DataReader(symbol, start=start_date)
                
                if df.empty:
                    logger.warning(f"{symbol}: No data")
                    continue
                
                # DB 저장
                saved = 0
                for date, row in df.iterrows():
                    try:
                        await conn.execute("""
                            INSERT INTO market_candles (time, symbol, open, high, low, close, volume, interval)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, '1d')
                            ON CONFLICT (time, symbol, interval) DO UPDATE SET
                                open = EXCLUDED.open,
                                high = EXCLUDED.high,
                                low = EXCLUDED.low,
                                close = EXCLUDED.close,
                                volume = EXCLUDED.volume
                        """,
                            date.to_pydatetime(),
                            symbol,
                            float(row['Open']),
                            float(row['High']),
                            float(row['Low']),
                            float(row['Close']),
                            float(row['Volume'])
                        )
                        saved += 1
                    except Exception as e:
                        logger.debug(f"Skip {symbol} {date}: {e}")
                        continue
                
                total_saved += saved
                logger.info(f"✅ {symbol}: {saved} candles saved")
                
            except Exception as e:
                logger.error(f"❌ {symbol}: {e}")
                continue
        
        logger.info(f"🎉 Daily backfill complete: {total_saved} total candles")
        return total_saved
    
    async def run(self):
        """실행"""
        logger.info(f"Starting daily backfill for {len(self.symbols)} symbols")
        
        conn = await asyncpg.connect(self.db_url)
        
        try:
            await self.backfill_daily(conn)
        finally:
            await conn.close()


async def main():
    backfiller = DailyBackfiller()
    await backfiller.run()


if __name__ == "__main__":
    asyncio.run(main())
