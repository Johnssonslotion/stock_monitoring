"""
BaseAPIClient 및 KISClient 단위 테스트

Fixture 기반 테스트로 실제 API 호출 없이 검증합니다.
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import httpx

from src.api_gateway.hub.clients.base import BaseAPIClient
from src.api_gateway.hub.clients.kis_client import KISClient
from src.api_gateway.hub.clients.exceptions import (
    APIError,
    RateLimitError,
    AuthenticationError,
    NetworkError
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def kis_candle_fixture():
    """KIS 분봉 API 응답 Fixture"""
    return {
        "rt_cd": "0",
        "msg_cd": "MCA00000",
        "msg1": "정상처리 되었습니다.",
        "output2": [
            {
                "stck_bsop_date": "20260123",
                "stck_cntg_hour": "153000",
                "stck_prpr": "59100",
                "stck_oprc": "59000",
                "stck_hgpr": "59200",
                "stck_lwpr": "59000",
                "cntg_vol": "1523"
            }
        ]
    }


@pytest.fixture
def kis_error_fixture():
    """KIS 에러 응답 Fixture"""
    return {
        "rt_cd": "1",
        "msg_cd": "ERR001",
        "msg1": "잘못된 요청입니다."
    }


# ============================================================================
# KISClient Tests
# ============================================================================

class TestKISClient:
    """KISClient 단위 테스트"""
    
    def test_init_with_env_vars(self, monkeypatch):
        """환경변수로 초기화 테스트"""
        monkeypatch.setenv("KIS_APP_KEY", "test_app_key")
        monkeypatch.setenv("KIS_APP_SECRET", "test_app_secret")
        monkeypatch.setenv("KIS_BASE_URL", "https://test.api.com")
        
        client = KISClient()
        
        assert client.app_key == "test_app_key"
        assert client.app_secret == "test_app_secret"
        assert client.base_url == "https://test.api.com"
        assert client.provider == "KIS"
    
    def test_init_missing_credentials(self, monkeypatch):
        """인증정보 누락 시 ValueError 발생"""
        monkeypatch.delenv("KIS_APP_KEY", raising=False)
        monkeypatch.delenv("KIS_APP_SECRET", raising=False)
        
        with pytest.raises(ValueError, match="KIS_APP_KEY and KIS_APP_SECRET are required"):
            KISClient()
    
    def test_build_headers(self, monkeypatch):
        """헤더 구성 테스트"""
        monkeypatch.setenv("KIS_APP_KEY", "test_key")
        monkeypatch.setenv("KIS_APP_SECRET", "test_secret")
        
        client = KISClient(access_token="test_token")
        headers = client._build_headers("FHKST01010100")
        
        assert headers["authorization"] == "Bearer test_token"
        assert headers["appkey"] == "test_key"
        assert headers["appsecret"] == "test_secret"
        assert headers["tr_id"] == "FHKST01010100"
        assert headers["custtype"] == "P"
    
    def test_build_request_body_candle(self, monkeypatch):
        """분봉 조회 요청 바디 구성 테스트"""
        monkeypatch.setenv("KIS_APP_KEY", "test_key")
        monkeypatch.setenv("KIS_APP_SECRET", "test_secret")
        
        client = KISClient()
        body = client._build_request_body(
            "FHKST01010100",
            {"symbol": "005930", "timeframe": "1"}
        )
        
        assert body["FID_INPUT_ISCD"] == "005930"
        assert body["FID_INPUT_HOUR_1"] == "153000"
        assert body["FID_COND_MRKT_DIV_CODE"] == "J"
    
    @pytest.mark.asyncio
    async def test_handle_response_success(self, monkeypatch, kis_candle_fixture):
        """정상 응답 처리 테스트"""
        monkeypatch.setenv("KIS_APP_KEY", "test_key")
        monkeypatch.setenv("KIS_APP_SECRET", "test_secret")
        
        client = KISClient()
        
        mock_response = MagicMock()
        mock_response.json.return_value = kis_candle_fixture
        
        result = await client._handle_response(mock_response, "FHKST01010100")
        
        assert result["status"] == "success"
        assert result["provider"] == "KIS"
        assert result["tr_id"] == "FHKST01010100"
        assert len(result["data"]) == 1
    
    @pytest.mark.asyncio
    async def test_handle_response_error(self, monkeypatch, kis_error_fixture):
        """에러 응답 처리 테스트"""
        monkeypatch.setenv("KIS_APP_KEY", "test_key")
        monkeypatch.setenv("KIS_APP_SECRET", "test_secret")
        
        client = KISClient()
        
        mock_response = MagicMock()
        mock_response.json.return_value = kis_error_fixture
        
        with pytest.raises(APIError, match="KIS API Error"):
            await client._handle_response(mock_response, "FHKST01010100")


# ============================================================================
# BaseAPIClient Tests (via concrete implementation)
# ============================================================================

class TestBaseAPIClientBehavior:
    """BaseAPIClient 공통 동작 테스트 (KISClient를 통해 검증)"""
    
    @pytest.mark.asyncio
    async def test_connect_creates_client(self, monkeypatch):
        """connect() 호출 시 httpx.AsyncClient 생성"""
        monkeypatch.setenv("KIS_APP_KEY", "test_key")
        monkeypatch.setenv("KIS_APP_SECRET", "test_secret")
        
        client = KISClient()
        assert client._client is None
        
        await client.connect()
        assert client._client is not None
        
        await client.disconnect()
        assert client._client is None
    
    @pytest.mark.asyncio
    async def test_execute_timeout(self, monkeypatch):
        """타임아웃 처리 테스트"""
        monkeypatch.setenv("KIS_APP_KEY", "test_key")
        monkeypatch.setenv("KIS_APP_SECRET", "test_secret")

        client = KISClient()
        client.timeout = 0.1  # 100ms
        client._access_token = "test_token"  # 토큰 설정 (ensure_token 통과용)

        async def slow_operation(*args, **kwargs):
            await asyncio.sleep(1)  # 1초 지연
            return {}

        with patch.object(client, "_execute_with_retry", side_effect=slow_operation):
            with pytest.raises(TimeoutError):
                await client.execute("FHKST01010100", {"symbol": "005930"})
