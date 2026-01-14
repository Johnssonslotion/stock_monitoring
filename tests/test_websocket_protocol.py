import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from src.data_ingestion.price.common.websocket_dual import DualWebSocketManager

@pytest.fixture
def mock_collectors():
    return []

@pytest.fixture
def manager(mock_collectors):
    return DualWebSocketManager(collectors=mock_collectors, redis_url="redis://localhost:6379")

@pytest.mark.asyncio
async def test_handle_message_valid_tick(manager):
    """Test handling of a valid pipe-delimited tick message."""
    # Mocking a valid tick message format: 
    # 0|TR_ID|001|BODY_CONTENT
    message = "0|H0STCNT0|001|12345^78900^..."
    
    # We need to mock a collector for this TR_ID to avoid "Unknown TR_ID"
    mock_collector = MagicMock()
    mock_collector.tr_id = "H0STCNT0"
    mock_collector.parse_tick.return_value = None # Just to avoid redis publish error
    manager.collectors["H0STCNT0"] = mock_collector
    
    res = await manager._handle_message(message, source="tick")
    assert res == "H0STCNT0"

@pytest.mark.asyncio
async def test_handle_message_protocol_error(manager):
    """Test handling of a JSON protocol error message."""
    # Example error message from KIS
    message = '{"header": {"tr_id": "H0STCNT0", "tr_key": "xxx", "encrypt": "N"}, "body": {"msg1": "invalid tr_key"}}'
    
    # Currently, without modification, this might be ignored or fail parsing
    # The goal is to have it return None (or a specific error signal) and log an error
    res = await manager._handle_message(message, source="tick")
    
    # After implementation, we expect this to return "ERROR"
    assert res == "ERROR"

@pytest.mark.asyncio
async def test_handle_message_pingpong(manager):
    """Test handling of PINGPONG message."""
    message = '{"header":{"tr_id":"PINGPONG","datetime":"20230101120000"}}'
    res = await manager._handle_message(message, source="tick")
    assert res == "PONG"
