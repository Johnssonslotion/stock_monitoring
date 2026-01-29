from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

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
    
    # [ISSUE-036 Alignment] Metadata Fields
    broker: str = Field("KIWOOM", description="브로커 식별자")
    broker_time: Optional[datetime] = Field(None, description="브로커 제공 체결시간")
    received_time: datetime = Field(default_factory=datetime.now, description="시스템 수신 시간")
    sequence_number: Optional[int] = Field(None, description="브로커 제공 시퀀스 번호")
    
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
            # 1. 핀 꼽기: 모든 타임스탬프의 기준이 되는 수신 시간 고정
            now = datetime.now()
            
            # 2. 시간 파싱 (HHMMSS -> datetime)
            time_str = data.get("20") or data.get("STCK_CNTG_HOUR", "")  # 20: 체결시간
            
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
            price_raw = data.get("10") or data.get("STCK_PRPR", 0)
            curr_price = abs(float(price_raw))
            
            vol_raw = data.get("13") or data.get("ACML_VOL", 0)
            change_raw = data.get("11") or data.get("PRDY_VRSS", 0)
            
            # 시퀀스 번호 (FID 8? 키움은 틱별 유니크 ID가 명확하지 않으나 전달된 값이 있으면 사용)
            # 여기서는 예시로 90011(체결번호) 등이 있으면 사용 가능하나, 일단 None으로 유지하거나 dummy
            seq = int(data.get("9001", 0)) if data.get("9001") else None

            return cls(
                symbol=symbol,
                price=curr_price,
                volume=float(vol_raw),
                change=float(change_raw),
                timestamp=dt,
                broker="KIWOOM",
                broker_time=dt,
                received_time=now,
                sequence_number=seq,
                open_price=abs(float(data.get("16", 0))), # 16: 시가
                high_price=abs(float(data.get("17", 0))), # 17: 고가
                low_price=abs(float(data.get("18", 0)))   # 18: 저가
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

    @classmethod
    def from_ws_json(cls, data: Dict[str, Any], symbol: str) -> "KiwoomOrderbookData":
        """
        FID Mapping for Orderbook (Type 0D)
        Asks: 27(1)..36(10) Prices, 61(1)..70(10) Vols
        Bids: 17(1)..26(10) Prices, 71(1)..80(10) Vols
        Totals: 121 (Ask), 125 (Bid)
        """
        try:
            now = datetime.now() # Orderbook usually doesn't have explicit time FID, use current
            
            # Helper to get list
            def get_list(start_fid, count):
                res = []
                for i in range(count):
                    fid = str(start_fid + i)
                    val = data.get(fid, 0)
                    res.append(abs(float(val)))
                return res

            # Caution: Keys are strings
            asks_prc = get_list(27, 10)
            asks_vol = get_list(61, 10)
            bids_prc = get_list(17, 10)
            bids_vol = get_list(71, 10)
            
            total_ask = float(data.get("121", 0))
            total_bid = float(data.get("125", 0))

            return cls(
                symbol=symbol,
                timestamp=now,
                ask_prices=asks_prc,
                ask_volumes=asks_vol,
                bid_prices=bids_prc,
                bid_volumes=bids_vol,
                total_ask_volume=total_ask,
                total_bid_volume=total_bid
            )
        except Exception as e:
             logger.error(f"Orderbook Parse Error: {e}")
             raise ValueError(f"Orderbook Parse Error: {e}")
