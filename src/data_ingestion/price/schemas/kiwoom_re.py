from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class KiwoomTickData(BaseModel):
    """
    Kiwoom WebSocket 실시간 체결 데이터 (주식체결)
    - TR: 주식체결
    - 화면번호: 가상번호
    """
    symbol: str = Field(..., description="종목코드 (MKSC_SHRN_ISCD)")
    price: float = Field(..., description="현재가 (STCK_PRPR)")
    volume: float = Field(..., description="누적거래량 (ACML_VOL)")
    change: float = Field(..., description="전일대비 (PRDY_VRSS)")
    timestamp: datetime = Field(..., description="체결시간")
    
    # 2차 정보
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    
    @classmethod
    def from_ws_json(cls, data: Dict[str, Any], symbol: str) -> "KiwoomTickData":
        """
        Kiwoom WebSocket JSON 응답을 내부 모델로 변환
        
        Args:
            data (dict): WebSocket 수신 데이터 (Raw)
            symbol (str): 종목코드
            
        Returns:
            KiwoomTickData
        """
        try:
            # 시간 파싱 (HHMMSS -> datetime)
            time_str = data.get("STCK_CNTG_HOUR", "")  # 체결시간
            now = datetime.now()
            
            if len(time_str) == 6:
                dt = now.replace(
                    hour=int(time_str[:2]),
                    minute=int(time_str[2:4]),
                    second=int(time_str[4:]),
                    microsecond=0
                )
            else:
                dt = now

            # 가격정보 처리 (부호 제거)
            curr_price = abs(float(data.get("STCK_PRPR", 0)))
            
            return cls(
                symbol=symbol,
                price=curr_price,
                volume=float(data.get("ACML_VOL", 0)),
                change=float(data.get("PRDY_VRSS", 0)),
                timestamp=dt,
                open_price=abs(float(data.get("STCK_OPRC", 0))),
                high_price=abs(float(data.get("STCK_HGPR", 0))),
                low_price=abs(float(data.get("STCK_LWPR", 0)))
            )
        except Exception as e:
            raise ValueError(f"Kiwoom Schema Parsing Error: {e}")

class KiwoomOrderbookData(BaseModel):
    """Kiwoom 호가 데이터 (주식호가잔량)"""
    symbol: str
    timestamp: datetime
    
    ask_prices: list[float]
    bid_prices: list[float]
    ask_volumes: list[float]
    bid_volumes: list[float]
    
    total_ask_volume: float
    total_bid_volume: float
