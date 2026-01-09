"""
KIS WebSocket 실시간 체결가 스키마 (TR_ID: H0STCNT0 / H0STOUP0)
- H0STCNT0: 정규장 실시간 체결가
- H0STOUP0: 시간외 실시간 체결가
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class TickRequestHeader:
    """WebSocket 구독 요청 헤더"""
    approval_key: str    # 웹소켓 접속키
    custtype: str        # 고객 타입 (P=개인)
    tr_type: str         # 거래 타입 (1=구독, 2=해제)
    content_type: str    # 컨텐츠 타입 (주의: 'content-type'이 아님)


@dataclass
class TickRequestBody:
    """WebSocket 구독 요청 바디"""
    tr_id: str    # 거래 ID (H0STCNT0 or H0STOUP0)
    tr_key: str   # 구분값 (종목코드, 예: 005930)


@dataclass
class TickResponseBody:
    """
    실시간 체결가 응답 Body (43개 필드)
    
    정규장(H0STCNT0)과 시간외(H0STOUP0) 동일한 스키마 사용
    """
    
    # 기본 정보
    MKSC_SHRN_ISCD: str         # 유가증권 단축 종목코드
    STCK_CNTG_HOUR: str         # 주식 체결 시간
    
    # 가격 정보
    STCK_PRPR: str              # 주식 현재가
    PRDY_VRSS_SIGN: str         # 전일 대비 부호
    PRDY_VRSS: str              # 전일 대비
    PRDY_CTRT: str              # 등락율
    WGHN_AVRG_STCK_PRC: str     # 가중 평균 주식 가격
    
    # OHLC
    STCK_OPRC: str              # 시가
    STCK_HGPR: str              # 고가
    STCK_LWPR: str              # 저가
    
    # 호가
    ASKP1: str                  # 매도호가1
    BIDP1: str                  # 매수호가1
    
    # 거래량
    CNTG_VOL: str               # 체결 거래량
    ACML_VOL: str               # 누적 거래량
    ACML_TR_PBMN: str           # 누적 거래 대금
    
    # 체결 정보
    SELN_CNTG_CSNU: str         # 매도 체결 건수
    SHNU_CNTG_CSNU: str         # 매수 체결 건수
    NTBY_CNTG_CSNU: str         # 순매수 체결 건수
    CTTR: str                   # 체결강도
    SELN_CNTG_SMTN: str         # 총 매도 수량
    SHNU_CNTG_SMTN: str         # 총 매수 수량
    CNTG_CLS_CODE: str          # 체결 구분
    SHNU_RATE: str              # 매수 비율
    PRDY_VOL_VRSS_ACML_VOL_RATE: str  # 전일 거래량 대비 등락율
    
    # 시가 대비
    OPRC_HOUR: str              # 시가 시간
    OPRC_VRSS_PRPR_SIGN: str    # 시가 대비 구분
    OPRC_VRSS_PRPR: str         # 시가 대비
    
    # 고가 대비
    HGPR_HOUR: str              # 최고가 시간
    HGPR_VRSS_PRPR_SIGN: str    # 고가 대비 구분
    HGPR_VRSS_PRPR: str         # 고가 대비
    
    # 저가 대비
    LWPR_HOUR: str              # 최저가 시간
    LWPR_VRSS_PRPR_SIGN: str    # 저가 대비 구분
    LWPR_VRSS_PRPR: str         # 저가 대비
    
    # 기타
    BSOP_DATE: str              # 영업 일자
    NEW_MKOP_CLS_CODE: str      # 신 장운영 구분 코드
    TRHT_YN: str                # 거래정지 여부
    
    # 호가 잔량
    ASKP_RSQN1: str             # 매도호가 잔량1
    BIDP_RSQN1: str             # 매수호가 잔량1
    TOTAL_ASKP_RSQN: str        # 총 매도호가 잔량
    TOTAL_BIDP_RSQN: str        # 총 매수호가 잔량
    
    # 거래량 회전율
    VOL_TNRT: str               # 거래량 회전율
    PRDY_SMNS_HOUR_ACML_VOL: str       # 전일 동시간 누적 거래량
    PRDY_SMNS_HOUR_ACML_VOL_RATE: str  # 전일 동시간 누적 거래량 비율
