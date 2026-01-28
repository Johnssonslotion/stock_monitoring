import asyncio
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

from src.data_ingestion.recovery.log_recovery import LogRecoveryManager
# ISSUE-044: Legacy imports (moved to legacy folder)
from src.data_ingestion.recovery.legacy.backfill_manager import BackfillManager
from src.data_ingestion.recovery.legacy.merge_worker import merge_recovery_data

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RecoveryOrchestrator")


class RecoveryOrchestrator:
    """
    [ISSUE-031] Hybrid Recovery Orchestrator
    [RFC-009] Ground Truth & API Control 준수
    
    Coordinates the two-phase recovery process:
    1. Log Recovery: Parse JSONL logs and insert into DuckDB
    2. Gap Analysis & REST Backfill: Detect remaining gaps and backfill via KIS API
    
    Note: REST API 호출은 BackfillManager를 통해 gatekeeper 경유 (RFC-009 준수)
    """
    
    def __init__(self, 
                 main_db_path: str = "data/ticks.duckdb",
                 log_dir: str = "data/raw/kiwoom",
                 symbols: Optional[List[str]] = None):
        self.main_db_path = main_db_path
        self.log_dir = log_dir
        self.symbols = symbols
        
        # Managers
        self.log_manager = LogRecoveryManager(db_path=main_db_path, log_dir=log_dir)
        # RFC-009: BackfillManager now includes Self-Diagnosis and gatekeeper integration
        self.backfill_manager = BackfillManager(target_symbols=symbols)
        
    async def run_hybrid_recovery(self, target_date: str):
        """
        Execute hybrid recovery for a target date (YYYYMMDD).
        
        Args:
            target_date: Date in YYYYMMDD format
        
        Workflow:
            1. Log Recovery (Primary)
            2. Gap Detection
            3. REST API Backfill (Secondary, only for gaps)
            4. Merge temp recovery DB to main DB
        """
        logger.info(f"🚀 Starting Hybrid Recovery for {target_date}")
        
        # === Phase 1: Log Recovery ===
        logger.info("📂 Phase 1: Log-based Recovery")
        try:
            self.log_manager.connect()
            self.log_manager.recover_from_date(target_date)
            self.log_manager.close()
            logger.info("✅ Phase 1 Complete")
        except Exception as e:
            logger.error(f"❌ Log Recovery Failed: {e}")
            # Continue to Phase 2 anyway (API fallback)
        
        # === Phase 2: Gap Analysis ===
        logger.info("🔍 Phase 2: Gap Detection")
        gaps = self.backfill_manager.detect_gaps(
            main_db_path=self.main_db_path,
            target_date=target_date
        )
        
        if not gaps:
            logger.info("✅ No gaps detected. Recovery complete!")
            return
        
        total_missing = sum(g['total_missing'] for g in gaps)
        logger.info(f"⚠️  Found gaps: {len(gaps)} symbols, {total_missing} total missing minutes")
        
        # === Phase 3: REST API Backfill ===
        logger.info("📡 Phase 3: REST API Backfill (for gaps only)")
        try:
            # Currently backfill_manager fetches all ticks for the day
            # To optimize, we'd need to modify it to accept specific time ranges
            # For now, we run backfill and rely on deduplication
            await self.backfill_manager.run_backfill(target_date)
            logger.info("✅ Phase 3 Complete")
        except Exception as e:
            logger.error(f"❌ REST Backfill Failed: {e}")
        
        # === Phase 4: Merge Temp DB ===
        logger.info("🔄 Phase 4: Merging Recovery Data")
        try:
            temp_db_path = self.backfill_manager.db_path
            if os.path.exists(temp_db_path):
                merge_recovery_data(self.main_db_path, temp_db_path)
                logger.info("✅ Phase 4 Complete")
            else:
                logger.warning("No temp DB found to merge")
        except Exception as e:
            logger.error(f"❌ Merge Failed: {e}")
        
        logger.info("🎉 Hybrid Recovery Complete!")
        
    def analyze_recovery_results(self, target_date: str) -> Dict:
        """
        Analyze recovery results by querying final state.
        
        Returns:
            Dict with recovery statistics
        """
        import duckdb
        
        # Convert YYYYMMDD to YYYY-MM-DD
        date_str = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:8]}"
        
        conn = duckdb.connect(self.main_db_path, read_only=True)
        
        stats = {}
        
        # Total ticks recovered
        query = f"""
            SELECT COUNT(*) as total, 
                   COUNT(DISTINCT symbol) as symbols,
                   MIN(timestamp) as first_tick,
                   MAX(timestamp) as last_tick
            FROM market_ticks
            WHERE DATE(timestamp) = '{date_str}'
        """
        result = conn.execute(query).fetchone()
        stats['total_ticks'] = result[0]
        stats['unique_symbols'] = result[1]
        stats['first_tick'] = result[2]
        stats['last_tick'] = result[3]
        
        # Breakdown by source
        query = f"""
            SELECT source, COUNT(*) as count
            FROM market_ticks
            WHERE DATE(timestamp) = '{date_str}'
            GROUP BY source
        """
        sources = conn.execute(query).fetchall()
        stats['by_source'] = {row[0]: row[1] for row in sources}
        
        conn.close()
        
        return stats


async def main():
    """CLI Entry Point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hybrid Data Recovery Orchestrator")
    parser.add_argument("--date", required=True, help="Target date (YYYYMMDD)")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols (optional)")
    
    args = parser.parse_args()
    
    orchestrator = RecoveryOrchestrator(symbols=args.symbols)
    await orchestrator.run_hybrid_recovery(args.date)
    
    # Show results
    stats = orchestrator.analyze_recovery_results(args.date)
    logger.info(f"📊 Recovery Statistics: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
