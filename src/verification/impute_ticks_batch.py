import asyncio
import asyncpg
import os
import logging
import yaml
from datetime import datetime, timedelta

logger = logging.getLogger("TickImputation")
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class TickImputer:
    def __init__(self, config_path: str = "configs/kr_symbols.yaml"):
        self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/stockval")
        self.config_path = config_path
        self.symbols = self._load_symbols()

    def _load_symbols(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        symbols = set()
        s_config = config.get("symbols", {})
        for group in ["indices", "leverage"]:
            for item in s_config.get(group, []): symbols.add(item["symbol"])
        sectors = s_config.get("sectors", {})
        for sector in sectors.values():
            if "etf" in sector: symbols.add(sector["etf"]["symbol"])
            for item in sector.get("top3", []): symbols.add(item["symbol"])
        for item in s_config.get("etf_special", {}).get("top3", []):
            symbols.add(item["symbol"])
        return sorted(list(symbols))

    async def impute_all(self, date_str: str):
        conn = await asyncpg.connect(self.db_url)
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # 1. Clear existing for date
            logger.info(f"🧹 Clearing imputed ticks for {date_str}...")
            await conn.execute("DELETE FROM market_ticks_imputed WHERE CAST(time AS DATE) = $1", target_date)
            
            # 2. Copy BASE data (Originals)
            logger.info("📦 Copying original recovered ticks to imputed table...")
            query_base = """
                INSERT INTO market_ticks_imputed (time, symbol, price, volume, source, execution_no, imputed_from)
                SELECT time, symbol, price, volume, source, execution_no, NULL
                FROM market_ticks_recovery
                WHERE CAST(time AS DATE) = $1
                ON CONFLICT DO NOTHING
            """
            await conn.execute(query_base, target_date)
            
            # 3. Cross-Fill Gaps
            logger.info("🔄 Starting Cross-Source Imputation...")
            
            for idx, symbol in enumerate(self.symbols, 1):
                await self._impute_symbol(conn, symbol, target_date)
                
                if idx % 10 == 0:
                    logger.info(f"Progress: {idx}/{len(self.symbols)} symbols processed.")

            logger.info("✅ Imputation Complete.")

        finally:
            await conn.close()

    async def _impute_symbol(self, conn, symbol: str, target_date: datetime.date):
        # Identify minutes where KIS is missing but Kiwoom exists
        query_kis_missing = """
            WITH stats AS (
                SELECT 
                    time_bucket('1 minute', time) as minute,
                    count(*) FILTER (WHERE source = 'KIS') as kis_count,
                    count(*) FILTER (WHERE source = 'KIWOOM') as kiwoom_count
                FROM market_ticks_recovery
                WHERE symbol = $1 AND CAST(time AS DATE) = $2
                GROUP BY minute
            )
            SELECT minute FROM stats
            WHERE kis_count = 0 AND kiwoom_count > 0
        """
        rows_kis_missing = await conn.fetch(query_kis_missing, symbol, target_date)
        
        if rows_kis_missing:
            # Generate KIS ticks from Kiwoom
            minutes = [r['minute'] for r in rows_kis_missing]
            # Ensure list of timestamps is passed correctly as naive/UTC
            # asyncpg prefers datetime objects, but we need to ensure consistency
            minutes_ts = [m.replace(tzinfo=None) if m.tzinfo else m for m in minutes]
            
            insert_query = """
                INSERT INTO market_ticks_imputed (time, symbol, price, volume, source, execution_no, imputed_from)
                SELECT 
                    time, symbol, price, volume, 'KIS', execution_no, 'KIWOOM'
                FROM market_ticks_recovery
                WHERE symbol = $1 
                  AND source = 'KIWOOM'
                  AND time_bucket('1 minute', time) = ANY($2::timestamp[])
                ON CONFLICT DO NOTHING
            """
            result = await conn.execute(insert_query, symbol, minutes_ts)
            # logger.info(f"[{symbol}] Filled KIS gaps: {result}")

        # Reverse: Identify minutes where Kiwoom is missing but KIS exists
        query_kw_missing = """
            WITH stats AS (
                SELECT 
                    time_bucket('1 minute', time) as minute,
                    count(*) FILTER (WHERE source = 'KIS') as kis_count,
                    count(*) FILTER (WHERE source = 'KIWOOM') as kiwoom_count
                FROM market_ticks_recovery
                WHERE symbol = $1 AND CAST(time AS DATE) = $2
                GROUP BY minute
            )
            SELECT minute FROM stats
            WHERE kiwoom_count = 0 AND kis_count > 0
        """
        rows_kw_missing = await conn.fetch(query_kw_missing, symbol, target_date)
        
        if rows_kw_missing:
            minutes = [r['minute'] for r in rows_kw_missing]
            minutes_ts = [m.replace(tzinfo=None) if m.tzinfo else m for m in minutes]
            
            insert_query_kw = """
                INSERT INTO market_ticks_imputed (time, symbol, price, volume, source, execution_no, imputed_from)
                SELECT 
                    time, symbol, price, volume, 'KIWOOM', execution_no, 'KIS'
                FROM market_ticks_recovery
                WHERE symbol = $1 
                  AND source = 'KIS'
                  AND time_bucket('1 minute', time) = ANY($2::timestamp[])
                ON CONFLICT DO NOTHING
            """
            result = await conn.execute(insert_query_kw, symbol, minutes_ts)
            # logger.info(f"[{symbol}] Filled Kiwoom gaps: {result}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-01-20")
    args = parser.parse_args()
    
    imputer = TickImputer()
    asyncio.run(imputer.impute_all(args.date))
