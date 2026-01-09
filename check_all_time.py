import asyncio
import asyncpg

async def check_all_data():
    try:
        conn = await asyncpg.connect(
            user="postgres", 
            password="password", 
            database="stockval", 
            host="localhost"
        )
        
        # Check any data in market_ticks (ever)
        all_time = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total,
                MIN(time) as first,
                MAX(time) as last,
                COUNT(DISTINCT symbol) as symbols
            FROM market_ticks
        """)
        
        print(f"=== All-Time Market Ticks Data ===")
        print(f"Total: {all_time['total']}")
        print(f"Symbols: {all_time['symbols']}")
        print(f"First: {all_time['first']}")
        print(f"Last: {all_time['last']}")
        
        # Check last 3 days
        if all_time['total'] > 0:
            recent = await conn.fetch("""
                SELECT DATE(time) as date, COUNT(*) as count
                FROM market_ticks
                WHERE time >= NOW() - INTERVAL '3 days'
                GROUP BY DATE(time)
                ORDER BY date DESC
            """)
            print(f"\nLast 3 days:")
            for r in recent:
                print(f"  {r['date']}: {r['count']} ticks")
        
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(check_all_data())
