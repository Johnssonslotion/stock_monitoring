
import asyncio
import asyncpg
import os
from datetime import datetime

async def main():
    try:
        # Defaults from collector.py
        conn = await asyncpg.connect(user="postgres", password="password", database="stockval", host="localhost")
        
        # Check Samsung Electronics (005930) as a proxy for KR market
        row = await conn.fetchrow("SELECT MAX(time) as last_time FROM market_minutes WHERE symbol = '005930'")
        print(f"Last time for 005930 (Samsung Elec): {row['last_time']}")
        
        # Check US symbol if possible (e.g. AAPL)
        row_us = await conn.fetchrow("SELECT MAX(time) as last_time FROM market_minutes WHERE symbol = 'AAPL'")
        print(f"Last time for AAPL: {row_us['last_time']}")
        
        await conn.close()
    except Exception as e:
        print(f"Error accessing DB: {e}")

if __name__ == "__main__":
    asyncio.run(main())
