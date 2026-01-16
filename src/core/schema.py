from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class MessageType(str, Enum):
    TICKER = "ticker"
    ORDERBOOK = "orderbook"
    ALERT = "alert"
    SYSTEM = "system"

class BaseMessage(BaseModel):
    """시스템 내 모든 메시지의 기본이 되는 스키마"""
    type: MessageType
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(use_enum_values=True)

class OrderbookUnit(BaseModel):
    price: float = Field(..., gt=0)
    vol: float = Field(..., ge=0)

class OrderbookData(BaseMessage):
    """실시간 호가(Orderbook) 데이터 스키마"""
    type: MessageType = MessageType.ORDERBOOK
    symbol: str = Field(..., min_length=1)
    source: str = "KIS"  # Origin (KIS or KIWOOM)
    asks: list[OrderbookUnit]
    bids: list[OrderbookUnit]

class MarketData(BaseMessage):
    """실시간 체결가(Ticker) 데이터 스케마"""
    type: MessageType = MessageType.TICKER
    symbol: str = Field(..., min_length=1)
    source: str = "KIS"  # Origin (KIS or KIWOOM)
    price: float = Field(..., gt=0)
    change: float  # 전일 대비 등락률 (%)
    volume: float = Field(..., ge=0)

class NewsAlert(BaseMessage):
    """뉴스 분석 및 알림 스키마"""
    type: MessageType = MessageType.ALERT
    symbol: Optional[str] = None
    headline: str
    url: str
    source: str
    keywords: list[str]

class SystemStatus(BaseMessage):
    type: MessageType = MessageType.SYSTEM
    status: str
    connected_clients: int
