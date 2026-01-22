import asyncio
import asyncpg
import os
import logging
import yaml
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger("OutlierDetector")
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class OutlierDetector:
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

    async def detect_all(self, date_str: str):
        conn = await asyncpg.connect(self.db_url)
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            report_path = f"data/reports/outlier_report_{date_str.replace('-', '')}.md"
            os.makedirs("data/reports", exist_ok=True)

            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"# Outlier Detection Report - {date_str}\n\n")
                f.write("이 보고서는 REST API 분봉 데이터와 복구된 Log 데이터 간의 정합성을 검증하여 보간 전략 수립을 지원합니다.\n\n")
                
                f.write("## 1. Outlier Summary by Type\n\n")
                f.write("| Symbol | Total Minutes | MATCH | PRICE_DIFF | PARTIAL_LOSS | EXCESS_LOG | MISSING_LOG | Coverage % |\n")
                f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")

                for symbol in self.symbols:
                    stats = await self._analyze_symbol_outliers(conn, symbol, target_date)
                    covered_pct = (stats['MATCH'] / stats['Total'] * 100) if stats['Total'] > 0 else 0
                    f.write(f"| {symbol} | {stats['Total']} | {stats['MATCH']} | {stats['PRICE_DIFF']} | {stats['PARTIAL_LOSS']} | {stats['EXCESS_LOG']} | {stats['MISSING_LOG']} | {covered_pct:.1f}% |\n")

                f.write("\n## 2. Detailed Outlier Cases (Top 100 by Severity)\n\n")
                f.write("| Symbol | Minute | Type | API Vol | Log Vol | API Close | Log Close | Gap Info |\n")
                f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")

                outliers = await self._fetch_top_outliers(conn, target_date, limit=100)
                for o in outliers:
                    f.write(f"| {o['symbol']} | {o['minute']} | {o['type']} | {o['api_vol']:.0f} | {o['log_vol']:.0f} | {o['api_close']:.0f} | {o['log_close']:.0f} | {o['gap_info']} |\n")

            logger.info(f"📊 Outlier report generated: {report_path}")

        finally:
            await conn.close()

    async def _analyze_symbol_outliers(self, conn, symbol: str, target_date: datetime.date) -> Dict:
        query = """
            WITH logs AS (
                SELECT 
                    time_bucket('1 minute', time) as minute,
                    (array_agg(price ORDER BY time DESC))[1] as close,
                    sum(volume) as volume
                FROM market_ticks_recovery
                WHERE symbol = $1 AND CAST(time AS DATE) = $2
                GROUP BY minute
            )
            SELECT 
                v.time as minute,
                v.volume as api_vol,
                COALESCE(l.volume, 0) as log_vol,
                v.close as api_close,
                COALESCE(l.close, 0) as log_close
            FROM market_minutes v
            LEFT JOIN logs l ON v.time = l.minute
            WHERE v.symbol = $1 AND CAST(v.time AS DATE) = $2
        """
        rows = await conn.fetch(query, symbol, target_date)
        
        stats = {'Total': len(rows), 'MATCH': 0, 'PRICE_DIFF': 0, 'PARTIAL_LOSS': 0, 'EXCESS_LOG': 0, 'MISSING_LOG': 0}
        
        for r in rows:
            api_v = r['api_vol'] or 0
            log_v = r['log_vol'] or 0
            api_c = r['api_close'] or 0
            log_c = r['log_close'] or 0
            
            if log_v == 0:
                stats['MISSING_LOG'] += 1
            elif log_v > api_v * 1.05: # Allow small margin
                stats['EXCESS_LOG'] += 1
            elif log_v < api_v * 0.95: # Allow small margin
                stats['PARTIAL_LOSS'] += 1
            elif abs(api_c - log_c) > 0: # Strict price match (or use tick size)
                stats['PRICE_DIFF'] += 1
            else:
                stats['MATCH'] += 1
                
        return stats

    async def _fetch_top_outliers(self, conn, target_date: datetime.date, limit: int = 100) -> List[Dict]:
        # This is a bit complex in pure SQL across all symbols, so implementing a python-side aggregator or complex query
        # Let's use a simplified approach: Query discrepancies directly
        query = """
            WITH logs AS (
                SELECT 
                    time_bucket('1 minute', time) as minute,
                    symbol,
                    (array_agg(price ORDER BY time DESC))[1] as close,
                    sum(volume) as volume
                FROM market_ticks_recovery
                WHERE CAST(time AS DATE) = $1
                GROUP BY minute, symbol
            )
            SELECT 
                v.symbol,
                v.time,
                v.volume as api_vol,
                COALESCE(l.volume, 0) as log_vol,
                v.close as api_close,
                COALESCE(l.close, 0) as log_close
            FROM market_minutes v
            LEFT JOIN logs l ON v.time = l.minute AND v.symbol = l.symbol
            WHERE CAST(v.time AS DATE) = $1
        """
        rows = await conn.fetch(query, target_date)
        
        outliers = []
        for r in rows:
            api_v = r['api_vol'] or 0
            log_v = r['log_vol'] or 0
            api_c = r['api_close'] or 0
            log_c = r['log_close'] or 0
            
            o_type = None
            gap_info = ""
            
            if log_v == 0:
                o_type = "MISSING_LOG"
                gap_info = f"Vol -{api_v:.0f}"
            elif log_v > api_v * 1.05:
                o_type = "EXCESS_LOG"
                gap_info = f"Vol +{log_v - api_v:.0f}"
            elif log_v < api_v * 0.95:
                o_type = "PARTIAL_LOSS"
                gap_info = f"Vol -{api_v - log_v:.0f}"
            elif abs(api_c - log_c) > 0:
                o_type = "PRICE_DIFF"
                gap_info = f"Price {log_c - api_c:.0f}"
            
            if o_type:
                outliers.append({
                    'symbol': r['symbol'],
                    'minute': r['time'],
                    'type': o_type,
                    'api_vol': api_v,
                    'log_vol': log_v,
                    'api_close': api_c,
                    'log_close': log_c,
                    'gap_info': gap_info,
                    'sort_key': abs(api_v - log_v) if 'Vol' in gap_info else abs(api_c - log_c) * 1000 # Weight price diff
                })
        
        # Sort by severity (Volume gap or Price gap)
        outliers.sort(key=lambda x: x['sort_key'], reverse=True)
        return outliers[:limit]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-01-20")
    args = parser.parse_args()
    
    detector = OutlierDetector()
    asyncio.run(detector.detect_all(args.date))
