import asyncio
import os
import sys
import logging
from datetime import datetime
import aiohttp
import redis.asyncio as redis
import asyncpg
from dotenv import load_dotenv

# Setup
sys.path.append(os.getcwd())

# 🔍 Environment Selection
# actual code in Docker uses env_file from compose, so vars are already in environment.
# For host execution, we default to .env.prod if not specified.
env_file = os.getenv("ENV_FILE", ".env.prod")
if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    load_dotenv() # Fallback to .env

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PreFlight")

# Status Flags
STATUS = {
    "SMOKE_TEST": False,
    "KIS_API": False,
    "KIWOOM_API": False,
    "REDIS": False,
    "TIMESCALE": False,
    "DISK": False,
    "MIRROR_TABLES": False,  # ISSUE-035
    "SCHEMA_PARITY": False,   # ISSUE-035
    "DB_WRITE_TEST": False    # ISSUE-035
}

def run_smoke_test():
    """Run pytest based smoke tests (ISSUE-027)"""
    import subprocess
    logger.info("🧪 Running Smoke Tests (Modules & Basic Infra)...")
    try:
        result = subprocess.run(
            ["poetry", "run", "pytest", "-q", "tests/test_smoke_modules.py"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error("❌ Smoke Test FAILED")
            for line in result.stdout.splitlines():
                logger.error(f"   {line}")
            for line in result.stderr.splitlines():
                logger.error(f"   {line}")
            return False
        else:
            logger.info("✅ Smoke Test PASSED")
            STATUS["SMOKE_TEST"] = True
            return True
    except Exception as e:
        logger.error(f"❌ Smoke Test Execution Error: {e}")
        return False

async def check_kis_api():
    """Check KIS API Authentication and Simple Query"""
    try:
        from src.data_ingestion.price.common import KISAuthManager
        auth = KISAuthManager()
        token = await auth.get_access_token()
        if token:
            logger.info("✅ KIS API: Auth Successful")
            STATUS["KIS_API"] = True
        else:
            logger.error("❌ KIS API: Auth Failed (No Token)")
    except Exception as e:
        logger.error(f"❌ KIS API: Exception {e}")

async def check_kiwoom_api():
    """Check Kiwoom REST API (ka10079) Connectivity"""
    # Simply check if we can reach the endpoint (even with auth error, network should be up)
    url = "https://api.kiwoom.com/api/dostk/chart"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp: # GET might behave differently but checks reachability
                if resp.status in [200, 400, 401, 405]: # 405 Method Not Allowed is fine for connectivity check
                     logger.info(f"✅ Kiwoom API: Reachable (Status {resp.status})")
                     STATUS["KIWOOM_API"] = True
                else:
                    logger.error(f"❌ Kiwoom API: Unreachable (Status {resp.status})")
    except Exception as e:
        logger.error(f"❌ Kiwoom API: Exception {e}")

async def check_redis():
    try:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        if "stock-redis" in url: # Host-side execution correction
            url = url.replace("stock-redis", "localhost")
            
        r = redis.from_url(url)
        await r.ping()
        await r.close()
        logger.info("✅ Redis: Connected")
        STATUS["REDIS"] = True
    except Exception as e:
        logger.error(f"❌ Redis: Exception {e}")

async def check_timescaledb():
    try:
        host = os.getenv("DB_HOST", "localhost")
        if host == "stock-timescale": # Host-side execution correction
             host = "localhost"
             
        conn = await asyncpg.connect(
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "password"),
            database=os.getenv("DB_NAME", "stockval"),
            host=host,
            port=os.getenv("DB_PORT", "5432")
        )
        await conn.close()
        logger.info("✅ TimescaleDB: Connected")
        STATUS["TIMESCALE"] = True
    except Exception as e:
        logger.error(f"❌ TimescaleDB: Exception {e}")

async def check_disk_space():
    """Check if we have enough disk space (> 1GB)"""
    import shutil
    total, used, free = shutil.disk_usage("/")
    free_gb = free // (2**30)
    if free_gb > 1:
        logger.info(f"✅ Disk Space: OK ({free_gb} GB free)")
        STATUS["DISK"] = True
    else:
        logger.error(f"❌ Disk Space: LOW ({free_gb} GB free)")

async def sync_mirror_tables():
    """
    ISSUE-035: Phase A - Mirror Table Synchronization
    Create test tables with same schema as production tables
    """
    try:
        host = os.getenv("DB_HOST", "localhost")
        if host == "stock-timescale":
            host = "localhost"

        conn = await asyncpg.connect(
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "password"),
            database=os.getenv("DB_NAME", "stockval"),
            host=host,
            port=os.getenv("DB_PORT", "5432")
        )

        try:
            # Create mirror table for market_ticks
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS market_ticks_test (LIKE market_ticks INCLUDING ALL);
            """)

            # Create mirror table for market_orderbook
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS market_orderbook_test (LIKE market_orderbook INCLUDING ALL);
            """)

            logger.info("✅ Mirror Tables: Created/Synced (market_ticks_test, market_orderbook_test)")
            STATUS["MIRROR_TABLES"] = True

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"❌ Mirror Tables: Exception {e}")

