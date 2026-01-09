"""
KIS WebSocket TR_ID 스키마 맵핑 (정규장 vs 시간외)

중요: 정규장과 시간외는 **동일한 스키마**를 사용합니다.
차이점은 TR_ID와 운영 시간뿐입니다.
"""

# ============================================================
# 체결가 (Tick Data) - 43개 필드
# ============================================================

# 정규장 실시간 체결가
TR_ID_TICK_REGULAR = "H0STCNT0"
TICK_REGULAR_HOURS = "09:00 ~ 15:30 KST"

# 시간외 실시간 체결가  
TR_ID_TICK_AFTERHOURS = "H0STOUP0"
TICK_AFTERHOURS_HOURS = "08:30~09:00, 15:40~18:00 KST"

# 스키마: kis_tick_schema.TickResponseBody (43 fields)
# - MKSC_SHRN_ISCD (종목코드)
# - STCK_CNTG_HOUR (체결시간)
# - STCK_PRPR (현재가)
# - PRDY_VRSS_SIGN (전일대비부호)
# - PRDY_VRSS (전일대비)
# - PRDY_CTRT (등락율)
# - ... (총 43개)


# ============================================================
# 호가 (Orderbook) - 54개 필드, 9레벨
# ============================================================

# 정규장 실시간 호가
TR_ID_ORDERBOOK_REGULAR = "H0STASP0"
ORDERBOOK_REGULAR_HOURS = "09:00 ~ 15:30 KST"

# 시간외 실시간 호가
TR_ID_ORDERBOOK_AFTERHOURS = "H0STOAA0"
ORDERBOOK_AFTERHOURS_HOURS = "08:30~09:00, 15:40~18:00 KST"

# 스키마: kis_orderbook_schema.OrderbookResponseBody (54 fields, 9 levels)
# - MKSC_SHRN_ISCD (종목코드)
# - BSOP_HOUR (영업시간)
# - HOUR_CLS_CODE (시간구분코드)
# - ASKP1~9 (매도호가 1-9) - Index 3~11
# - BIDP1~9 (매수호가 1-9) - Index 12~20
# - ASKP_RSQN1~9 (매도잔량 1-9) - Index 21~29
# - BIDP_RSQN1~9 (매수잔량 1-9) - Index 30~38
# - ... (총 54개)


# ============================================================
# Field Index 상세 (Body ^-separated)
# ============================================================

