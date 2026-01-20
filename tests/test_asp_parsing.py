import pytest
from src.data_ingestion.price.kr.asp_collector import KRASPCollector as KISASPCollector
from src.data_ingestion.price.us.asp_collector import USASPCollector as KISASPCollectorUS

def test_kr_orderbook_parsing():
    collector = KISASPCollector()
    # KIS KR Orderbook (H0STASP0) Mock Body
    # Format: "symbol^...^ask1^...^bid1^...^ask_vol1^...^bid_vol1..."
    # indices: symbol(0), ask1(3), bid1(13), ask_vol1(23), bid_vol1(33)
    mock_body = "005930^0^0^75000^75100^75200^75300^75400^0^0^0^0^0^74900^74800^74700^74600^74500^0^0^0^0^0^1000^2000^3000^4000^5000^0^0^0^0^0^1500^2500^3500^4500^5500"
    
    parsed = collector.parse_orderbook(mock_body)
    
    assert parsed is not None
    assert parsed.symbol == "005930"
    assert parsed.asks[0].price == 75000
    assert parsed.asks[0].vol == 1000
    assert parsed.bids[0].price == 74900
    assert parsed.bids[0].vol == 1500
    assert len(parsed.asks) == 5
    assert len(parsed.bids) == 5

def test_us_orderbook_parsing():
    collector = KISASPCollectorUS()
    # KIS US Orderbook (HDFSASP0) Mock Body
    # Format: "Exch^Sym^Time^...^Ask1^AskVol1^Bid1^BidVol1..."
    # indices: Sym(1), Ask1(10), AskVol1(11), Bid1(12), BidVol1(13)
    # Note: parsing logic uses index 10, 11, 12, 13 etc with +4 offset for each level
    # Mock fields: [0:Exch, 1:Sym, 2:Time, 3..9:Other, 10:Ask1, 11:AskVol1, 12:Bid1, 13:BidVol1, ...]
    fields = ["NAS", "AAPL", "130122", "0", "0", "0", "0", "0", "0", "0", 
              "200.50", "100", "200.40", "150", # Level 1
              "200.60", "200", "200.30", "250", # Level 2
              "200.70", "300", "200.20", "350", # Level 3
              "200.80", "400", "200.10", "450", # Level 4
              "200.90", "500", "200.00", "550"] # Level 5
    mock_body = "^".join(fields)
    
    parsed = collector.parse_us_orderbook(mock_body)
    
    assert parsed is not None
    assert parsed.symbol == "AAPL"
    assert parsed.asks[0].price == 200.50
    assert parsed.asks[0].vol == 100
    assert parsed.bids[0].price == 200.40
    assert parsed.bids[0].vol == 150
    assert len(parsed.asks) == 5
    assert len(parsed.bids) == 5

def test_kr_collector_syntax_validity():
    """ISSUE-021: Regression test for SyntaxError in KRASPCollector"""
    from src.data_ingestion.price.kr.asp_collector import KRASPCollector
    collector = KRASPCollector()
    assert collector is not None
    assert collector.get_channel() == "orderbook.kr"
    # Verify strict role separation logic (should return empty symbols)
    assert collector.load_symbols() == []
