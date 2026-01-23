"""
BaseAPIClient - REST API 클라이언트 추상 베이스 클래스

모든 Provider(KIS, Kiwoom 등)의 공통 인터페이스를 정의합니다.
TokenManager 통합으로 토큰 자동 관리 지원.

Reference:
    - ISSUE-040: API Hub v2 Phase 2 - Real API Integration
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TYPE_CHECKING

import httpx

from .exceptions import (
    APIError,
    RateLimitError,
    AuthenticationError,
    NetworkError
)

if TYPE_CHECKING:
    from ..token_manager import TokenManager


class BaseAPIClient(ABC):
    """
    REST API 클라이언트 추상 베이스 클래스

    KIS, Kiwoom 등 모든 API 클라이언트의 공통 인터페이스를 정의합니다.
    """

    def __init__(
        self,
        provider: str,
        base_url: str,
        timeout: float = 10.0,
        token_manager: Optional["TokenManager"] = None
    ):
        """
        Args:
            provider: 제공자 이름 (예: "KIS", "KIWOOM")
            base_url: API Base URL
            timeout: 요청 타임아웃 (초 단위, 기본값 10초)
            token_manager: TokenManager 인스턴스 (Redis SSoT)
        """
        self.provider = provider
        self.base_url = base_url
        self.timeout = timeout
        self.token_manager = token_manager
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None  # 로컬 캐시
        self.logger = logging.getLogger(f"{provider}Client")

    @abstractmethod
    def _build_headers(self, tr_id: str, **kwargs) -> Dict[str, str]:
        """
        API 요청 헤더 구성 (Provider별 구현 필요)

        Args:
            tr_id: 거래 ID (예: FHKST01010100)
            **kwargs: 추가 헤더 파라미터

        Returns:
            Dict[str, str]: HTTP 헤더 딕셔너리
        """
        pass

    @abstractmethod
    def _build_request_body(
        self, tr_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        API 요청 바디 구성 (Provider별 구현 필요)

        Args:
            tr_id: 거래 ID
            params: 요청 파라미터

        Returns:
            Dict[str, Any]: 요청 바디 (JSON)
        """
        pass

    @abstractmethod
    async def _handle_response(
        self, response: httpx.Response, tr_id: str
    ) -> Dict[str, Any]:
        """
        API 응답 파싱 및 검증 (Provider별 구현 필요)

        Args:
            response: httpx Response 객체
            tr_id: 거래 ID

        Returns:
            Dict[str, Any]: 정규화된 응답 데이터

        Raises:
            APIError: API 에러 발생 시
            ValidationError: 응답 데이터 검증 실패 시
        """
        pass

    @abstractmethod
    async def refresh_token(self) -> str:
        """
        액세스 토큰 갱신 (Provider별 구현 필요)

        Returns:
            str: 새로운 액세스 토큰

        Raises:
            AuthenticationError: 토큰 갱신 실패 시
        """
        pass

    async def connect(self):
        """HTTP 클라이언트 초기화"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"User-Agent": f"APIHub/{self.provider}"}
            )
            self.logger.info(
                f"✅ {self.provider} client connected to {self.base_url}"
            )

    async def disconnect(self):
        """HTTP 클라이언트 종료"""
        if self._client:
            await self._client.aclose()
            self._client = None
            self.logger.info(f"🔴 {self.provider} client disconnected")

    @property
    def access_token(self) -> Optional[str]:
        """현재 액세스 토큰 (로컬 캐시)"""
        return self._access_token

    @access_token.setter
    def access_token(self, value: str):
        """액세스 토큰 설정"""
        self._access_token = value

    async def ensure_token(self) -> str:
        """
        토큰이 유효한지 확인하고, 필요시 TokenManager에서 로드

        Returns:
            str: 유효한 액세스 토큰

        Raises:
            AuthenticationError: 토큰을 가져올 수 없는 경우
        """
        if self.token_manager is not None:
            # TokenManager에서 토큰 조회 (자동 갱신 포함)
            token = await self.token_manager.get_token(self.provider)
            if token:
                self.logger.debug(f"✅ Token for {self.provider} acquired from manager")
                self._access_token = token
                return token
            else:
                self.logger.error(f"❌ TokenManager returned None for {self.provider}")
                raise AuthenticationError(
                    f"Failed to get token for {self.provider} from TokenManager"
                )
        elif self._access_token:
            # TokenManager 없이 직접 주입된 토큰 사용
            return self._access_token
        else:
            raise AuthenticationError(
                f"No token available for {self.provider}. "
                "Either provide token_manager or set access_token directly."
            )

    async def execute(
        self,
        tr_id: str,
        params: Dict[str, Any],
        method: str = "POST"
    ) -> Dict[str, Any]:
        """
        API 요청 실행 (공통 로직)

        토큰 자동 로드/갱신 포함.

        Args:
            tr_id: 거래 ID
            params: 요청 파라미터
            method: HTTP 메서드 (기본값: POST)

        Returns:
            Dict[str, Any]: 정규화된 응답 데이터

        Raises:
            TimeoutError: 타임아웃 발생 시
            APIError: API 에러 발생 시
            NetworkError: 네트워크 오류 발생 시
            AuthenticationError: 토큰 문제 발생 시
        """
        if self._client is None:
            await self.connect()

        # 토큰 확보 (TokenManager 또는 로컬 캐시)
        await self.ensure_token()

        try:
            # 타임아웃 적용
            result = await asyncio.wait_for(
                self._execute_with_retry(tr_id, params, method),
                timeout=self.timeout
            )
            return result

        except asyncio.TimeoutError:
            raise TimeoutError(
                f"{self.provider} API timeout after {self.timeout}s "
                f"(tr_id={tr_id})"
            )
        except AuthenticationError:
            # 401 에러: 토큰 갱신 후 1회 재시도
            if self.token_manager:
                self.logger.warning(
                    f"⚠️ {self.provider} auth failed, refreshing token..."
                )
                new_token = await self.token_manager.refresh_token_with_lock(
                    self.provider
                )
                if new_token:
                    self._access_token = new_token
                    # 재시도
                    return await asyncio.wait_for(
                        self._execute_with_retry(tr_id, params, method),
                        timeout=self.timeout
                    )
            raise
        except Exception as e:
            await self._handle_error(tr_id, e)
            raise

    async def _execute_with_retry(
        self,
        tr_id: str,
        params: Dict[str, Any],
        method: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        재시도 로직이 포함된 API 실행

        Args:
            tr_id: 거래 ID
            params: 요청 파라미터
            method: HTTP 메서드
            max_retries: 최대 재시도 횟수

        Returns:
            Dict[str, Any]: 정규화된 응답 데이터

        Note:
            - 5xx 에러: 재시도 (exponential backoff)
            - 4xx 에러: 즉시 실패 (재시도 안 함)
            - 429 에러: Rate Limit 초과, Circuit Breaker 트리거
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                # 헤더 및 바디 구성
                headers = self._build_headers(tr_id)
                body = self._build_request_body(tr_id, params)

                # URL 경로 결정 (클라이언트별 매핑 지원)
                if hasattr(self, 'get_url_for_tr_id'):
                    url_path = self.get_url_for_tr_id(tr_id)
                else:
                    url_path = f"/{tr_id}"

                # HTTP 요청 (KIS API는 GET 사용)
                if method.upper() == "GET":
                    response = await self._client.get(
                        url=url_path,
                        headers=headers,
                        params=body
                    )
                else:  # POST
                    response = await self._client.post(
                        url=url_path,
                        headers=headers,
                        json=body
                    )

                # 응답 처리
                response.raise_for_status()
                return await self._handle_response(response, tr_id)

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code

                # 429 Rate Limit: 재시도 안 함, Circuit Breaker로 전달
                if status_code == 429:
                    raise RateLimitError(
                        f"{self.provider} Rate Limit exceeded (tr_id={tr_id})"
                    )

                # 401/403 인증 에러
                if status_code in (401, 403):
                    raise AuthenticationError(
                        f"{self.provider} Authentication failed "
                        f"({status_code}): {e.response.text} (tr_id={tr_id})"
                    )

                # 4xx 클라이언트 에러: 재시도 안 함
                if 400 <= status_code < 500:
                    raise APIError(
                        f"{self.provider} Client Error {status_code}: "
                        f"{e.response.text} (tr_id={tr_id})"
                    )

                # 5xx 서버 에러: 재시도
                if attempt < max_retries - 1:
                    backoff = 2 ** attempt  # exponential backoff
                    self.logger.warning(
                        f"⚠️ {self.provider} {tr_id} 5xx error, "
                        f"retrying in {backoff}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(backoff)
                    last_error = e
                    continue
                else:
                    raise APIError(
                        f"{self.provider} Server Error {status_code} after "
                        f"{max_retries} retries (tr_id={tr_id})"
                    )

            except httpx.NetworkError as e:
                if attempt < max_retries - 1:
                    backoff = 2 ** attempt
                    self.logger.warning(
                        f"⚠️ {self.provider} {tr_id} network error, "
                        f"retrying in {backoff}s"
                    )
                    await asyncio.sleep(backoff)
                    last_error = e
                    continue
                else:
                    raise NetworkError(
                        f"{self.provider} Network error after {max_retries} "
                        f"retries: {str(e)} (tr_id={tr_id})"
                    )

        # 모든 재시도 실패
        raise last_error

    async def _handle_error(self, tr_id: str, exception: Exception):
        """
        에러 로깅 및 추가 처리 (공통 로직)

        Args:
            tr_id: 거래 ID
            exception: 발생한 예외
        """
        self.logger.error(
            f"❌ API Error: {self.provider} {tr_id} - "
            f"{type(exception).__name__}: {str(exception)}",
            exc_info=True
        )
