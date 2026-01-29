import pytest
from datetime import datetime
from src.data_ingestion.price.common.delta_filter import OrderbookDeltaFilter

def test_orderbook_delta_filter():
    filter = OrderbookDeltaFilter()
    symbol = "005930"
    
    # 1. First data should always be published
    data1 = {
        "ask_prices": [50000.0] * 10,
        "bid_prices": [49900.0] * 10,
        "ask_volumes": [100.0] * 10,
        "bid_volumes": [200.0] * 10,
        "timestamp": datetime.now()
    }
    assert filter.should_publish(symbol, data1) is True
    
    # 2. Identical data should not be published
    data2 = data1.copy()
    data2["timestamp"] = datetime.now() # Timestamp varies but prices/vols are same
    assert filter.should_publish(symbol, data2) is False
    
    # 3. Changed data should be published
    data3 = data1.copy()
    data3["ask_prices"] = [50100.0] + [50000.0] * 9 # Change first ask price
    assert filter.should_publish(symbol, data3) is True
    
    # 4. Another symbol should be published
    symbol2 = "000660"
    assert filter.should_publish(symbol2, data1) is True

def test_orderbook_delta_filter_reset():
    filter = OrderbookDeltaFilter()
    symbol = "005930"
    data = {
        "ask_prices": [1.0] * 10,
        "bid_prices": [1.0] * 10,
        "ask_volumes": [1.0] * 10,
        "bid_volumes": [1.0] * 10
    }
    
    assert filter.should_publish(symbol, data) is True
    assert filter.should_publish(symbol, data) is False
    
    filter.reset(symbol)
    assert filter.should_publish(symbol, data) is True
