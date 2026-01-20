import asyncio
import asyncpg
import os
import logging
import yaml
from datetime import datetime
from src.verification.collector_kis import KISMinuteCollector
from src.verification.collector_kiwoom import KiwoomMinuteCollector

logger = logging.getLogger("VerificationCollector")
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class VerificationDataCollector:
    def __init__(self, config_path: str = "configs/kr_symbols.yaml"):
        self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/stockval")
        self.config_path = config_path
        self.symbols = self._load_symbols()
        self.kis_collector = KISMinuteCollector()
        self.kiwoom_collector = KiwoomMinuteCollector()

    def _load_symbols(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        symbols = set()
        s_config = config.get("symbols", {})
        for group in ["indices", "leverage"]:
            for item in s_config.get(group, []):
                symbols.add(item["symbol"])
        sectors = s_config.get("sectors", {})
        for sector in sectors.values():
            if "etf" in sector: symbols.add(sector["etf"]["symbol"])
            for item in sector.get("top3", []): symbols.add(item["symbol"])
        for item in s_config.get("etf_special", {}).get("top3", []):
            symbols.add(item["symbol"])
        return sorted(list(symbols))

    async def collect_all(self, date_str: str):
        target_date_nodash = date_str.replace("-", "")
        
        # 1. Clear existing verification data for this date
        logger.info(f"🧹 Clearing existing verification data for {date_str}...")
        conn = await asyncpg.connect(self.db_url)
        try:
            # Delete by casting timestamp to date
            await conn.execute(
                "DELETE FROM market_verification_raw WHERE CAST(time AS DATE) = $1", 
                datetime.strptime(date_str, "%Y-%m-%d").date()
            )
        finally:
            await conn.close()

        logger.info(f"🚀 Starting Collection for {len(self.symbols)} symbols...")
        
        for idx, symbol in enumerate(self.symbols, 1):
            logger.info(f"[{idx}/{len(self.symbols)}] Processing {symbol}...")
            
            # KIS
            try:
                await self.kis_collector.fetch_and_store(symbol, target_date_nodash)
            except Exception as e:
                logger.error(f"[{symbol}] KIS failed: {e}")
            
            # Kiwoom
            try:
                await self.kiwoom_collector.fetch_and_store(symbol, target_date_nodash)
            except Exception as e:
                logger.error(f"[{symbol}] Kiwoom failed: {e}")
            
            # Simple rate limiting
            await asyncio.sleep(0.5)

        logger.info("✅ Collection Complete.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-01-20")
    args = parser.parse_args()
    
    collector = VerificationDataCollector()
    asyncio.run(collector.collect_all(args.date))
