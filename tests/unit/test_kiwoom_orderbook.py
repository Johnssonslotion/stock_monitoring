import pytest
from datetime import datetime
from src.data_ingestion.price.schemas.kiwoom_re import KiwoomOrderbookData

def test_kiwoom_orderbook_10level_parsing():
    # Mock Kiwoom 0D values (10 depth)
    # Asks: 27..36 prices, 61..70 vols
    # Bids: 17..26 prices, 71..80 vols
    # Totals: 121, 125
    mock_values = {}
    
    # Fill Asks
    for i in range(10):
        mock_values[str(27 + i)] = str(50000 + i * 100) # Prices
        mock_values[str(61 + i)] = str(10 + i)          # Vols
        
    # Fill Bids
    for i in range(10):
        mock_values[str(17 + i)] = str(49900 - i * 100) # Prices
        mock_values[str(71 + i)] = str(20 + i)          # Vols
        
    mock_values["121"] = "550" # Total Ask
    mock_values["125"] = "650" # Total Bid
    
    symbol = "005930"
    ob = KiwoomOrderbookData.from_ws_json(mock_values, symbol)
    
    assert ob.symbol == symbol
    assert len(ob.ask_prices) == 10
    assert len(ob.bid_prices) == 10
    assert len(ob.ask_volumes) == 10
    assert len(ob.bid_volumes) == 10
    
    # Check specific values
    assert ob.ask_prices[0] == 50000.0
    assert ob.ask_prices[9] == 50900.0
    assert ob.bid_prices[0] == 49900.0
    assert ob.bid_prices[9] == 49000.0
    
    assert ob.ask_volumes[0] == 10.0
    assert ob.ask_volumes[9] == 19.0
    assert ob.bid_volumes[0] == 20.0
    assert ob.bid_volumes[9] == 29.0
    
    assert ob.total_ask_volume == 550.0
    assert ob.total_bid_volume == 650.0

def test_kiwoom_orderbook_parsing_error():
    # pass invalid types to trigger ValueError
    with pytest.raises(ValueError):
        KiwoomOrderbookData.from_ws_json({"27": "NotAFloat"}, "005930")
