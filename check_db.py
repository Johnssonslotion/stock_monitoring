import asyncio
import asyncpg
import json

async def check_data():
    try:
        conn = await asyncpg.connect(
            host="localhost",
            port=5433,
            user="postgres",
            password="password",
            database="backtest_db"
        )
        print("Connected to DB successfully.")
        
        # Check market_candles table
        count = await conn.fetchval("SELECT COUNT(*) FROM market_candles")
        print(f"market_candles count: {count}")
        
        if count > 0:
            latest = await conn.fetch("SELECT * FROM market_candles ORDER BY time DESC LIMIT 5")
            print("Latest market_candles:")
            for row in latest:
                print(dict(row))
                
        # Check public.candles_1m view
        try:
            v_count = await conn.fetchval("SELECT COUNT(*) FROM public.candles_1m")
            print(f"public.candles_1m count: {v_count}")
        except Exception as e:
            print(f"Could not query candles_1m view: {e}")

        await conn.close()
    except Exception as e:
        print(f"Error connecting to DB: {e}")

if __name__ == "__main__":
    asyncio.run(check_data())
