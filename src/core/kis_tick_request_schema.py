"""
KIS WebSocket Request Schema - 실시간 체결가
TR_ID: H0STCNT0 (실시간 체결가)
"""
from dataclasses import dataclass

@dataclass
class RequestHeader:
    approval_key: str    # 웹소켓 접속키
    custtype: str        # 고객타입
    tr_type: str         # 거래타입 (1=구독, 2=구독해제)
    content_type: str    # 컨텐츠타입 (주의: content-type이 아닌 content_type으로 변환)

@dataclass
class RequestBody:
    tr_id: str    # 거래ID (H0STCNT0)
    tr_key: str   # 구분값 (종목코드)
