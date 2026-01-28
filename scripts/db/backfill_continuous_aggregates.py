#!/usr/bin/env python3
"""
Continuous Aggregates Backfill Script

[ISSUE-044] 기존 틱 데이터에서 분봉 추출 및 복구

Usage:
    # 기본 실행 (1월 22일부터 현재까지)
    python scripts/db/backfill_continuous_aggregates.py

    # 특정 기간 지정
    python scripts/db/backfill_continuous_aggregates.py --start 2026-01-15 --end 2026-01-28

    # Dry-run (실제 실행 없이 확인)
    python scripts/db/backfill_continuous_aggregates.py --dry-run
"""

import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from typing import Optional

import asyncpg
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


# Continuous Aggregates (Order of refresh)
CONTINUOUS_AGGREGATES = [
    'market_candles_1m_view',
    'market_candles_5m_view',
    'market_candles_1h_view',
    'market_candles_1d_view',
]


def get_db_url() -> str:
    """Get TimescaleDB connection URL from environment"""
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "password")
    db_name = os.getenv("DB_NAME", "stockval")
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


async def check_views_exist(conn: asyncpg.Connection) -> dict:
    """Check if Continuous Aggregate views exist"""
    results = {}
    for view in CONTINUOUS_AGGREGATES:
        row = await conn.fetchrow("""
            SELECT COUNT(*) as cnt
            FROM timescaledb_information.continuous_aggregates
            WHERE view_name = $1
        """, view)
        results[view] = row['cnt'] > 0
    return results


async def get_tick_data_range(conn: asyncpg.Connection) -> tuple:
    """Get min/max time from market_ticks"""
    row = await conn.fetchrow("""
        SELECT
            MIN(time) as min_time,
            MAX(time) as max_time,
            COUNT(*) as total_ticks
        FROM market_ticks
    """)
    return row['min_time'], row['max_time'], row['total_ticks']


async def get_view_data_count(conn: asyncpg.Connection, view: str) -> int:
    """Get row count from a view"""
    try:
        row = await conn.fetchrow(f"SELECT COUNT(*) as cnt FROM {view}")
        return row['cnt']
    except Exception:
        return 0


async def refresh_continuous_aggregate(
    conn: asyncpg.Connection,
    view: str,
    start: datetime,
    end: datetime,
    dry_run: bool = False
) -> bool:
    """
    Refresh a single Continuous Aggregate for the given time range

    Args:
        conn: Database connection
        view: View name
        start: Start time
        end: End time
        dry_run: If True, don't execute (just log)

    Returns:
        True if successful
    """
    logger.info(f"{'[DRY-RUN] ' if dry_run else ''}Refreshing {view}: {start} → {end}")

    if dry_run:
        return True

    try:
        # TimescaleDB 2.x uses CALL refresh_continuous_aggregate
        await conn.execute(
            "CALL refresh_continuous_aggregate($1, $2, $3)",
            view, start, end
        )

        # Verify refresh
        count = await get_view_data_count(conn, view)
        logger.info(f"✅ {view} refreshed. Current row count: {count:,}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to refresh {view}: {e}")
        return False


async def run_backfill(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    dry_run: bool = False
):
    """
    Run backfill for all Continuous Aggregates

    Args:
        start: Start time (default: 2026-01-22)
        end: End time (default: now)
        dry_run: If True, don't execute
    """
    db_url = get_db_url()
    logger.info(f"Connecting to database...")

    conn = await asyncpg.connect(db_url)

    try:
        # 1. Check if views exist
        logger.info("Checking Continuous Aggregates...")
        view_status = await check_views_exist(conn)

        missing_views = [v for v, exists in view_status.items() if not exists]
        if missing_views:
            logger.error(f"❌ Missing views: {missing_views}")
            logger.error("Run migration 009_create_continuous_aggregates.sql first!")
            return False

        logger.info("✅ All Continuous Aggregates exist")

        # 2. Get tick data range
        min_time, max_time, total_ticks = await get_tick_data_range(conn)
        logger.info(f"📊 Tick data range: {min_time} → {max_time}")
        logger.info(f"📊 Total ticks: {total_ticks:,}")

        if total_ticks == 0:
            logger.warning("⚠️ No tick data found. Nothing to backfill.")
            return True

        # 3. Determine backfill range
        if start is None:
            # Default: 2026-01-22 (분봉 생성 중단 시점)
            start = datetime(2026, 1, 22, 0, 0, 0)

        if end is None:
            end = datetime.now()

        # Ensure start is not before min_time
        if min_time and start < min_time:
            logger.info(f"Adjusting start to min tick time: {min_time}")
            start = min_time

        logger.info(f"🔄 Backfill range: {start} → {end}")

        # 4. Show current state
        logger.info("\n📈 Current view state:")
        for view in CONTINUOUS_AGGREGATES:
            count = await get_view_data_count(conn, view)
            logger.info(f"   {view}: {count:,} rows")

        # 5. Run backfill in dependency order
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting Backfill {'(DRY-RUN)' if dry_run else ''}")
        logger.info(f"{'='*60}")

        success_count = 0
        for view in CONTINUOUS_AGGREGATES:
            success = await refresh_continuous_aggregate(conn, view, start, end, dry_run)
            if success:
                success_count += 1
            else:
                logger.warning(f"⚠️ Stopping due to failure in {view}")
                break

        # 6. Show final state
        if not dry_run:
            logger.info("\n📈 Final view state:")
            for view in CONTINUOUS_AGGREGATES:
                count = await get_view_data_count(conn, view)
                logger.info(f"   {view}: {count:,} rows")

        logger.info(f"\n{'='*60}")
        logger.info(f"Backfill Complete: {success_count}/{len(CONTINUOUS_AGGREGATES)} views")
        logger.info(f"{'='*60}")

        return success_count == len(CONTINUOUS_AGGREGATES)

    finally:
        await conn.close()


async def main():
    parser = argparse.ArgumentParser(description='Backfill Continuous Aggregates from tick data')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)', default=None)
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)', default=None)
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no actual refresh)')

    args = parser.parse_args()

    start = datetime.strptime(args.start, '%Y-%m-%d') if args.start else None
    end = datetime.strptime(args.end, '%Y-%m-%d') if args.end else None

    success = await run_backfill(start, end, args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
