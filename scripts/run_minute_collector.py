
import asyncio
import logging
from src.data_ingestion.history.collector import HistoryCollector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    collector = HistoryCollector()
    await collector.run()

if __name__ == "__main__":
    asyncio.run(main())
