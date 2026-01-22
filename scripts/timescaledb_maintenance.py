import asyncio
import os
import logging
import asyncpg
from datetime import datetime

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DBOptimization")

# Database configuration from environment variables
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

async def apply_optimization():
    """
    Applies TimescaleDB optimizations (Compression & Retention)
    to market_ticks and market_orderbook tables.
    """
    logger.info(f"Connecting to TimescaleDB at {DB_HOST}:{DB_PORT} as {DB_USER}...")
    
    try:
        conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            port=DB_PORT
        )
        
        logger.info("Successfully connected to the database.")
        
        tables = ['market_ticks', 'market_orderbook']
        
        for table in tables:
            logger.info(f"⚙️ Optimizing table: {table}")
            
            # 1. Enable Compression (if not already enabled)
            try:
                await conn.execute(f"""
                    ALTER TABLE {table} SET (
                        timescaledb.compress,
                        timescaledb.compress_segmentby = 'symbol',
                        timescaledb.compress_orderby = 'time DESC'
                    );
                """)
                logger.info(f"   ✅ Compression enabled for {table}")
            except Exception as e:
                if "already has compression enabled" in str(e):
                    logger.info(f"   ℹ️ Compression already enabled for {table}")
                else:
                    logger.error(f"   ❌ Failed to enable compression for {table}: {e}")

            # 2. Add Compression Policy (1 day)
            try:
                await conn.execute(f"SELECT add_compression_policy('{table}', INTERVAL '1 day', if_not_exists => TRUE);")
                logger.info(f"   ✅ Compression policy (1 day) added for {table}")
            except Exception as e:
                logger.error(f"   ❌ Failed to add compression policy for {table}: {e}")

            # 3. Add Retention Policy (7 days)
            try:
                await conn.execute(f"SELECT add_retention_policy('{table}', INTERVAL '7 days', if_not_exists => TRUE);")
                logger.info(f"   ✅ Retention policy (7 days) added for {table}")
            except Exception as e:
                logger.error(f"   ❌ Failed to add retention policy for {table}: {e}")

        # 4. Manual Maintenance: Run compression on old chunks immediately (one-time if needed)
        # For now, let the background policy handle it.
        
        await conn.close()
        logger.info("🚀 Database optimization task completed successfully.")
        
    except Exception as e:
        logger.error(f"🔥 Critical error during database optimization: {e}")

if __name__ == "__main__":
    asyncio.run(apply_optimization())
