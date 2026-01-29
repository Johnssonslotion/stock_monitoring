"""
KISClient - 한국투자증권 REST API 클라이언트

한국투자증권(KIS) REST API를 호출하는 클라이언트 구현체입니다.

Reference:
    - ISSUE-040: API Hub v2 Phase 2 - Real API Integration
    - https://apiportal.koreainvestment.com/apiservice/
"""
import os
from typing import Dict, Any, Optional, TYPE_CHECKING

import httpx

from .base import BaseAPIClient
from .exceptions import APIError, AuthenticationError

if TYPE_CHECKING:
    from ..token_manager import TokenManager


class KISClient(BaseAPIClient):
    """
    한국투자증권 REST API 클라이언트

    TokenManager 통합으로 토큰 자동 관리 지원.

    Reference:
        https://apiportal.koreainvestment.com/apiservice/
    """

    def __init__(
        self,
        app_key: str = None,
        app_secret: str = None,
        access_token: str = None,
        base_url: str = None,
        token_manager: Optional["TokenManager"] = None
    ):
        """
        Args:
            app_key: KIS API App Key (환경변수 KIS_APP_KEY 대체 가능)
            app_secret: KIS API App Secret (환경변수 KIS_APP_SECRET 대체 가능)
            access_token: 직접 주입할 액세스 토큰 (선택)
            base_url: KIS API Base URL (환경변수 KIS_BASE_URL 대체 가능)
            token_manager: TokenManager 인스턴스 (Redis SSoT)
        """
        # 환경변수 우선, 인자 대체
        self.app_key = app_key or os.getenv("KIS_APP_KEY")
        self.app_secret = app_secret or os.getenv("KIS_APP_SECRET")

        if not self.app_key or not self.app_secret:
            raise ValueError("KIS_APP_KEY and KIS_APP_SECRET are required")

        # Base URL 결정 (실전/모의)
        _base_url = base_url or os.getenv(
            "KIS_BASE_URL",
            "https://openapi.koreainvestment.com:9443"
        )

        super().__init__(
            provider="KIS",
            base_url=_base_url,
            timeout=10.0,
            token_manager=token_manager
        )

        # 직접 주입된 토큰 설정 (TokenManager 없을 때)
        if access_token:
            self._access_token = access_token

    # TR ID to URL Path 매핑 (BackfillManager 참조)
    TR_URL_MAP = {
        # 기존 시세 조회
        "FHKST01010100": (
            "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
        ),
        "FHKST01010300": (
            "/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
        ),
        "FHKST01010400": (
            "/uapi/domestic-stock/v1/quotations/inquire-ccnl"
        ),
        "FHKST03010200": (
            "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
        ),
        "HHDFS76950200": (
            "/uapi/overseas-price/v1/quotations/inquire-daily-chartprice"
        ),
        # Pillar 8: Market Intelligence (RFC-010)
        "FHKST01010900": (
            "/uapi/domestic-stock/v1/quotations/inquire-investor"
        ),
        "FHKST01060200": (
            "/uapi/domestic-stock/v1/quotations/inquire-foreign-daily"
        ),
        "FHKST01060300": (
            "/uapi/domestic-stock/v1/quotations/inquire-member-daily"
        ),
        "FHKST01060500": (
            "/uapi/domestic-stock/v1/quotations/inquire-daily-short"
        ),
        "FHKST01060600": (
            "/uapi/domestic-stock/v1/quotations/inquire-daily-program"
        ),
    }

    def _build_headers(self, tr_id: str, **kwargs) -> Dict[str, str]:
        """KIS API 헤더 구성"""
        return {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self._access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P"  # 개인
        }

    def _build_request_body(
        self, tr_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """KIS API 요청 파라미터 구성"""

        # 분봉 조회 (FHKST01010100)
        if tr_id == "FHKST01010100":
            return {
                "FID_COND_MRKT_DIV_CODE": "J",  # 주식
                "FID_INPUT_ISCD": params["symbol"],
                "FID_INPUT_HOUR_1": params.get("time", "153000"),
                "FID_PW_DATA_INCU_YN": "Y"
            }

        # Tick 조회 (FHKST01010300)
        if tr_id == "FHKST01010300":
            return {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": params["symbol"],
                "FID_INPUT_HOUR_1": params.get("time", "153000")
            }

        # 현재가 분봉 조회 (FHKST01010400)
        if tr_id == "FHKST01010400":
            return {
                "FID_COND_MRKT_DIV_CODE": params.get("FID_COND_MRKT_DIV_CODE", "J"),
                "FID_INPUT_ISCD": params.get("FID_INPUT_ISCD", params.get("symbol", ""))
            }

        # 기간별 분봉 조회 (FHKST03010200)
        if tr_id == "FHKST03010200":
            return {
                "fid_etc_cls_code": params.get("fid_etc_cls_code", ""),
                "fid_cond_mrkt_div_code": params.get("fid_cond_mrkt_div_code", "J"),
                "fid_input_iscd": params.get("fid_input_iscd", params.get("symbol", "")),
                "fid_input_hour_1": params.get("fid_input_hour_1", params.get("time", "153000")),
                "fid_pw_data_incu_yn": params.get("fid_pw_data_incu_yn", "Y")
            }

        # 해외주식 기간별 분봉 (HHDFS76950200)
        if tr_id == "HHDFS76950200":
            return {
                "AUTH": params.get("AUTH", ""),
                "EXCD": params.get("EXCD", "NAS"),
                "SYMB": params.get("SYMB", params.get("symbol", "")),
                "GUBN": params.get("GUBN", "0"),
                "BYMD": params.get("BYMD", ""),
                "MODP": params.get("MODP", "1")
            }

        # Pillar 8: Market Intelligence TR IDs
        # 주식현재가 투자자 (FHKST01010900)
        if tr_id == "FHKST01010900":
            return {
                "FID_COND_MRKT_DIV_CODE": params.get("FID_COND_MRKT_DIV_CODE", "J"),
                "FID_INPUT_ISCD": params.get("FID_INPUT_ISCD", params.get("symbol", ""))
            }

        # 종목별 외국계 순매수추이 (FHKST01060200)
        if tr_id == "FHKST01060200":
            return {
                "FID_COND_MRKT_DIV_CODE": params.get("FID_COND_MRKT_DIV_CODE", "J"),
                "FID_INPUT_ISCD": params.get("FID_INPUT_ISCD", params.get("symbol", "")),
                "FID_INPUT_DATE_1": params.get("FID_INPUT_DATE_1", ""),
                "FID_INPUT_DATE_2": params.get("FID_INPUT_DATE_2", "")
            }

        # 국내기관/외국인 매매종목 (FHKST01060300)
        if tr_id == "FHKST01060300":
            return {
                "FID_COND_MRKT_DIV_CODE": params.get("FID_COND_MRKT_DIV_CODE", "J"),
                "FID_INPUT_ISCD": params.get("FID_INPUT_ISCD", params.get("symbol", ""))
            }

        # 공매도 일별추이 (FHKST01060500)
        if tr_id == "FHKST01060500":
            return {
                "FID_COND_MRKT_DIV_CODE": params.get("FID_COND_MRKT_DIV_CODE", "J"),
                "FID_INPUT_ISCD": params.get("FID_INPUT_ISCD", params.get("symbol", "")),
                "FID_INPUT_DATE_1": params.get("FID_INPUT_DATE_1", ""),
                "FID_INPUT_DATE_2": params.get("FID_INPUT_DATE_2", "")
            }

        # 프로그램매매 추이 (FHKST01060600)
        if tr_id == "FHKST01060600":
            return {
                "FID_COND_MRKT_DIV_CODE": params.get("FID_COND_MRKT_DIV_CODE", "J"),
                "FID_INPUT_ISCD": params.get("FID_INPUT_ISCD", params.get("symbol", ""))
            }

        # 다른 TR ID는 params 그대로 전달
        return params

    def get_url_for_tr_id(self, tr_id: str) -> str:
        """TR ID에 해당하는 URL 경로 반환"""
        return self.TR_URL_MAP.get(tr_id, f"/{tr_id}")

    # GET 요청이 필요한 TR ID 목록
    GET_TRS = {
        # 기존
        "FHKST01010100",
        "FHKST01010300",
        "FHKST01010400",
        "FHKST03010200",
        "HHDFS76950200",
        # Pillar 8: Market Intelligence
        "FHKST01010900",
        "FHKST01060200",
        "FHKST01060300",
        "FHKST01060500",
        "FHKST01060600",
    }

    async def execute(
        self,
        tr_id: str,
        params: Dict[str, Any],
        method: str = None
    ) -> Dict[str, Any]:
        """
        KIS API 실행 (GET/POST 자동 선택)
        """
        if method is None:
            method = "GET" if tr_id in self.GET_TRS else "POST"
        
        return await super().execute(tr_id, params, method)

    async def _handle_response(
        self, response: httpx.Response, tr_id: str
    ) -> Dict[str, Any]:
        """KIS API 응답 처리"""
        data = response.json()

        # DEBUG: 응답 구조 확인
        self.logger.info(f"🔍 KIS API Response keys: {list(data.keys())[:10]}")
        self.logger.info(f"🔍 rt_cd={repr(data.get('rt_cd'))}, msg_cd={data.get('msg_cd')}, msg1={data.get('msg1')}")

        # 에러 체크
        rt_cd = data.get("rt_cd")
        # rt_cd가 None이거나 "0"이거나 빈 문자열이면 성공으로 간주
        if rt_cd and rt_cd != "0":
            error_msg = data.get("msg1", "Unknown error")
            # 보안: 전체 응답 데이터를 로그에 출력하지 않음 (토큰이 포함될 수 있음)
            self.logger.error(f"❌ KIS API Error: rt_cd={rt_cd}, msg1={error_msg}")
            raise APIError(f"KIS API Error ({rt_cd}): {error_msg}")

        # 정규화된 데이터 반환
        return {
            "status": "success",
            "provider": "KIS",
            "tr_id": tr_id,
            "data": data.get(
                "output1", data.get("output2", data.get("output", []))
            ),
            "message": data.get("msg1", "")
        }

    async def refresh_token(self) -> str:
        """
        KIS 토큰 갱신

        Note:
            TokenManager 사용 시 이 메서드는 직접 호출하지 않음.
            TokenManager.refresh_token_with_lock()이 대신 호출함.
        """
        if self._client is None:
            await self.connect()

        response = await self._client.post(
            url="/oauth2/tokenP",
            json={
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }
        )

        response.raise_for_status()
        data = response.json()

        # KIS OAuth 응답 형식: 성공 시 access_token 직접 반환
        # 실패 시 error_code, error_description 반환
        if "error_code" in data:
            raise AuthenticationError(
                f"KIS token refresh failed ({data['error_code']}): "
                f"{data.get('error_description', 'Unknown error')}"
            )

        if "access_token" not in data:
            raise AuthenticationError(
                "KIS token refresh failed: No access_token in response"
            )

        self._access_token = data["access_token"]
        self.logger.info("✅ KIS access token refreshed")

        return self._access_token
