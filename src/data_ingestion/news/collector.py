import asyncio
import logging
import feedparser
import yaml
import os
import duckdb
from datetime import datetime
from typing import List, Dict, Optional
from src.core.config import settings

logger = logging.getLogger(__name__)

class NewsCollector:
    """
    뉴스 데이터 수집기 (News Collector)
    
    정의된 RSS 소스에서 뉴스를 가져와 키워드 필터링 후 DuckDB에 저장합니다.
    """
    
    def __init__(self, config_path: str = "src/data_ingestion/news/sources.yaml", db_path: str = "data/market_data.duckdb"):
        self.config_paths = config_path
        self.db_path = db_path
        self.running = False
        self.sources = []
        self.keywords = []
        
        self._load_config()
        self._init_db()

    def _load_config(self):
        """YAML 설정 로드"""
        try:
            with open(self.config_paths, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.sources = config.get('sources', [])
                self.keywords = [k.lower() for k in config.get('keywords', [])]
                logger.info(f"Loaded {len(self.sources)} sources and {len(self.keywords)} keywords.")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")

    def _init_db(self):
        """DuckDB news 테이블 생성"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self.conn = duckdb.connect(self.db_path)
            
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    source_name VARCHAR,
                    title VARCHAR,
                    link VARCHAR,
                    published_at TIMESTAMP,
                    matched_keywords VARCHAR,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (link)
                )
            """)
            logger.info("Connected to DuckDB (News Table)")
        except Exception as e:
            logger.error(f"DB Init Error: {e}")

    def filter_news(self, entry: Dict) -> Optional[Dict]:
        """
        뉴스 제목/요약에 키워드가 포함되어 있는지 확인.
        
        Returns:
            Dict: 저장할 데이터 (매칭 안되면 None)
        """
        title = entry.get('title', '').lower()
        summary = entry.get('summary', '').lower()
        content = title + " " + summary
        
        matched = []
        for kw in self.keywords:
            if kw in content:
                matched.append(kw)
        
        if matched:
            return {
                "title": entry.get('title'),
                "link": entry.get('link'),
                "published": entry.get('published', datetime.now().isoformat()),
                "keywords": ",".join(matched)
            }
        return None

    async def fetch_rss(self, source: Dict):
        """개별 RSS 피드 파싱"""
        logger.info(f"Fetching {source['name']}...")
        try:
            # feedparser는 blocking I/O이므로 executor에서 실행
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, source['url'])
            
            items_to_save = []
            for entry in feed.entries:
                filtered = self.filter_news(entry)
                if filtered:
                    filtered['source_name'] = source['name']
                    items_to_save.append(filtered)
            
            if items_to_save:
                self.save_to_db(items_to_save)
                
        except Exception as e:
            logger.error(f"Error fetching {source['name']}: {e}")

    def save_to_db(self, items: List[Dict]):
        """DuckDB 저장 (INSERT OR IGNORE)"""
        try:
            # DuckDB의 INSERT OR IGNORE 구문 활용 (Link 기준 중복 제거)
            data = [
                (i['source_name'], i['title'], i['link'], i['published'], i['keywords']) # published parsing needed?
                for i in items
            ]
            
            # published string -> timestamp 변환 처리가 필요할 수 있으나,
            # 일단 VARCHAR나 Auto Cast에 맡김. (실제 구현시 파싱 로직 보완 필요)
            
            self.conn.executemany("""
                INSERT OR IGNORE INTO news (source_name, title, link, published_at, matched_keywords)
                VALUES (?, ?, ?, ?, ?)
            """, data)
            logger.info(f"Saved {len(items)} news from {items[0]['source_name']}")
            
        except Exception as e:
            logger.error(f"DB Save Error: {e}")

    async def run(self, interval_seconds: int = 3600):
        self.running = True
        logger.info("Starting NewsCollector...")
        
        while self.running:
            tasks = [self.fetch_rss(source) for source in self.sources]
            await asyncio.gather(*tasks)
            
            logger.info(f"Cycle finished. Sleeping for {interval_seconds}s...")
            await asyncio.sleep(interval_seconds)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = NewsCollector()
    asyncio.run(collector.run(interval_seconds=60)) # Test with 60s
