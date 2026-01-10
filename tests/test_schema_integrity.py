import pytest
from src.core.schema import MarketData, MessageType
from datetime import datetime

def test_market_data_schema_integrity():
    """
    MarketData 스키마가 비정상적인 데이터 인입 시 어떻게 반응하는지 검증 (Tier 2)
    """
    # 1. 정상 케이스
    valid_data = {
        "symbol": "AAPL",
        "price": 200.5,
        "change": 1.2,
        "volume": 1000,
        "timestamp": datetime.now().isoformat()
    }
    obj = MarketData(**valid_data)
    assert obj.symbol == "AAPL"
    assert obj.type == MessageType.TICKER

    # 2. 타입 불일치 (자동 형변환 확인)
    mixed_data = valid_data.copy()
    mixed_data["price"] = "200.5" # 문자열 숫자
    obj2 = MarketData(**mixed_data)
    assert isinstance(obj2.price, float)

    # 3. 필수 필드 누락 (ValidationError 발생 여부)
    from pydantic import ValidationError
    invalid_data = {"symbol": "TSLA"} # price, volume 등 누락
    with pytest.raises(ValidationError):
        MarketData(**invalid_data)

    # 4. 값 제약 조건 (Tier 2: Price > 0, Volume >= 0)
    negative_price = valid_data.copy()
    negative_price["price"] = -100
    with pytest.raises(ValidationError):
        MarketData(**negative_price)
        
    negative_vol = valid_data.copy()
    negative_vol["volume"] = -1
    with pytest.raises(ValidationError):
        MarketData(**negative_vol)

def test_news_alert_schema_integrity():
    """뉴스 알람 스키마 정합성 검증"""
    from src.core.schema import NewsAlert
    
    valid_news = {
        "headline": "Test News",
        "url": "http://test.com",
        "source": "Google",
        "keywords": ["test", "ai"],
        "timestamp": datetime.now().isoformat()
    }
    obj = NewsAlert(**valid_news)
    assert obj.type == MessageType.ALERT
    assert len(obj.keywords) == 2
