import pytest
import os
import duckdb
import yaml
from unittest.mock import MagicMock, patch
from src.data_ingestion.news.collector import NewsCollector

# Test Config
TEST_DB_PATH = "data/test_market_data.duckdb"
TEST_CONFIG_PATH = "tests/test_sources.yaml"

@pytest.fixture
def collector_config():
    # Create temp config
    config = {
        "sources": [{"name": "test_src", "type": "rss", "url": "http://test.com"}],
        "keywords": ["election", "금투세"]
    }
    with open(TEST_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f)
    
    yield TEST_CONFIG_PATH
    
    if os.path.exists(TEST_CONFIG_PATH):
        os.remove(TEST_CONFIG_PATH)

@pytest.fixture
def collector(collector_config):
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        
    c = NewsCollector(config_path=TEST_CONFIG_PATH, db_path=TEST_DB_PATH)
    return c

def test_filter_news(collector):
    """키워드 필터링 로직 검증"""
    # 1. Match Case
    entry_match = {"title": "Election results updated", "summary": "Trump wins...", "link": "http://a.com"}
    result = collector.filter_news(entry_match)
    assert result is not None
    assert "election" in result["keywords"]

    # 2. No Match Case
    entry_no_match = {"title": "Today's weather", "summary": "Sunny", "link": "http://b.com"}
    result = collector.filter_news(entry_no_match)
    assert result is None
    
    # 3. Case Insensitive Check
    entry_case = {"title": "금투세 폐지 논의", "summary": "...", "link": "http://c.com"}
    result = collector.filter_news(entry_case)
    assert result is not None
    assert "금투세" in result["keywords"]

def test_save_to_db(collector):
    """DuckDB 저장 검증"""
    items = [
        {
            "source_name": "test_src",
            "title": "Test Title",
            "link": "http://test.com/1",
            "published": "2024-01-04T12:00:00",
            "keywords": "election"
        }
    ]
    
    collector.save_to_db(items)
    
    # Verify
    conn = duckdb.connect(TEST_DB_PATH)
    res = conn.execute("SELECT title, matched_keywords FROM news").fetchall()
    conn.close()
    
    assert len(res) == 1
    assert res[0][0] == "Test Title"
    assert res[0][1] == "election"

@pytest.mark.asyncio
async def test_fetch_rss_mock(collector):
    """RSS Fetch Mocking Test"""
    # Mock feedparser.parse
    mock_feed = MagicMock()
    mock_feed.entries = [
        {"title": "Election News", "summary": "Big news", "link": "http://t.com/1", "published": "2024-01-01 12:00:00"},
        {"title": "Boring News", "summary": "Nothing", "link": "http://t.com/2", "published": "2024-01-01 12:00:00"}
    ]
    
    with patch("feedparser.parse", return_value=mock_feed):
        # We need to manually call fetch_rss for a single source
        source = collector.sources[0]
        await collector.fetch_rss(source)
        
        # Check DB -> Only 1 should be saved
        conn = duckdb.connect(TEST_DB_PATH)
        count = conn.execute("SELECT count(*) FROM news").fetchone()[0]
        conn.close()
        
        assert count == 1
