from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

# = :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# Mirae Asset API Schema Definition (v2.2)
# = :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class MiraeAuthRequest(BaseModel):
    """Access Token 발급 요청 스키마"""
    grant_type: str = "client_credentials"
    appkey: str = Field(..., description="미래에셋 발급 AppKey")
    appsecret: str = Field(..., description="미래에셋 발급 AppSecret")

class MiraeAuthResponse(BaseModel):
    """Access Token 발급 응답 스키마"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    issued_at: datetime = Field(default_factory=datetime.now)

class MiraeSubRequest(BaseModel):
    """실시간 시세 구독 요청 (WebSocket)"""
    tr_type: str = Field(..., pattern="^[12]$") # 1: 구독, 2: 해제
    tr_cd: str = Field(..., description="거래코드 (현금체결: H0STCNT0 등)")
    tr_key: str = Field(..., description="종목코드 (예: 005930)")

class MiraePriceData(BaseModel):
    """실시간 체결가 데이터 (JSON 형태 가정)"""
    stck_cntg_hour: str = Field(..., description="주식 체결 시간")
    stck_prpr: float = Field(..., description="주식 현재가")
    prdy_vrss: float = Field(..., description="전일 대비")
    prdy_ctrt: float = Field(..., description="전일 대비율")
    acml_vol: float = Field(..., description="누적 거래량")
    cntg_vol: float = Field(..., description="체결 거래량")

class MiraeWSResponse(BaseModel):
    """WebSocket 수신 데이터 최상위 스키마"""
    tr_cd: str
    tr_key: str
    rt_cd: str = "0"
    data: Optional[MiraePriceData] = None

# = :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# [DEBUG] Actual Values (Sample Data for Verification)
# Source: Mirae Asset Developer Portal Documentation
# = :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
ACTUAL_SAMPLE_WS_DATA = {
    "tr_cd": "H0STCNT0",
    "tr_key": "005930",
    "rt_cd": "0",
    "data": {
        "stck_cntg_hour": "153000",
        "stck_prpr": 73200,
        "prdy_vrss": -500,
        "prdy_ctrt": -0.68,
        "acml_vol": 12500000,
        "cntg_vol": 1500
    }
}
