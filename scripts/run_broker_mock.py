import asyncio
import logging
import sys
import os

# root path setup
sys.path.append(os.getcwd())

from src.trading.orchestrator import BrokerOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mock_runner")

async def run_simulation():
    # 1. Configuration (Mock Mode)
    config = {
        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        "use_mock": True,
        "brokers": {
            "mirae": {"app_key": "dummy", "app_secret": "dummy"},
            "kiwoom_re": {"app_key": "dummy"}
        }
    }

    # 2. Orchestrator Setup
    orc = BrokerOrchestrator(config)
    orc.setup_brokers(["mirae", "kiwoom_re"])

    # 3. Symbols to Mock
    symbols = {
        "mirae": ["005930", "000660"],
        "kiwoom_re": ["069500", "114800"] # KODEX 200, KODEX Inverse
    }

    logger.info("🏁 Starting Mock Simulation... (Duration: 10s)")
    
    # 4. Start Simulation
    try:
        await orc.start_all(symbols)
        # 10초간 스케줄링 유지
        await asyncio.sleep(10)
    except Exception as e:
        logger.error(f"Simulation Error: {e}")
    finally:
        await orc.stop_all()
        logger.info("🏁 Simulation Finished")

if __name__ == "__main__":
    asyncio.run(run_simulation())
