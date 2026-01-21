import asyncio
import asyncpg
import os
import logging
import yaml
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger("LossAnalyzerBatch")
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class LossAnalyzerBatch:
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
            for item in s_config.get(group, []):
                symbols.add(item["symbol"])
        sectors = s_config.get("sectors", {})
        for sector in sectors.values():
            if "etf" in sector: symbols.add(sector["etf"]["symbol"])
            for item in sector.get("top3", []): symbols.add(item["symbol"])
        for item in s_config.get("etf_special", {}).get("top3", []):
            symbols.add(item["symbol"])
        return sorted(list(symbols))

    async def analyze_all(self, date_str: str):
        conn = await asyncpg.connect(self.db_url)
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            report_path = f"data/reports/minute_loss_analysis_{date_str.replace('-', '')}.md"
            os.makedirs("data/reports", exist_ok=True)

            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"# Minute-Level Data Loss Analysis Report - {date_str}\n\n")
                f.write("이 보고서는 REST API 분봉 거래량 대비 복구된 틱 데이터의 합산 거래량 차이를 분석합니다.\n\n")
                
                f.write("## 1. Summary by Symbol\n\n")
                f.write("| Symbol | Total Minutes | Full Match | Partial Loss | Total Missing | Coverage % |\n")
                f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")

                for symbol in self.symbols:
                    stats = await self._analyze_symbol_loss(conn, symbol, target_date)
                    covered_pct = (stats['matches'] / stats['total'] * 100) if stats['total'] > 0 else 0
                    f.write(f"| {symbol} | {stats['total']} | {stats['matches']} | {stats['partial']} | {stats['missing']} | {covered_pct:.1f}% |\n")

                f.write("\n## 2. Detailed Loss List (Top 50 Mismatched Minutes)\n\n")
                f.write("| Symbol | Minute | API Volume | Recovery Volume | Loss Amount | Loss % |\n")
                f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")

                # Get top 50 worst minutes across all symbols
                worst_query = """
                    WITH aggregated AS (
                        SELECT 
                            time_bucket('1 minute', time) as minute,
                            symbol,
                            sum(volume) as rec_vol
                        FROM market_ticks_recovery
                        WHERE CAST(time AS DATE) = $1
                        GROUP BY minute, symbol
                    )
                    SELECT 
                        v.symbol,
                        v.time as minute,
                        v.volume as api_vol,
                        COALESCE(a.rec_vol, 0) as rec_vol,
                        (v.volume - COALESCE(a.rec_vol, 0)) as loss_amt
                    FROM market_minutes v
                    LEFT JOIN aggregated a ON v.time = a.minute AND v.symbol = a.symbol
                    WHERE CAST(v.time AS DATE) = $1
                      AND v.volume > COALESCE(a.rec_vol, 0)
                    ORDER BY loss_amt DESC
                    LIMIT 50
                """
                worst_rows = await conn.fetch(worst_query, target_date)
                for wr in worst_rows:
                    loss_pct = (wr['loss_amt'] / wr['api_vol'] * 100) if wr['api_vol'] > 0 else 0
                    f.write(f"| {wr['symbol']} | {wr['minute']} | {wr['api_vol']:.0f} | {wr['rec_vol']:.0f} | {wr['loss_amt']:.0f} | {loss_pct:.1f}% |\n")

            logger.info(f"📊 Detailed loss analysis generated: {report_path}")

        finally:
            await conn.close()

    async def _analyze_symbol_loss(self, conn, symbol: str, target_date: datetime.date) -> Dict:
        query = """
            WITH aggregated AS (
                SELECT 
                    time_bucket('1 minute', time) as minute,
                    sum(volume) as rec_vol
                FROM market_ticks_recovery
                WHERE symbol = $1 AND CAST(time AS DATE) = $2
                GROUP BY minute
            )
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE v.volume = COALESCE(a.rec_vol, 0)) as matches,
                COUNT(*) FILTER (WHERE v.volume > COALESCE(a.rec_vol, 0) AND COALESCE(a.rec_vol, 0) > 0) as partial,
                COUNT(*) FILTER (WHERE COALESCE(a.rec_vol, 0) = 0) as missing
            FROM market_minutes v
            LEFT JOIN aggregated a ON v.time = a.minute
            WHERE v.symbol = $1 AND CAST(v.time AS DATE) = $2
        """
        row = await conn.fetchrow(query, symbol, target_date)
        return dict(row) if row else {'total': 0, 'matches': 0, 'partial': 0, 'missing': 0}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-01-20")
    args = parser.parse_args()
    
    analyzer = LossAnalyzerBatch()
    asyncio.run(analyzer.analyze_all(args.date))
