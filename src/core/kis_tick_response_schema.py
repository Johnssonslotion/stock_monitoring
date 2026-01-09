"""
KIS WebSocket Response Schema - 실시간 체결가
TR_ID: H0STCNT0 (실시간 체결가)
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
    """실시간 체결가 응답 Body (45개 필드)"""
    
    # 기본 정보
    MKSC_SHRN_ISCD: str         # 유가증권 단축 종목코드
    STCK_CNTG_HOUR: str         # 주식 체결 시간
    
    # 가격 정보
    STCK_PRPR: float            # 주식 현재가
    PRDY_VRSS_SIGN: str         # 전일 대비 부호
    PRDY_VRSS: float            # 전일 대비
    PRDY_CTRT: float            # 전일 대비율
    WGHN_AVRG_STCK_PRC: float   # 가중 평균 주식 가격
    
    # OHLC
    STCK_OPRC: float            # 주식 시가
    STCK_HGPR: float            # 주식 최고가
    STCK_LWPR: float            # 주식 최저가
    
    # 호가
    ASKP1: float                # 매도호가1
    BIDP1: float                # 매수호가1
    
    # 거래량
    CNTG_VOL: float             # 체결 거래량
    ACML_VOL: float             # 누적 거래량
    ACML_TR_PBMN: float         # 누적 거래 대금
    
    # 체결 정보
    SELN_CNTG_CSNU: float       # 매도 체결 건수
    SHNU_CNTG_CSNU: float       # 매수 체결 건수
    NTBY_CNTG_CSNU: float       # 순매수 체결 건수
    CTTR: float                 # 체결강도
    SELN_CNTG_SMTN: float       # 총 매도 수량
    SHNU_CNTG_SMTN: float       # 총 매수 수량
    CCLD_DVSN: str              # 체결구분
    SHNU_RATE: float            # 매수비율
    PRDY_VOL_VRSS_ACML_VOL_RATE: float  # 전일 거래량 대비 등락율
    
    # 시가 대비
    OPRC_HOUR: str              # 시가 시간
    OPRC_VRSS_PRPR_SIGN: str    # 시가대비구분
    OPRC_VRSS_PRPR: float       # 시가대비
    
    # 고가 대비
    HGPR_HOUR: str              # 최고가 시간
    HGPR_VRSS_PRPR_SIGN: str    # 고가대비구분
    HGPR_VRSS_PRPR: float       # 고가대비
    
    # 저가 대비
    LWPR_HOUR: str              # 최저가 시간
    LWPR_VRSS_PRPR_SIGN: str    # 저가대비구분
    LWPR_VRSS_PRPR: float       # 저가대비
    
    # 기타
    BSOP_DATE: str              # 영업 일자
    NEW_MKOP_CLS_CODE: str      # 신 장운영 구분 코드
    TRHT_YN: str                # 거래정지 여부
    
    # 호가 잔량
    ASKP_RSQN1: float           # 매도호가 잔량1
    BIDP_RSQN1: float           # 매수호가 잔량1
    TOTAL_ASKP_RSQN: float      # 총 매도호가 잔량
    TOTAL_BIDP_RSQN: float      # 총 매수호가 잔량
    
    # 거래량 회전율
    VOL_TNRT: float             # 거래량 회전율
    PRDY_SMNS_HOUR_ACML_VOL: float       # 전일 동시간 누적 거래량
    PRDY_SMNS_HOUR_ACML_VOL_RATE: float  # 전일 동시간 누적 거래량 비율
    
    # 시간/구분 코드
    HOUR_CLS_CODE: str          # 시간 구분 코드
    MRKT_TRTM_CLS_CODE: str     # 임의종료구분코드
    VI_STND_PRC: float          # 정적VI발동기준가
