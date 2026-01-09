"""
KIS WebSocket Request Schema (H0STCNT0)
국내주식 실시간호가
"""
from dataclasses import dataclass

@dataclass
class RequestHeader:
    approval_key: str    # 웹소켓 접속키
    custtype: str        # 고객타입
    tr_type: str         # 거래타입 (1=구독, 2=구독해제)
    content_type: str    # 컨텐츠타입 (주의: content-type이 아닌 content_type)

@dataclass
class RequestBody:
    tr_id: str    # 거래ID (H0STCNT0)
    tr_key: str   # 구분값 (종목코드, 예: 005930)

@dataclass
class WebSocketRequest:
    header: RequestHeader
    body: dict  # {"input": RequestBody}
