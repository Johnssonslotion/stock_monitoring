"""
KiwoomClient - 키움증권 REST API 클라이언트

키움증권 REST API를 호출하는 클라이언트 구현체입니다.

Reference:
    - ISSUE-040: API Hub v2 Phase 2 - Real API Integration
    - https://apiportal.kiwoom.com/
"""
import os
from typing import Dict, Any, Optional, TYPE_CHECKING

import httpx

from .base import BaseAPIClient
from .exceptions import APIError, AuthenticationError

if TYPE_CHECKING:
    from ..token_manager import TokenManager


class KiwoomClient(BaseAPIClient):
    """
    키움증권 REST API 클라이언트

    TokenManager 통합으로 토큰 자동 관리 지원.

    Reference:
        https://apiportal.kiwoom.com/
    """

    def __init__(
        self,
        api_key: str = None,
        secret_key: str = None,
        access_token: str = None,
        base_url: str = None,
        token_manager: Optional["TokenManager"] = None
    ):
        """
        Args:
            api_key: Kiwoom API Key (환경변수 KIWOOM_API_KEY 대체 가능)
            secret_key: Kiwoom Secret Key (환경변수 KIWOOM_SECRET_KEY 대체 가능)
            access_token: 직접 주입할 액세스 토큰 (선택)
            base_url: Kiwoom API Base URL (환경변수 KIWOOM_API_URL 대체 가능)
            token_manager: TokenManager 인스턴스 (Redis SSoT)
        """
        self.api_key = api_key or os.getenv("KIWOOM_API_KEY") or os.getenv("KIWOOM_APP_KEY")
        self.secret_key = secret_key or os.getenv("KIWOOM_SECRET_KEY") or os.getenv("KIWOOM_APP_SECRET")

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "KIWOOM_API_KEY and KIWOOM_SECRET_KEY are required"
            )

        # Base URL 결정 (RFC-008: api.kiwoom.com 사용)
        _base_url = base_url or os.getenv(
            "KIWOOM_REST_API_URL",
            "https://api.kiwoom.com"
        )

        super().__init__(
            provider="KIWOOM",
            base_url=_base_url,
            timeout=10.0,
            token_manager=token_manager
        )

        # 직접 주입된 토큰 설정 (TokenManager 없을 때)
        if access_token:
            self._access_token = access_token

    def _build_headers(self, tr_id: str, **kwargs) -> Dict[str, str]:
        """Kiwoom API 헤더 구성 (RFC-008 준수)"""
        # OpenAPI+ TR ID → REST API ID 매핑
        api_id_map = {
            "opt10081": "ka10080",  # 분봉 조회
            "opt10079": "ka10079",  # 틱 조회
        }
        api_id = api_id_map.get(tr_id, tr_id)
        
        return {
            "Content-Type": "application/json; charset=UTF-8",
            "authorization": f"Bearer {self._access_token}",
            "api-id": api_id,  # 매핑된 API ID 사용
            "content-yn": "N",
            "User-Agent": "Mozilla/5.0"
        }

    def _build_request_body(
        self, tr_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Kiwoom API 요청 바디 구성 (REST API ka100xx 형식)"""

        # 분봉 조회 (ka10080) - opt10081은 REST API에서 지원 안함
        # opt10081을 ka10080으로 매핑
        if tr_id in ["ka10080", "opt10081"]:
            return {
                "stk_cd": params["symbol"],
                "tic_scope": params.get("timeframe", "1"),
                "upd_stkpc_tp": "1"
            }

        # Tick 조회 (ka10079) - opt10079를 ka10079로 매핑  
        if tr_id in ["ka10079", "opt10079"]:
            return {
                "stk_cd": params["symbol"],
                "tic_scope": params.get("tick_unit", "1"),
                "upd_stkpc_tp": "0"
            }

        return params

    def get_url_for_tr_id(self, tr_id: str) -> str:
        """Kiwoom REST API는 단일 엔드포인트 사용 (RFC-008)"""
        return "/api/dostk/chart"
    async def _handle_response(
        self, response: httpx.Response, tr_id: str
    ) -> Dict[str, Any]:
        """Kiwoom API 응답 처리 (RFC-008 준수)"""
        data = response.json()

        # 에러 체크 (Kiwoom REST는 HTTP 200이면서 본문 내용으로 판단)
        # 성공 시 별도의 rsp_cd가 없을 수 있으므로 본문의 데이터 유무로 판단하거나
        # trnm 응답을 확인해야 함. (verification collector 코드 기반)
        
        # ka10080 (분봉) 데이터 키: stk_min_pole_chart_qry
        # ka10079 (틱) 데이터 키: stk_tic_chart_qry
        data_key = "stk_min_pole_chart_qry" if tr_id in ["ka10080", "opt10081"] else "stk_tic_chart_qry"
        
        output_data = data.get(data_key, [])
        
        if not output_data and tr_id not in ["LOGIN", "REG"]:
            # 데이터가 없는 경우를 에러로 볼 것인지 결정 필요. 
            # 일단 빈 리스트 반환을 허용하되, 명확한 에러 메시지가 있으면 예외 발생
            if "return_msg" in data and data.get("return_code") != "0000":
                 raise APIError(f"Kiwoom API Error: {data.get('return_msg')}")

        return {
            "status": "success",
            "provider": "KIWOOM",
            "tr_id": tr_id,
            "data": output_data,
            "message": data.get("return_msg", "Success")
        }

    async def refresh_token(self) -> str:
        """
        Kiwoom 토큰 갱신

        Note:
            TokenManager 사용 시 이 메서드는 직접 호출하지 않음.
            TokenManager.refresh_token_with_lock()이 대신 호출함.
        """
        if self._client is None:
            await self.connect()

        response = await self._client.post(
            url="/oauth/token",
            json={
                "grant_type": "client_credentials",
                "appkey": self.api_key,
                "secretkey": self.secret_key
            }
        )

        response.raise_for_status()
        data = response.json()

        if data.get("rsp_cd") != "0000":
            raise AuthenticationError(
                f"Kiwoom token refresh failed: "
                f"{data.get('rsp_msg', 'Unknown error')}"
            )

        self._access_token = data["access_token"]
        self.logger.info("✅ Kiwoom access token refreshed")

        return self._access_token
