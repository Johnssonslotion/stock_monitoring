import asyncio
import logging
import yaml
import os
from pathlib import Path
from datetime import datetime
from src.verification.collector_kis import KISMinuteCollector
from src.verification.collector_kiwoom import KiwoomMinuteCollector
from src.verification.cross_checker import CrossChecker

logger = logging.getLogger("BatchAssessment")
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class BatchAssessmentManager:
    def __init__(self, config_path: str = "configs/kr_symbols.yaml"):
        self.config_path = config_path
        self.symbols = self._load_symbols()
        self.kis_collector = KISMinuteCollector()
        self.kiwoom_collector = KiwoomMinuteCollector()
        self.checker = CrossChecker()

    def _load_symbols(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        symbols = set()
        s_config = config.get("symbols", {})
        
        # Indices & Leverage
        for group in ["indices", "leverage"]:
            for item in s_config.get(group, []):
                symbols.add(item["symbol"])
        
        # Sectors
        sectors = s_config.get("sectors", {})
        for sector in sectors.values():
            if "etf" in sector:
                symbols.add(sector["etf"]["symbol"])
            for item in sector.get("top3", []):
                symbols.add(item["symbol"])
        
        # Special ETFs
        for item in s_config.get("etf_special", {}).get("top3", []):
            symbols.add(item["symbol"])
            
        return sorted(list(symbols))

    async def run_full_assessment(self, date_str: str):
        """
        date_str: YYYY-MM-DD (for checker)
        target_date: YYYYMMDD (for collectors)
        """
        target_date = date_str.replace("-", "")
        logger.info(f"🚀 Starting Full-scale Assessment for {date_str} ({len(self.symbols)} symbols)")
        
        for idx, symbol in enumerate(self.symbols, 1):
            logger.info(f"[{idx}/{len(self.symbols)}] Processing {symbol}...")
            
            # 1. Collect from KIS
            try:
                await self.kis_collector.fetch_and_store(symbol, target_date)
            except Exception as e:
                logger.error(f"[{symbol}] KIS Collection failed: {e}")
            
            # 2. Collect from Kiwoom
            try:
                await self.kiwoom_collector.fetch_and_store(symbol, target_date)
            except Exception as e:
                logger.error(f"[{symbol}] Kiwoom Collection failed: {e}")
                
            # 3. Cross-Check
            try:
                await self.checker.run_check(symbol, date_str)
            except Exception as e:
                logger.error(f"[{symbol}] Cross-Check failed: {e}")
            
            # Rate limit spread
            await asyncio.sleep(1)

        logger.info(f"✅ Full-scale Assessment complete for {date_str}")
        await self._generate_summary_report(date_str)

    async def _generate_summary_report(self, date_str: str):
        import asyncpg
        tsdb_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/stockval")
        conn = await asyncpg.connect(tsdb_url)
        
        try:
            # Aggregate status counts across all symbols
            target_date = date_str.replace("-", "")
            query = """
                SELECT 
                    status, 
                    count(*) as count
                FROM market_verification_results
                WHERE CAST(time AS DATE) = $1
                GROUP BY status
                ORDER BY count DESC
            """
            rows = await conn.fetch(query, datetime.strptime(date_str, "%Y-%m-%d").date())
            
            report_path = f"data/reports/full_assessment_{target_date}.md"
            os.makedirs("data/reports", exist_ok=True)
            
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"# Batch Data Quality Assessment Report - {date_str}\n\n")
                f.write("## Overall Statistics\n\n")
                f.write("| Status | Count | Percentage |\n")
                f.write("| :--- | :--- | :--- |\n")
                
                total = sum(r['count'] for r in rows)
                for r in rows:
                    pct = (r['count'] / total * 100) if total > 0 else 0
                    f.write(f"| {r['status']} | {r['count']} | {pct:.1f}% |\n")
                
                f.write("\n## Symbol Heatmap (Top Mismatches)\n\n")
                f.write("| Symbol | Mismatch Count | Missing Local |\n")
                f.write("| :--- | :--- | :--- |\n")
                
                # Top problematic symbols
                detail_query = """
                    WITH stats AS (
                        SELECT 
                            symbol,
                            count(*) FILTER (WHERE status = 'MISMATCH') as mismatches,
                            count(*) FILTER (WHERE status = 'MISSING_LOCAL') as missing
                        FROM market_verification_results
                        WHERE CAST(time AS DATE) = $1
                        GROUP BY symbol
                    )
                    SELECT * FROM stats
                    WHERE (mismatches + missing) > 0
                    ORDER BY (mismatches + missing) DESC
                    LIMIT 20
                """
                detail_rows = await conn.fetch(detail_query, datetime.strptime(date_str, "%Y-%m-%d").date())
                for dr in detail_rows:
                    f.write(f"| {dr['symbol']} | {dr['mismatches']} | {dr['missing']} |\n")
            
            logger.info(f"📊 Summary report generated: {report_path}")
            
        finally:
            await conn.close()

if __name__ == "__main__":
    import argparse
    from datetime import datetime
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-01-20")
    args = parser.parse_args()
    
    manager = BatchAssessmentManager()
    asyncio.run(manager.run_full_assessment(args.date))