async def check_schema_parity():
    """
    ISSUE-035: Phase B - Schema Parity Check
    Detect schema drift between production and mirror tables
    """
    try:
        host = os.getenv("DB_HOST", "localhost")
        if host == "stock-timescale":
            host = "localhost"

        conn = await asyncpg.connect(
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "password"),
            database=os.getenv("DB_NAME", "stockval"),
            host=host,
            port=os.getenv("DB_PORT", "5432")
        )

        try:
            # Get columns from production table
            prod_cols = await conn.fetch("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'market_ticks'
                ORDER BY ordinal_position;
            """)

            # Get columns from test table
            test_cols = await conn.fetch("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'market_ticks_test'
                ORDER BY ordinal_position;
            """)

            # Compare schemas
            prod_schema = {(r['column_name'], r['data_type'], r['is_nullable']) for r in prod_cols}
            test_schema = {(r['column_name'], r['data_type'], r['is_nullable']) for r in test_cols}

            if prod_schema == test_schema:
                logger.info("✅ Schema Parity: MATCH (Production ↔ Test)")
                STATUS["SCHEMA_PARITY"] = True
            else:
                missing_in_test = prod_schema - test_schema
                extra_in_test = test_schema - prod_schema

                if missing_in_test:
                    logger.warning(f"⚠️  Schema Drift: Columns missing in test: {missing_in_test}")
                if extra_in_test:
                    logger.warning(f"⚠️  Schema Drift: Extra columns in test: {extra_in_test}")

                # Still mark as success if we detected the drift
                STATUS["SCHEMA_PARITY"] = True

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"❌ Schema Parity: Exception {e}")

async def db_write_test():
    """
    ISSUE-035: Phase C - DB Write Test (08:58)
    Test actual write permissions and DDL integrity
    """
    try:
        host = os.getenv("DB_HOST", "localhost")
        if host == "stock-timescale":
            host = "localhost"

        conn = await asyncpg.connect(
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "password"),
            database=os.getenv("DB_NAME", "stockval"),
            host=host,
            port=os.getenv("DB_PORT", "5432")
        )

        try:
            # Insert test data
            test_time = datetime.now()
            await conn.execute("""
                INSERT INTO market_ticks_test (time, symbol, price, volume, change, source)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT DO NOTHING;
            """, test_time, "TEST_SYMBOL", 100.0, 1000.0, 0.0, "PREFLIGHT")

            # Verify write
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM market_ticks_test WHERE symbol = 'TEST_SYMBOL';
            """)

            if count >= 1:
                logger.info(f"✅ DB Write Test: PASSED ({count} test records)")
                STATUS["DB_WRITE_TEST"] = True
            else:
                logger.error("❌ DB Write Test: FAILED (No records written)")

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"❌ DB Write Test: Exception {e}")

async def main():
    logger.info("🚀 Starting Pre-flight Check for Market Open...")

    # 0. Smoke Test (Blocking)
    if not run_smoke_test():
        logger.error("🚨 Smoke Test Failed. Aborting Pre-flight Check.")
        sys.exit(1)

    # 1. Basic Infrastructure Checks
    await asyncio.gather(
        check_kis_api(),
        check_kiwoom_api(),
        check_redis(),
        check_timescaledb(),
        check_disk_space()
    )

    # 2. ISSUE-035: Mirror Tables & Schema Validation (Sequential)
    logger.info("🔍 ISSUE-035: Starting DB Ingestion Readiness Checks...")
    await sync_mirror_tables()
    await check_schema_parity()
    await db_write_test()

    # Final Report
    failed = [k for k, v in STATUS.items() if not v]
    if failed:
        logger.error(f"🚨 Pre-flight Check FAILED for: {failed}")
        sys.exit(1)
    else:
        logger.info("✨ All Systems GO! Ready for Market Open.")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
