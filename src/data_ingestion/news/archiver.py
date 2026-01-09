import asyncio
import json
import logging
import os
from datetime import datetime
import duckdb
import redis.asyncio as redis
from src.core.config import settings
from src.core.schema import NewsAlert

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NewsArchiver")

# Config
REDIS_URL = os.getenv("REDIS_URL", settings.data.redis_url)
DB_PATH = os.getenv("DB_PATH", "data/market_data.duckdb")

class NewsArchiver:
    def __init__(self):
        self.redis = None
        self.running = True
        self._init_db()

    def _init_db(self):
        """Initialize DuckDB table for News and ensure all columns exist"""
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.conn = duckdb.connect(DB_PATH)
        
        # Check if schema matches current needs
        try:
            res = self.conn.execute("PRAGMA table_info(news)").fetchall()
            existing_cols = [r[1] for r in res]
            logger.info(f"Existing columns in 'news': {existing_cols}")
            
            # If 'published' column is missing, it's the old/wrong schema
            if res and "published" not in existing_cols:
                logger.warning("Detected old news table schema. Dropping and recreating...")
                self.conn.execute("DROP TABLE news")
        except Exception as e:
            logger.error(f"Error checking table schema: {e}")

        # Table schema aligned with dashboard/app.py expectations
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS news (
                published_at TIMESTAMP,
                published VARCHAR,
                title VARCHAR,
                source VARCHAR,
                link VARCHAR,
                keywords JSON,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info(f"Connected to DuckDB: {DB_PATH}")

    async def start(self):
        self.redis = await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        logger.info(f"NewsArchiver started. Subscribed to 'news_alert' via {REDIS_URL}")

        pubsub = self.redis.pubsub()
        await pubsub.subscribe("news_alert")

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    # Parse using Pydantic for validation
                    alert = NewsAlert(**data)
                    
                    self.save_to_db(alert)
                except Exception as e:
                    logger.error(f"Error processing news alert: {e}")

    def save_to_db(self, alert: NewsAlert):
        """Save a single news alert to DuckDB"""
        try:
            published_at = alert.timestamp
            published_str = published_at.strftime("%Y-%m-%d %H:%M:%S")
            title = alert.headline
            source = alert.source
            link = alert.url
            keywords_json = json.dumps(alert.keywords)

            self.conn.execute("""
                INSERT INTO news (published_at, published, title, source, link, keywords)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (published_at, published_str, title, source, link, keywords_json))
            
            logger.info(f"Archived news: {title}")
        except Exception as e:
            logger.error(f"Failed to save to DuckDB: {e}")

if __name__ == "__main__":
    archiver = NewsArchiver()
    asyncio.run(archiver.start())
