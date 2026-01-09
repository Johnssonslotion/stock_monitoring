"""
KIS WebSocket 실시간 호가 스키마 (TR_ID: H0STASP0 / H0STOAA0)
- H0STASP0: 정규장 실시간 호가
- H0STOAA0: 시간외 실시간 호가
"""
from dataclasses import dataclass


@dataclass
class OrderbookRequestHeader:
    """WebSocket 구독 요청 헤더"""
    approval_key: str    # 웹소켓 접속키
    custtype: str        # 고객 타입 (P=개인)
    tr_type: str         # 거래 타입 (1=구독, 2=해제)
    content_type: str    # 컨텐츠 타입


@dataclass
class OrderbookRequestBody:
    """WebSocket 구독 요청 바디"""
    tr_id: str    # 거래 ID (H0STASP0 or H0STOAA0)
    tr_key: str   # 구분값 (종목코드)


@dataclass
class OrderbookResponseBody:
    """
    실시간 호가 응답 Body (54개 필드, 9레벨 호가)
    
    정규장(H0STASP0)과 시간외(H0STOAA0) 동일한 스키마 사용
    
    Field Index 맵핑:
        Index 0: MKSC_SHRN_ISCD (종목코드)
        Index 1-2: 시간 정보
        Index 3-11: ASKP1~9 (매도호가 1-9)
        Index 12-20: BIDP1~9 (매수호가 1-9)
        Index 21-29: ASKP_RSQN1~9 (매도잔량 1-9)
        Index 30-38: BIDP_RSQN1~9 (매수잔량 1-9)
        Index 39-53: 집계 및 예상 체결 정보
    """
    
    # 기본 정보
    MKSC_SHRN_ISCD: str         # [0] 유가증권 단축 종목코드
    BSOP_HOUR: str              # [1] 영업시간
    HOUR_CLS_CODE: str          # [2] 시간구분코드
    
    # 매도호가 1-9 (9레벨)
    ASKP1: str                  # [3] 매도호가1
    ASKP2: str                  # [4] 매도호가2
    ASKP3: str                  # [5] 매도호가3
    ASKP4: str                  # [6] 매도호가4
    ASKP5: str                  # [7] 매도호가5
    ASKP6: str                  # [8] 매도호가6
    ASKP7: str                  # [9] 매도호가7
    ASKP8: str                  # [10] 매도호가8
    ASKP9: str                  # [11] 매도호가9
    
    # 매수호가 1-9 (9레벨)
    BIDP1: str                  # [12] 매수호가1
    BIDP2: str                  # [13] 매수호가2
    BIDP3: str                  # [14] 매수호가3
    BIDP4: str                  # [15] 매수호가4
    BIDP5: str                  # [16] 매수호가5
    BIDP6: str                  # [17] 매수호가6
    BIDP7: str                  # [18] 매수호가7
    BIDP8: str                  # [19] 매수호가8
    BIDP9: str                  # [20] 매수호가9
    
    # 매도호가 잔량 1-9 (9레벨)
    ASKP_RSQN1: str             # [21] 매도호가잔량1
    ASKP_RSQN2: str             # [22] 매도호가잔량2
    ASKP_RSQN3: str             # [23] 매도호가잔량3
    ASKP_RSQN4: str             # [24] 매도호가잔량4
    ASKP_RSQN5: str             # [25] 매도호가잔량5
    ASKP_RSQN6: str             # [26] 매도호가잔량6
    ASKP_RSQN7: str             # [27] 매도호가잔량7
    ASKP_RSQN8: str             # [28] 매도호가잔량8
    ASKP_RSQN9: str             # [29] 매도호가잔량9
    
    # 매수호가 잔량 1-9 (9레벨)
    BIDP_RSQN1: str             # [30] 매수호가잔량1
    BIDP_RSQN2: str             # [31] 매수호가잔량2
    BIDP_RSQN3: str             # [32] 매수호가잔량3
    BIDP_RSQN4: str             # [33] 매수호가잔량4
    BIDP_RSQN5: str             # [34] 매수호가잔량5
    BIDP_RSQN6: str             # [35] 매수호가잔량6
    BIDP_RSQN7: str             # [36] 매수호가잔량7
    BIDP_RSQN8: str             # [37] 매수호가잔량8
    BIDP_RSQN9: str             # [38] 매수호가잔량9
    
    # 집계 정보
    TOTAL_ASKP_RSQN: str        # [39] 총매도호가잔량
    TOTAL_BIDP_RSQN: str        # [40] 총매수호가잔량
    OVTM_TOTAL_ASKP_RSQN: str   # [41] 시간외총매도호가잔량
    OVTM_TOTAL_BIDP_RSQN: str   # [42] 시간외총매수호가잔량
    
    # 예상 체결 정보
    ANTC_CNPR: str              # [43] 예상체결가
    ANTC_CNQN: str              # [44] 예상체결량
    ANTC_VOL: str               # [45] 예상거래량
    ANTC_CNTG_VRSS: str         # [46] 예상체결대비
    ANTC_CNTG_VRSS_SIGN: str    # [47] 예상체결대비부호
    ANTC_CNTG_PRDY_CTRT: str    # [48] 예상체결전일대비율
    
    # 기타
    ACML_VOL: str               # [49] 누적거래량
    TOTAL_ASKP_RSQN_ICDC: str   # [50] 총매도호가잔량증감
    TOTAL_BIDP_RSQN_ICDC: str   # [51] 총매수호가잔량증감
    OVTM_TOTAL_ASKP_ICDC: str   # [52] 시간외총매도호가증감
    OVTM_TOTAL_BIDP_ICDC: str   # [53] 시간외총매수호가증감
