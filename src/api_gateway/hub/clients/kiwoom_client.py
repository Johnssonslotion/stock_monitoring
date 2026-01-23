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
        self.api_key = api_key or os.getenv("KIWOOM_API_KEY")
        self.secret_key = secret_key or os.getenv("KIWOOM_SECRET_KEY")

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "KIWOOM_API_KEY and KIWOOM_SECRET_KEY are required"
            )

        _base_url = base_url or os.getenv(
            "KIWOOM_API_URL",
            "https://openapi.kiwoom.com:9443"
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
        """Kiwoom API 헤더 구성"""
        return {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self._access_token}",
            "apikey": self.api_key,
            "tr_cd": tr_id
        }

    def _build_request_body(
        self, tr_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Kiwoom API 요청 바디 구성"""

        # 분봉 조회 (opt10081)
        if tr_id == "opt10081":
            return {
                "종목코드": params["symbol"],
                "틱범위": params.get("timeframe", "1"),
                "수정주가구분": "1"
            }

        # Tick 조회 (opt10079)
        if tr_id == "opt10079":
            return {
                "종목코드": params["symbol"],
                "틱범위": params.get("tick_unit", "1"),
                "수정주가구분": "1"
            }

        return params

    async def _handle_response(
        self, response: httpx.Response, tr_id: str
    ) -> Dict[str, Any]:
        """Kiwoom API 응답 처리"""
        data = response.json()

        # 에러 체크
        if data.get("rsp_cd") != "0000":
            error_msg = data.get("rsp_msg", "Unknown error")
            raise APIError(f"Kiwoom API Error: {error_msg}")

        return {
            "status": "success",
            "provider": "KIWOOM",
            "tr_id": tr_id,
            "data": data.get("output", []),
            "message": data.get("rsp_msg", "")
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
