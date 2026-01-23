"""
API Hub 데이터 모델 (Pydantic)

Ground Truth Policy 준수:
- source_type 필드로 데이터 출처 명시
- REST_API_KIS, REST_API_KIWOOM 등 허용된 값만 사용
"""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, field_validator

# Ground Truth Policy에 정의된 유효한 source_type 값
VALID_SOURCE_TYPES = [
    "REST_API_KIS",
    "REST_API_KIWOOM",
    "WEBSOCKET_KIS",
    "WEBSOCKET_KIWOOM",
    "TICK_AGGREGATION",
    "IMPUTED",
]

SourceType = Literal[
    "REST_API_KIS",
    "REST_API_KIWOOM",
    "WEBSOCKET_KIS",
    "WEBSOCKET_KIWOOM",
    "TICK_AGGREGATION",
    "IMPUTED",
]


class CandleModel(BaseModel):
    """
    분봉 데이터 모델

    Schema Triple-Lock:
    - API Spec: docs/specs/api_hub_specification.md
    - Python Model: 이 파일
    - DB Migration: migrations/006_add_source_type_to_candles.sql
    """
    time: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    source_type: SourceType

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        """source_type이 Ground Truth Policy에 정의된 값인지 검증"""
        if v not in VALID_SOURCE_TYPES:
            raise ValueError(
                f"Invalid source_type: {v}. "
                f"Must be one of: {VALID_SOURCE_TYPES}"
            )
        return v

    model_config = ConfigDict(ser_json_timedelta="iso8601")


class TickModel(BaseModel):
    """
    틱 데이터 모델

    execution_no: 체결 고유 식별자 (중복 방지용)
    """
    time: datetime
    symbol: str
    price: float
    volume: int
    change: float
    source: str
    execution_no: str

    model_config = ConfigDict(ser_json_timedelta="iso8601")


class TaskRequest(BaseModel):
    """
    API Hub 태스크 요청 모델

    Queue Protocol에 정의된 스키마
    """
    task_id: str
    priority: Literal["HIGH", "NORMAL"] = "NORMAL"
    provider: Literal["KIS", "KIWOOM"]
    tr_id: str
    params: dict = {}
    timestamp: datetime
    callback_key: str | None = None

    model_config = ConfigDict(ser_json_timedelta="iso8601")
