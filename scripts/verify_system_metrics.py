
import asyncio
import asyncpg
import os
from datetime import datetime

# Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")

async def verify_system_metrics():
    print("🔍 Connecting to TimescaleDB to verify system metrics...")
    try:
        conn = await asyncpg.connect(
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        
        # Check Table Count
        rows = await conn.fetch("SELECT * FROM system_metrics ORDER BY time DESC LIMIT 20")
        
        if not rows:
            print("⚠️  No metrics found in 'system_metrics' table yet.")
        else:
            print(f"✅ Found {len(rows)} recent metrics:")
            for row in rows:
                meta_str = f" | {row['meta']}" if row['meta'] else ""
                print(f"   [{row['time']}] {row['type']}: {row['value']}{meta_str}")
                
        await conn.close()
        
    except Exception as e:
        print(f"❌ Verification Failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_system_metrics())
