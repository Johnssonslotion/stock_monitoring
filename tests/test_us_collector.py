import pytest
import json
from src.data_ingestion.price.real_collector_us import KISRealCollectorUS

@pytest.fixture
def collector():
    return KISRealCollectorUS()

def test_parse_us_tick_data(collector):
    """
    미국 시장 실시간 체결가(HDFSCNT0) 데이터 파싱 테스트.
    """
    # Mock US Tick Data (HDFSCNT0)
    # Field 1: Sym, Field 11: Price, Field 13: Vol
    fields = ["RS", "AAPL", "130122", "0", "0", "0", "0", "0", "0", "0", "0", "200.50", "0", "1500", "0"]
    mock_msg = "^".join(fields)
    
    parsed_data = collector.parse_us_tick(mock_msg)
    
    assert parsed_data is not None
    assert parsed_data.symbol == "AAPL"
    assert parsed_data.price == 200.50
    assert parsed_data.volume == 1500

@pytest.mark.asyncio
async def test_parse_us_websocket_message(collector):
    """
    전체 웹소켓 메시지 프레임 파워징 테스트 (US)
    handle_message is async in current version.
    """
    fields = ["RS", "TSLA", "160000", "0", "0", "0", "0", "0", "0", "0", "0", "250.00", "0", "5000", "0"]
    body = "^".join(fields)
    raw_msg = f"0|HDFSCNT0|001|{body}"
    
    # Needs redis mock if handle_message publishes. 
    # But since handle_message is what we want to test, let's see if we can trigger it.
    # In real_collector_us.py, handle_message calls redis.publish, so we need to mock it.
    from unittest import mock
    collector.redis = mock.AsyncMock()
    
    res = await collector.handle_message(raw_msg)
    assert res == "HDFSCNT0"
    collector.redis.publish.assert_called()
