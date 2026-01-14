
import asyncio
import asyncpg
import os
from datetime import datetime, timezone

DB_HOST = "localhost"
DB_PORT = "5432"
DB_USER = "postgres"
DB_PASSWORD = "password"
DB_NAME = "stockval"

async def check_data():
    try:
        conn = await asyncpg.connect(
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        print("Connected to DB")
        
        # Check for today's data (UTC)
        # KR Market Open: 09:00 KST = 00:00 UTC
        # Today is 2026-01-13
        start_time = datetime(2026, 1, 13, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2026, 1, 14, 0, 0, 0, tzinfo=timezone.utc)
        
        print(f"Querying data between {start_time} and {end_time}")
        
        row_count = await conn.fetchval("""
            SELECT count(*) 
            FROM market_ticks 
            WHERE time >= $1 AND time < $2
        """, start_time, end_time)
        
        print(f"Total KR records today: {row_count}")
        
        if row_count > 0:
            latest = await conn.fetch("""
                SELECT time, symbol, price 
                FROM market_ticks 
                WHERE time >= $1 AND time < $2
                ORDER BY time DESC 
                LIMIT 5
            """, start_time, end_time)
            print("Latest 5 records:")
            for r in latest:
                print(f"{r['time']} - {r['symbol']}: {r['price']}")
                
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_data())