"""
체결가 Field Mapping (H0STCNT0 = H0STOUP0):
--------------------------------------------------
[0]  MKSC_SHRN_ISCD         종목코드
[1]  STCK_CNTG_HOUR         체결시간
[2]  STCK_PRPR              현재가
[3]  PRDY_VRSS_SIGN         전일대비구분
[4]  PRDY_VRSS              전일대비
[5]  PRDY_CTRT              등락율
[6]  WGHN_AVRG_STCK_PRC     가중평균가격
[7]  STCK_OPRC              시가
[8]  STCK_HGPR              고가
[9]  STCK_LWPR              저가
[10] ASKP1                  매도호가1
[11] BIDP1                  매수호가1
[12] CNTG_VOL               거래량
[13] ACML_VOL               누적거래량
[14] ACML_TR_PBMN           누적거래대금
[15] SELN_CNTG_CSNU         매도체결건수
[16] SHNU_CNTG_CSNU         매수체결건수
[17] NTBY_CNTG_CSNU         순매수체결건수
[18] CTTR                   체결강도
[19] SELN_CNTG_SMTN         총매도수량
[20] SHNU_CNTG_SMTN         총매수수량
[21] CNTG_CLS_CODE          체결구분
[22] SHNU_RATE              매수비율
[23] PRDY_VOL_VRSS_ACML_VOL_RATE  전일거래량대비등락율
[24] OPRC_HOUR              시가시간
[25] OPRC_VRSS_PRPR_SIGN    시가대비구분
[26] OPRC_VRSS_PRPR         시가대비
[27] HGPR_HOUR              최고가시간
[28] HGPR_VRSS_PRPR_SIGN    고가대비구분
[29] HGPR_VRSS_PRPR         고가대비
[30] LWPR_HOUR              최저가시간
[31] LWPR_VRSS_PRPR_SIGN    저가대비구분
[32] LWPR_VRSS_PRPR         저가대비
[33] BSOP_DATE              영업일자
[34] NEW_MKOP_CLS_CODE      신장운영구분코드
[35] TRHT_YN                거래정지여부
[36] ASKP_RSQN1             매도호가잔량1
[37] BIDP_RSQN1             매수호가잔량1
[38] TOTAL_ASKP_RSQN        총매도호가잔량
[39] TOTAL_BIDP_RSQN        총매수호가잔량
[40] VOL_TNRT               거래량회전율
[41] PRDY_SMNS_HOUR_ACML_VOL          전일동시간누적거래량
[42] PRDY_SMNS_HOUR_ACML_VOL_RATE     전일동시간누적거래량비율


호가 Field Mapping (H0STASP0 = H0STOAA0):
--------------------------------------------------
[0]  MKSC_SHRN_ISCD         종목코드
[1]  BSOP_HOUR              영업시간
[2]  HOUR_CLS_CODE          시간구분코드

[3]  ASKP1                  매도호가1
[4]  ASKP2                  매도호가2
[5]  ASKP3                  매도호가3
[6]  ASKP4                  매도호가4
[7]  ASKP5                  매도호가5
[8]  ASKP6                  매도호가6
[9]  ASKP7                  매도호가7
[10] ASKP8                  매도호가8
[11] ASKP9                  매도호가9

[12] BIDP1                  매수호가1
[13] BIDP2                  매수호가2
[14] BIDP3                  매수호가3
[15] BIDP4                  매수호가4
[16] BIDP5                  매수호가5
[17] BIDP6                  매수호가6
[18] BIDP7                  매수호가7
[19] BIDP8                  매수호가8
[20] BIDP9                  매수호가9

[21] ASKP_RSQN1             매도호가잔량1
[22] ASKP_RSQN2             매도호가잔량2
[23] ASKP_RSQN3             매도호가잔량3
[24] ASKP_RSQN4             매도호가잔량4
[25] ASKP_RSQN5             매도호가잔량5
[26] ASKP_RSQN6             매도호가잔량6
[27] ASKP_RSQN7             매도호가잔량7
[28] ASKP_RSQN8             매도호가잔량8
[29] ASKP_RSQN9             매도호가잔량9

[30] BIDP_RSQN1             매수호가잔량1
[31] BIDP_RSQN2             매수호가잔량2
[32] BIDP_RSQN3             매수호가잔량3
[33] BIDP_RSQN4             매수호가잔량4
[34] BIDP_RSQN5             매수호가잔량5
[35] BIDP_RSQN6             매수호가잔량6
[36] BIDP_RSQN7             매수호가잔량7
[37] BIDP_RSQN8             매수호가잔량8
[38] BIDP_RSQN9             매수호가잔량9

[39] TOTAL_ASKP_RSQN        총매도호가잔량
[40] TOTAL_BIDP_RSQN        총매수호가잔량
[41] OVTM_TOTAL_ASKP_RSQN   시간외총매도호가잔량
[42] OVTM_TOTAL_BIDP_RSQN   시간외총매수호가잔량

[43] ANTC_CNPR              예상체결가
[44] ANTC_CNQN              예상체결량
[45] ANTC_VOL               예상거래량
[46] ANTC_CNTG_VRSS         예상체결대비
[47] ANTC_CNTG_VRSS_SIGN    예상체결대비부호
[48] ANTC_CNTG_PRDY_CTRT    예상체결전일대비율

[49] ACML_VOL               누적거래량
[50] TOTAL_ASKP_RSQN_ICDC   총매도호가잔량증감
[51] TOTAL_BIDP_RSQN_ICDC   총매수호가잔량증감
[52] OVTM_TOTAL_ASKP_ICDC   시간외총매도호가증감
[53] OVTM_TOTAL_BIDP_ICDC   시간외총매수호가증감
"""


# ============================================================
# 사용 예시
# ============================================================

"""
# Collector 구현 시:

from src.core.kis_tick_schema import TickResponseBody
from src.core.kis_orderbook_schema import OrderbookResponseBody

# 정규장 체결가
class KRRealCollector(BaseCollector):
    def __init__(self):
        super().__init__(market="KR", tr_id="H0STCNT0")
    # parse_tick() 사용

# 시간외 체결가 (동일 스키마!)
class AfterHoursTickCollector(BaseCollector):
    def __init__(self):
        super().__init__(market="KR", tr_id="H0STOUP0")
    # parse_tick() 재사용 가능!

# 정규장 호가
class KRASPCollector(BaseCollector):
    def __init__(self):
        super().__init__(market="KR", tr_id="H0STASP0")
    # parse_orderbook() 사용

# 시간외 호가 (동일 스키마!)
class AfterHoursASPCollector(BaseCollector):
    def __init__(self):
        super().__init__(market="KR", tr_id="H0STOAA0")
    # parse_orderbook() 재사용 가능!
"""
