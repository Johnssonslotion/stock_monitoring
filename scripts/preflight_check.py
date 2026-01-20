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
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PreFlight")

# Status Flags
STATUS = {
    "SMOKE_TEST": False,
    "KIS_API": False,
    "KIWOOM_API": False,
    "REDIS": False,
    "TIMESCALE": False,
    "DISK": False
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
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        await r.ping()
        await r.close()
        logger.info("✅ Redis: Connected")
        STATUS["REDIS"] = True
    except Exception as e:
        logger.error(f"❌ Redis: Exception {e}")

async def check_timescaledb():
    try:
        conn = await asyncpg.connect(
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "password"),
            database=os.getenv("DB_NAME", "stockval"),
            host=os.getenv("DB_HOST", "localhost"),
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

async def main():
    logger.info("🚀 Starting Pre-flight Check for Market Open...")
    
    # 0. Smoke Test (Blocking)
    if not run_smoke_test():
        logger.error("🚨 Smoke Test Failed. Aborting Pre-flight Check.")
        sys.exit(1)
    
    await asyncio.gather(
        check_kis_api(),
        check_kiwoom_api(),
        check_redis(),
        check_timescaledb(),
        check_disk_space()
    )
    
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
