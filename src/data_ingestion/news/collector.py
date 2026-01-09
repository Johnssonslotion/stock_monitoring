import asyncio
import logging
import json
import feedparser
import redis.asyncio as redis
import os
from datetime import datetime
from src.core.schema import NewsAlert, MessageType

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NewsCollector")

# Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RSS_URLS = [
    "https://news.google.com/rss/search?q=stock+market+korea&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=economy&hl=ko&gl=KR&ceid=KR:ko"
]
KEYWORDS = ["삼성전자", "금리", "환율", "선거", "전쟁"]
POLL_INTERVAL = 60  # seconds

class NewsCollector:
    def __init__(self):
        self.redis = None
        self.seen_links = set()

    async def start(self):
        self.redis = await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        logger.info("NewsCollector started. Connected to Redis.")
        
        while True:
            await self.fetch_and_process()
            await asyncio.sleep(POLL_INTERVAL)

    async def fetch_and_process(self):
        for url in RSS_URLS:
            try:
                # Feedparser is blocking, run in executor
                feed = await asyncio.to_thread(feedparser.parse, url)
                
                for entry in feed.entries:
                    if entry.link in self.seen_links:
                        continue
                        
                    self.seen_links.add(entry.link)
                    
                    # Keyword matching
                    matched_keywords = [k for k in KEYWORDS if k in entry.title or k in entry.description]
                    
                    if matched_keywords:
                        await self.publish_alert(entry, matched_keywords)
                        
            except Exception as e:
                logger.error(f"Error fetching RSS {url}: {e}")

    async def publish_alert(self, entry, keywords):
        alert = NewsAlert(
            headline=entry.title,
            url=entry.link,
            source="Google News",
            keywords=keywords,
            timestamp=datetime.now()
        )
        
        # Publish to Redis
        await self.redis.publish("news_alert", alert.model_dump_json())
        logger.info(f"Published Alert: {alert.headline}")

if __name__ == "__main__":
    collector = NewsCollector()
    asyncio.run(collector.start())
