"""
KIS WebSocket Response Schema (H0STCNT0)
국내주식 실시간호가
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class ResponseHeader:
    tr_id: str           # 거래ID
    tr_key: str          # 구분값
    encrypt: str         # 암호화 여부

@dataclass
class ResponseBody:
    """국내주식 실시간호가 응답 Body"""
    
    # 기본 정보
    MKSC_SHRN_ISCD: str     # 유가증권 단축 종목코드
    BSOP_HOUR: str          # 영업 시간
    HOUR_CLS_CODE: str      # 시간 구분 코드
    
    # 매도호가 (Ask Price) 1-10
    ASKP1: float
    ASKP2: float
    ASKP3: float
    ASKP4: float
    ASKP5: float
    ASKP6: float
    ASKP7: float
    ASKP8: float
    ASKP9: float
    ASKP10: float
    
    # 매수호가 (Bid Price) 1-10
    BIDP1: float
    BIDP2: float
    BIDP3: float
    BIDP4: float
    BIDP5: float
    BIDP6: float
    BIDP7: float
    BIDP8: float
    BIDP9: float
    BIDP10: float
    
    # 매도호가 잔량 (Ask Quantity) 1-10
    ASKP_RSQN1: float
    ASKP_RSQN2: float
    ASKP_RSQN3: float
    ASKP_RSQN4: float
    ASKP_RSQN5: float
    ASKP_RSQN6: float
    ASKP_RSQN7: float
    ASKP_RSQN8: float
    ASKP_RSQN9: float
    ASKP_RSQN10: float
    
    # 매수호가 잔량 (Bid Quantity) 1-10
    BIDP_RSQN1: float
    BIDP_RSQN2: float
    BIDP_RSQN3: float
    BIDP_RSQN4: float
    BIDP_RSQN5: float
    BIDP_RSQN6: float
    BIDP_RSQN7: float
    BIDP_RSQN8: float
    BIDP_RSQN9: float
    BIDP_RSQN10: float
    
    # 호가 총량
    TOTAL_ASKP_RSQN: float       # 총 매도호가 잔량
    TOTAL_BIDP_RSQN: float       # 총 매수호가 잔량
    OVTM_TOTAL_ASKP_RSQN: float  # 시간외 총 매도호가 잔량
    OVTM_TOTAL_BIDP_RSQN: float  # 시간외 총 매수호가 잔량
    
    # 예상 체결
    ANTC_CNPR: float              # 예상 체결가
    ANTC_CNQN: float              # 예상 체결량
    ANTC_VOL: float               # 예상 거래량
    ANTC_CNTG_VRSS: float         # 예상 체결 대비
    ANTC_CNTG_VRSS_SIGN: str      # 예상 체결 대비 부호
    ANTC_CNTG_PRDY_CTRT: float    # 예상 체결 전일 대비율
    
    # 거래량 및 증감
    ACML_VOL: float                  # 누적 거래량
    TOTAL_ASKP_RSQN_ICDC: float      # 총 매도호가 잔량 증감
    TOTAL_BIDP_RSQN_ICDC: float      # 총 매수호가 잔량 증감
    OVTM_TOTAL_ASKP_ICDC: float      # 시간외 총 매도호가 증감
    OVTM_TOTAL_BIDP_ICDC: float      # 시간외 총 매수호가 증감
    STCK_DEAL_CLS_CODE: str          # 주식 매매 구분 코드

@dataclass
class WebSocketResponse:
    header: ResponseHeader
    body: ResponseBody
