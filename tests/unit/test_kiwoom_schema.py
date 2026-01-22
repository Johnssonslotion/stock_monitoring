import pytest
from datetime import datetime
from src.data_ingestion.price.schemas.kiwoom_re import KiwoomTickData

class TestKiwoomSchema:
    def test_tick_data_parsing(self):
        """Kiwoom WebSocket JSON 포맷 파싱 테스트"""
        # Given: 가상의 Kiwoom WS 응답 (주식체결)
        sample_json = {
            "MKSC_SHRN_ISCD": "005930",  # 삼성전자
            "STCK_PRPR": "-70000",       # 현재가 (하락)
            "ACML_VOL": "1000000",       # 누적거래량
            "PRDY_VRSS": "-500",         # 전일대비
            "STCK_CNTG_HOUR": "103000",  # 10:30:00
            "STCK_OPRC": "70500",        # 시가
            "STCK_HGPR": "71000",        # 고가
            "STCK_LWPR": "69500"         # 저가
        }
        
        # When
        tick = KiwoomTickData.from_ws_json(sample_json, "005930")
        
        # Then
        assert tick.symbol == "005930"
        assert tick.price == 70000.0  # 절대값 변환 확인
        assert tick.change == -500.0
        assert tick.volume == 1000000.0
        assert tick.timestamp.hour == 10
        assert tick.timestamp.minute == 30
        assert tick.timestamp.second == 0
        
        # Metadata 검증 (v2.15)
        assert tick.broker == "KIWOOM"
        assert tick.received_time is not None
        assert isinstance(tick.received_time, datetime)
        assert tick.broker_time == tick.timestamp
        
    def test_invalid_price(self):
        """잘못된 데이터 처리 테스트"""
        invalid_json = {
            "STCK_PRPR": "invalid_price"
        }
        
        with pytest.raises(ValueError):
            KiwoomTickData.from_ws_json(invalid_json, "005930")
