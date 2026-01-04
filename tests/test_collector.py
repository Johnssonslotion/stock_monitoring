import pytest
import json
from src.data_ingestion.ticks.collector import TickCollector

# Sample Upbit Data
UPBIT_TRADE_SAMPLE = {
    "type": "trade",
    "code": "KRW-BTC",
    "opening_price": 50000000,
    "high_price": 51000000,
    "low_price": 49000000,
    "trade_price": 50500000.0,
    "prev_closing_price": 50000000,
    "change": "RISE",
    "change_price": 500000,
    "sign_change_price": 500000,
    "change_rate": 0.01,
    "sign_change_rate": 0.01,
    "trade_volume": 0.015,
    "accum_trade_volume": 100.5,
    "trade_date": "20240104",
    "trade_time": "120000",
    "trade_timestamp": 1704337200000,
    "ask_bid": "BID",
    "sequential_id": 1234567890
}

def test_normalize_upbit():
    """Upbit 원본 데이터가 표준 포맷으로 잘 변환되는지 테스트"""
    collector = TickCollector()
    
    normalized = collector.normalize(UPBIT_TRADE_SAMPLE)
    
    assert normalized is not None
    assert normalized["source"] == "upbit"
    assert normalized["symbol"] == "KRW-BTC"
    assert normalized["price"] == 50500000.0
    assert normalized["volume"] == 0.015
    assert normalized["side"] == "bid"
    assert normalized["timestamp"] == 1704337200000
    assert "id" in normalized

def test_normalize_invalid_data():
    """필수 필드가 누락된 데이터는 None을 반환해야 함"""
    collector = TickCollector()
    invalid_data = {"type": "trade", "code": "KRW-BTC"} # trade_price missing
    
    normalized = collector.normalize(invalid_data)
    
    assert normalized is None

def test_normalize_negative_price():
    """(Chaos) 음수 가격 데이터 처리 테스트 - 현재 로직은 음수 허용, 추후 필터링 로직 추가 여부 결정"""
    collector = TickCollector()
    chaos_data = UPBIT_TRADE_SAMPLE.copy()
    chaos_data["trade_price"] = -50000000.0
    
    normalized = collector.normalize(chaos_data)
    
    # 현재 정책: 수집기는 있는 그대로 수집하고, 분석기에서 필터링하거나
    # 수집기에서부터 자를지 결정해야 함.
    # 대전략상 'Garbage In Garbage Out' 방지를 위해 여기서 자르는게 맞는지?
    # 일단 수집은 하되, 로그를 남기는 방향으로 갈 수 있음.
    # 현재 구현상으로는 음수도 통과됨. (Feature or Bug?)
    assert normalized["price"] == -50000000.0 
