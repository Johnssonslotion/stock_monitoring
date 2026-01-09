import pytest
import asyncio
from unittest.mock import MagicMock, patch
from src.data_ingestion.news.collector import NewsCollector

@pytest.fixture
def collector():
    return NewsCollector()

@pytest.mark.asyncio
async def test_news_processing_and_publish(collector):
    """뉴스 수집 후 키워드 매칭 및 Redis 발행 검증"""
    # 1. Mock RSS Feed
    mock_entry = MagicMock()
    mock_entry.title = "삼성전자 영업이익 급증"
    mock_entry.description = "반도체 호재로 인한..."
    mock_entry.link = "http://news.com/1"
    
    mock_feed = MagicMock()
    mock_feed.entries = [mock_entry]
    
    # 2. Setup Redis Mock
    import mock
    collector.redis = mock.AsyncMock()
    
    # 3. Patch asyncio.to_thread to return our mock feed
    with patch("asyncio.to_thread", return_value=mock_feed):
        await collector.fetch_and_process()
    
    # Check if publish was called because "삼성전자" is in KEYWORDS
    collector.redis.publish.assert_called_once()
    call_args = collector.redis.publish.call_args
    assert call_args[0][0] == "news_alert"
    assert "삼성전자" in call_args[0][1]

@pytest.mark.asyncio
async def test_news_duplicate_filter(collector):
    """중복 기사 필터링 검증"""
    mock_entry = MagicMock()
    mock_entry.title = "삼성전자"
    mock_entry.link = "http://news.com/dup"
    
    mock_feed = MagicMock()
    mock_feed.entries = [mock_entry]
    
    import mock
    collector.redis = mock.AsyncMock()
    
    with patch("asyncio.to_thread", return_value=mock_feed):
        # First fetch
        await collector.fetch_and_process()
        # Second fetch
        await collector.fetch_and_process()
    
    # Should only publish once
    assert collector.redis.publish.call_count == 1
