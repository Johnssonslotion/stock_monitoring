import pytest
import json
from datetime import datetime
from src.core.schema import MarketData, OrderbookData, OrderbookUnit, MessageType
from pydantic import ValidationError

def test_producer_consumer_contract_market_data():
    """Validates that data produced by collectors matches consumer expectations (Strict Tier 2)."""
    
    # 1. Producer Simulation (Valid)
    # Collectors use model_dump_json()
    producer_obj = MarketData(
        symbol="AAPL",
        price=150.0,
        change=1.5,
        volume=1000,
        timestamp=datetime.now()
    )
    payload = producer_obj.model_dump_json()
    
    # 2. Consumer Simulation (Valid)
    # Consumers load JSON and instantiate Model
    data = json.loads(payload)
    consumer_obj = MarketData(**data)
    
    assert consumer_obj.symbol == "AAPL"
    assert consumer_obj.price == 150.0
    
    # 3. Invalid Data Injection (Simulating bug in producer or bad external data)
    # If a producer somehow bypassed strict validation (e.g. constructing dict manually)
    bad_payload = json.dumps({
        "type": "ticker",
        "symbol": "AAPL",
        "price": -100.0, # Negative Price
        "change": 0,
        "volume": 100,
        "timestamp": datetime.now().isoformat()
    })
    
    # Consumer MUST reject this
    with pytest.raises(ValidationError):
        MarketData(**json.loads(bad_payload))

def test_producer_consumer_contract_orderbook():
    """Validates Orderbook data contract."""
    
    # 1. Producer Simulation
    producer_obj = OrderbookData(
        symbol="005930",
        asks=[OrderbookUnit(price=100, vol=10)],
        bids=[OrderbookUnit(price=99, vol=10)]
    )
    payload = producer_obj.model_dump_json()
    
    # 2. Consumer Simulation
    consumer_obj = OrderbookData(**json.loads(payload))
    assert len(consumer_obj.asks) == 1
    assert consumer_obj.asks[0].price == 100
    
    # 3. Invalid Orderbook Unit
    bad_payload = json.dumps({
        "type": "orderbook",
        "symbol": "005930",
        "asks": [{"price": -50, "vol": 10}], # Negative Price
        "bids": [],
        "timestamp": datetime.now().isoformat()
    })
    
    with pytest.raises(ValidationError):
        OrderbookData(**json.loads(bad_payload))
