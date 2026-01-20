
import pytest
import json
import asyncio
from unittest.mock import MagicMock, AsyncMock
from src.data_ingestion.price.common.websocket_dual import DualWebSocketManager
from src.data_ingestion.price.common.websocket_base import BaseCollector
from src.data_ingestion.price.kr.kiwoom_ws import KiwoomWSCollector 

@pytest.mark.asyncio
async def test_kis_dual_websocket_encrypt_header():
    """
    ISSUE-012 Verification: 
    Ensure KIS WebSocket requests include 'encrypt': 'N' in the header.
    """
    # Setup Mock Collector (Tick Type)
    mock_collector = MagicMock(spec=BaseCollector)
    mock_collector.tr_id = "H0STCNT0" # Recognized as TICK
    mock_collector.market = "KOSPI"
    mock_collector.symbols = ["005930"]
    
    # Setup Manager
    manager = DualWebSocketManager(collectors=[mock_collector], redis_url="redis://localhost:6379")
    manager.approval_key = "test_key"
    
    # Mock WebSocket and Inject
    mock_ws = AsyncMock()
    manager.ws_tick = mock_ws
    
    # Trigger Subscription
    # This will call _send_request via subscribe_market iteration
    await manager.subscribe_market("KOSPI")
    
    # Verification
    assert mock_ws.send.called, "❌ WebSocket.send() was not called!"
    
    # Inspect Payload
    call_args = mock_ws.send.call_args[0][0]
    payload = json.loads(call_args)
    header = payload.get('header', {})
    
    print(f"\n[Validation] KIS Header Sent: {header}")
    
    assert header.get('encrypt') == 'N', "❌ 'encrypt': 'N' header is MISSING in KIS request!"
    assert header.get('approval_key') == 'test_key'
    assert header.get('content-type') == 'utf-8'
    print("✅ KIS 'encrypt': 'N' Header Verified.")

@pytest.mark.asyncio
async def test_kiwoom_ws_send_method():
    """
    ISSUE-004 Verification: 
    Ensure Kiwoom Collector uses valid websockets method (send instead of send_json).
    """
    # Setup
    collector = KiwoomWSCollector(app_key="test", app_secret="test", symbols=["005930"])
    mock_ws = AsyncMock()
    
    # Mock the internal websocket object
    collector.ws = mock_ws
    
    # Execution
    # subscribe() does not exist. Call _subscribe_all() which triggers the send call.
    await collector._subscribe_all()
    
    # Verification
    # It should call send(), NOT send_json()
    assert mock_ws.send.called, "❌ KiwoomWSCollector did NOT call send()!"
    
    # Ensure send_json was NOT called (if it even exists on mock)
    # Note: AsyncMock creates attributes on access, so if code calls send_json, it would be recorded.
    if hasattr(mock_ws, 'send_json'):
         assert not mock_ws.send_json.called, "❌ KiwoomWSCollector called deprecated/invalid send_json()!"
    
    # Verify payload format if needed (json string)
    sent_data = mock_ws.send.call_args[0][0]
    assert isinstance(sent_data, str), "❌ KiwoomWSCollector must send JSON string"
    assert "005930" in sent_data
    print("✅ Kiwoom send() usage Verified.")
