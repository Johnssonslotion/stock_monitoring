from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# = :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# Kiwoom Open API RE Schema Definition (v2.2)
# = :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class KiwoomLoginResponse(BaseModel):
    """로그인 결과 스키마"""
    ret_code: int = Field(..., description="0: 성공, 음수: 실패")
    msg: str

class KiwoomSubRequest(BaseModel):
    """실시간 시세 구독 요청 (REST/WS 공통)"""
    scr_no: str = Field(..., description="화면번호 (4자리)")
    symbols: List[str] = Field(..., description="종목코드 리스트")
    fid_list: List[str] = Field(..., description="요청 FID 리스트 (예: 10, 11, 15)")
    opt_type: str = "0" # 0: 신규, 1: 추가

class KiwoomRealData(BaseModel):
    """실시간 체결 데이터 (FID 기반)"""
    symbol: str
    price: float = Field(alias="10")
    change: float = Field(alias="11")
    volume: float = Field(alias="15")
    time: str = Field(alias="20")

class KiwoomMsg(BaseModel):
    """OnReceiveMsg 이벤트 포맷"""
    scr_no: str
    rq_name: str
    tr_code: str
    msg: str

# = :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# [DEBUG] Actual Values (Sample Data for Verification)
# Source: Kiwoom Open API RE REST API Manual
# = :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
ACTUAL_SAMPLE_TR_DATA = {
    "scr_no": "0101",
    "rq_name": "주식체결",
    "tr_code": "opt10001",
    "msg": "[0000] 정상 처리되었습니다.",
    "data": {
        "종목명": "삼성전자",
        "현재가": "73200",
        "전일대비": "500",
        "거래량": "12500000"
    }
}
