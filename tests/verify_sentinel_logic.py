
import pytest
from datetime import datetime, time
import pytz
from src.monitoring.sentinel import Sentinel

@pytest.fixture
def sentinel():
    return Sentinel()

def test_market_hours_kr(sentinel):
    tz = pytz.timezone('Asia/Seoul')
    
    # 08:29 (Closed)
    t1 = datetime(2026, 1, 14, 8, 29, tzinfo=tz)
    assert sentinel.is_market_open("KR", _mock_time=t1) == False
    
    # 08:31 (Open)
    t2 = datetime(2026, 1, 14, 8, 31, tzinfo=tz)
    assert sentinel.is_market_open("KR", _mock_time=t2) == True
    
    # 15:59 (Open)
    t3 = datetime(2026, 1, 14, 15, 59, tzinfo=tz)
    assert sentinel.is_market_open("KR", _mock_time=t3) == True
    
    # 16:01 (Closed)
    t4 = datetime(2026, 1, 14, 16, 1, tzinfo=tz)
    assert sentinel.is_market_open("KR", _mock_time=t4) == False

def test_market_hours_us(sentinel):
    tz = pytz.timezone('Asia/Seoul')
    
    # 16:59 KST (Closed)
    t1 = datetime(2026, 1, 14, 16, 59, tzinfo=tz)
    assert sentinel.is_market_open("US", _mock_time=t1) == False
    
    # 17:01 KST (Open)
    t2 = datetime(2026, 1, 14, 17, 1, tzinfo=tz)
    assert sentinel.is_market_open("US", _mock_time=t2) == True
    
    # 02:00 KST (Open - Next Day)
    t3 = datetime(2026, 1, 15, 2, 0, tzinfo=tz)
    assert sentinel.is_market_open("US", _mock_time=t3) == True
    
    # 08:01 KST (Closed)
    t4 = datetime(2026, 1, 15, 8, 1, tzinfo=tz)
    assert sentinel.is_market_open("US", _mock_time=t4) == False
