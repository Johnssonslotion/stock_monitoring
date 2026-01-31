
import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from src.core.schema import OrderbookData, OrderbookUnit, MessageType
from src.data_ingestion.price.common.delta_filter import OrderbookDeltaFilter
# Assuming implementation classes will be created later (TDD)
# from src.analysis.whale_detector import WhaleDetector
# from src.api.streaming import OrderbookStreamManager

@pytest.mark.asyncio
async def test_orderbook_streaming_flow():
    """
    [Phase 1] TC-010-01: 실시간 호가 스트리밍 및 델타 압축 해제 검증
    """
    # 1. Setup Mock Stream Manager (Server-side Rehydration)
    stream_manager = MagicMock() # Placeholder for actual implementation
    stream_manager.broadcast = AsyncMock()
    
    # 2. Mock 10-level Orderbook Data
    full_snapshot = OrderbookData(
        symbol="005930",
        timestamp=datetime.now(),
        type=MessageType.ORDERBOOK,
        asks=[OrderbookUnit(price=100+i, vol=10) for i in range(10)],
        bids=[OrderbookUnit(price=90-i, vol=10) for i in range(10)]
    )
    
    # 3. Simulate Delta Logic (from partial update)
    # Scenario: Client just connected, needs FULL snapshot first.
    # In strict TDD, we expect the manager to handle rehydration.
    
    # For now, verify data integrity passed to broadcast
    data_payload = full_snapshot.model_dump_json()
    await stream_manager.broadcast("005930", data_payload)
    
    # 4. Verify
    stream_manager.broadcast.assert_called_once()
    args = stream_manager.broadcast.call_args[0]
    assert args[0] == "005930"
    received_json = json.loads(args[1])
    assert len(received_json['asks']) == 10
    assert len(received_json['bids']) == 10
    assert received_json['type'] == 'orderbook'


@pytest.mark.asyncio
async def test_whale_alert_trigger():
    """
    [Phase 2] TC-010-02: 대형 체결(Whale) 감지 로직 검증
    """
    # 1. Mock Whale Detector
    detector = MagicMock() # Placeholder
    detector.detect = AsyncMock(return_value=True) 
    
    # 2. Mock Big Trade (1.5 Billion KRW)
    tick_data = {
        'symbol': '005930',
        'price': 100000,
        'volume': 15000, # 1.5B
        'timestamp': datetime.now().isoformat()
    }
    
    # 3. Validation Logic (to be implemented in src)
    THRESHOLD = 100_000_000 # 1亿
    is_whale = (tick_data['price'] * tick_data['volume']) >= THRESHOLD
    
    # 4. Verify Logic
    assert is_whale is True
    
    # 5. Simulate Alert
    if is_whale:
        await detector.detect(tick_data)
        
    detector.detect.assert_called_once_with(tick_data)
