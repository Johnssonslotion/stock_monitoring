#!/usr/bin/env python3
"""
Apply DB Migrations using asyncpg
"""
import asyncio
import os
import asyncpg
from dotenv import load_dotenv

# Load env
load_dotenv(".env.backtest")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")

async def main():
    print(f"📡 Connecting to DB {DB_HOST}:{DB_PORT}/{DB_NAME}...")
    try:
        conn = await asyncpg.connect(
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    migration_file = "scripts/db/migrations/002_add_source_and_depth.sql"
    
    print(f"📄 Reading migration file: {migration_file}")
    with open(migration_file, 'r') as f:
        sql = f.read()

    print("🚀 Executing migration...")
    try:
        await conn.execute(sql)
        print("✅ Migration successful!")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
