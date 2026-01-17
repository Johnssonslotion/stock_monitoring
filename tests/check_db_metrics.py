import asyncpg
import asyncio
import os

async def check():
    conn = await asyncpg.connect(
        user='postgres', 
        password='password', 
        database='stockval', 
        host='localhost'
    )
    rows = await conn.fetch("SELECT type, count(*) FROM system_metrics GROUP BY type;")
    for r in rows:
        print(f"{r[0]}: {r[1]}")
    
    print("\nLatest CPU data:")
    cpu_rows = await conn.fetch("SELECT time, value FROM system_metrics WHERE type='cpu' ORDER BY time DESC LIMIT 5;")
    for r in cpu_rows:
        print(f"{r[0]} | {r[1]}")
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check())
