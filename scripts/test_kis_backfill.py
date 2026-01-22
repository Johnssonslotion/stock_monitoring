import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from src.data_ingestion.recovery.backfill_manager import BackfillManager

load_dotenv()

async def test_backfill():
    manager = BackfillManager()
    token = await manager.auth_manager.get_access_token()
    print(f"Token: {token[:10]}...")
    
    async with aiohttp.ClientSession() as session:
        # Try generic Samsung tick fetch
        await manager.fetch_real_ticks(session, "005930", token)

if __name__ == "__main__":
    asyncio.run(test_backfill())
