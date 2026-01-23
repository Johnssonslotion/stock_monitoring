"""
HUB-MDL-01: CandleModel Pydantic 검증
HUB-MDL-02: TickModel 직렬화/역직렬화
HUB-GT-01: source_type Ground Truth 검증
"""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestCandleModel:
    """HUB-MDL-01: CandleModel Pydantic 검증"""

    def test_candle_model_valid(self):
        """유효한 CandleModel 생성"""
        from src.api_gateway.hub.models import CandleModel

        candle = CandleModel(
            time=datetime.now(timezone.utc),
            symbol="005930",
            open=70000.0,
            high=71000.0,
            low=69500.0,
            close=70500.0,
            volume=1000000,
            source_type="REST_API_KIS"
        )

        assert candle.symbol == "005930"
        assert candle.source_type == "REST_API_KIS"

    def test_candle_model_invalid_source_type(self):
        """잘못된 source_type은 ValidationError 발생"""
        from src.api_gateway.hub.models import CandleModel

        with pytest.raises(ValidationError):
            CandleModel(
                time=datetime.now(timezone.utc),
                symbol="005930",
                open=70000.0,
                high=71000.0,
                low=69500.0,
                close=70500.0,
                volume=1000000,
                source_type="INVALID_SOURCE"  # 잘못된 값
            )

    def test_candle_model_serialization(self):
        """JSON 직렬화/역직렬화"""
        from src.api_gateway.hub.models import CandleModel

        candle = CandleModel(
            time=datetime.now(timezone.utc),
            symbol="005930",
            open=70000.0,
            high=71000.0,
            low=69500.0,
            close=70500.0,
            volume=1000000,
            source_type="REST_API_KIS"
        )

        json_str = candle.model_dump_json()
        restored = CandleModel.model_validate_json(json_str)

        assert restored.symbol == candle.symbol
        assert restored.close == candle.close


class TestTickModel:
    """HUB-MDL-02: TickModel 직렬화/역직렬화"""

    def test_tick_model_valid(self):
        """유효한 TickModel 생성"""
        from src.api_gateway.hub.models import TickModel

        tick = TickModel(
            time=datetime.now(timezone.utc),
            symbol="005930",
            price=70500.0,
            volume=100,
            change=0.5,
            source="KIS",
            execution_no="20260123100000001"
        )

        assert tick.symbol == "005930"
        assert tick.execution_no == "20260123100000001"

    def test_tick_model_serialization(self):
        """JSON 직렬화/역직렬화"""
        from src.api_gateway.hub.models import TickModel

        tick = TickModel(
            time=datetime.now(timezone.utc),
            symbol="005930",
            price=70500.0,
            volume=100,
            change=0.5,
            source="KIS",
            execution_no="20260123100000001"
        )

        json_str = tick.model_dump_json()
        restored = TickModel.model_validate_json(json_str)

        assert restored.execution_no == tick.execution_no


class TestGroundTruth:
    """HUB-GT-01: source_type Ground Truth 검증"""

    def test_valid_source_types(self):
        """허용된 source_type 값들"""
        from src.api_gateway.hub.models import CandleModel, VALID_SOURCE_TYPES

        for source_type in VALID_SOURCE_TYPES:
            candle = CandleModel(
                time=datetime.now(timezone.utc),
                symbol="005930",
                open=70000.0,
                high=71000.0,
                low=69500.0,
                close=70500.0,
                volume=1000000,
                source_type=source_type
            )
            assert candle.source_type == source_type

    def test_source_type_enum_values(self):
        """Ground Truth Policy에 정의된 source_type 목록 확인"""
        from src.api_gateway.hub.models import VALID_SOURCE_TYPES

        expected = {
            "REST_API_KIS",
            "REST_API_KIWOOM",
            "WEBSOCKET_KIS",
            "WEBSOCKET_KIWOOM",
            "TICK_AGGREGATION",
            "IMPUTED"
        }

        assert expected.issubset(set(VALID_SOURCE_TYPES))
