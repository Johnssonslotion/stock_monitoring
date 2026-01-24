"""
Unit Tests for KiwoomClient

KiwoomClient의 API ID 파라미터 빌딩 및 URL 매핑 테스트
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.api_gateway.hub.clients.kiwoom_client import KiwoomClient
from src.api_gateway.hub.clients.exceptions import APIError


class TestKiwoomClientInitialization:
    """KiwoomClient 초기화 테스트"""

    def test_init_with_explicit_credentials(self):
        """명시적 credentials로 초기화"""
        client = KiwoomClient(
            api_key="test_key",
            secret_key="test_secret"
        )
        assert client.api_key == "test_key"
        assert client.secret_key == "test_secret"
        assert client.provider == "KIWOOM"

    def test_init_without_credentials_raises_error(self):
        """Credentials 없이 초기화 시 에러 발생"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="KIWOOM_API_KEY and KIWOOM_SECRET_KEY are required"):
                KiwoomClient()


class TestAPIIDURLMapping:
    """API ID → URL 매핑 테스트"""

    def test_all_api_ids_use_same_endpoint(self):
        """모든 Kiwoom API ID가 동일한 엔드포인트를 사용하는지 확인 (RFC-008)"""
        client = KiwoomClient(api_key="test", secret_key="test")
        
        api_ids = ["ka10080", "ka10079"]
        
        for api_id in api_ids:
            url = client.get_url_for_tr_id(api_id)
            assert url == "/api/dostk/chart", f"API ID {api_id} should use /api/dostk/chart"

    def test_get_url_for_tr_id(self):
        """get_url_for_tr_id 메소드 테스트"""
        client = KiwoomClient(api_key="test", secret_key="test")
        
        # ka10080 (분봉)
        url = client.get_url_for_tr_id("ka10080")
        assert url == "/api/dostk/chart"
        
        # ka10079 (틱)
        url = client.get_url_for_tr_id("ka10079")
        assert url == "/api/dostk/chart"


class TestRequestBodyBuilding:
    """요청 파라미터 빌딩 테스트"""

    def test_build_ka10080_params(self):
        """ka10080 (분봉 조회) 파라미터 빌딩"""
        client = KiwoomClient(api_key="test", secret_key="test")
        
        # 1. symbol 키 사용
        params = client._build_request_body("ka10080", {
            "symbol": "005930",
            "timeframe": "1"
        })
        
        assert params["stk_cd"] == "005930"
        assert params["tic_scope"] == "1"
        assert params["upd_stkpc_tp"] == "1"
        
        # 2. timeframe 기본값 테스트
        params = client._build_request_body("ka10080", {
            "symbol": "035720"
        })
        
        assert params["stk_cd"] == "035720"
        assert params["tic_scope"] == "1"  # 기본값
        assert params["upd_stkpc_tp"] == "1"

    def test_build_ka10079_params(self):
        """ka10079 (틱 조회) 파라미터 빌딩"""
        client = KiwoomClient(api_key="test", secret_key="test")
        
        # 1. symbol + tick_unit 사용
        params = client._build_request_body("ka10079", {
            "symbol": "005930",
            "tick_unit": "10"
        })
        
        assert params["stk_cd"] == "005930"
        assert params["tic_scope"] == "10"
        assert params["upd_stkpc_tp"] == "0"
        
        # 2. tick_unit 기본값 테스트
        params = client._build_request_body("ka10079", {
            "symbol": "035420"
        })
        
        assert params["stk_cd"] == "035420"
        assert params["tic_scope"] == "1"  # 기본값
        assert params["upd_stkpc_tp"] == "0"

    def test_build_opt10081_legacy_mapping(self):
        """opt10081 (OpenAPI+ TR ID) → ka10080 자동 매핑 테스트"""
        client = KiwoomClient(api_key="test", secret_key="test")
        
        params = client._build_request_body("opt10081", {
            "symbol": "005930"
        })
        
        assert params["stk_cd"] == "005930"
        assert params["tic_scope"] == "1"
        assert params["upd_stkpc_tp"] == "1"

    def test_build_opt10079_legacy_mapping(self):
        """opt10079 (OpenAPI+ TR ID) → ka10079 자동 매핑 테스트"""
        client = KiwoomClient(api_key="test", secret_key="test")
        
        params = client._build_request_body("opt10079", {
            "symbol": "005930"
        })
        
        assert params["stk_cd"] == "005930"
        assert params["tic_scope"] == "1"
        assert params["upd_stkpc_tp"] == "0"

    def test_unknown_api_id_returns_params_as_is(self):
        """알 수 없는 API ID는 params를 그대로 반환"""
        client = KiwoomClient(api_key="test", secret_key="test")
        
        params = client._build_request_body("unknown_api_id", {
            "key1": "value1",
            "key2": "value2"
        })
        
        assert params == {"key1": "value1", "key2": "value2"}


class TestHeaderBuilding:
    """헤더 빌딩 테스트"""

    def test_build_headers_ka10080(self):
        """ka10080용 헤더 빌딩"""
        client = KiwoomClient(api_key="test_key", secret_key="test_secret")
        client._access_token = "test_token"
        
        headers = client._build_headers("ka10080")
        
        assert headers["authorization"] == "Bearer test_token"
        assert headers["api-id"] == "ka10080"
        assert headers["content-yn"] == "N"
        assert headers["Content-Type"] == "application/json; charset=UTF-8"
        assert headers["User-Agent"] == "Mozilla/5.0"

    def test_build_headers_ka10079(self):
        """ka10079용 헤더 빌딩"""
        client = KiwoomClient(api_key="test_key", secret_key="test_secret")
        client._access_token = "test_token"
        
        headers = client._build_headers("ka10079")
        
        assert headers["authorization"] == "Bearer test_token"
        assert headers["api-id"] == "ka10079"

    def test_build_headers_opt10081_mapping(self):
        """opt10081 → ka10080 자동 매핑 (헤더)"""
        client = KiwoomClient(api_key="test_key", secret_key="test_secret")
        client._access_token = "test_token"
        
        headers = client._build_headers("opt10081")
        
        # opt10081을 ka10080으로 매핑해야 함
        assert headers["api-id"] == "ka10080"

    def test_build_headers_opt10079_mapping(self):
        """opt10079 → ka10079 자동 매핑 (헤더)"""
        client = KiwoomClient(api_key="test_key", secret_key="test_secret")
        client._access_token = "test_token"
        
        headers = client._build_headers("opt10079")
        
        # opt10079를 ka10079로 매핑해야 함
        assert headers["api-id"] == "ka10079"


class TestTRRegistryIntegration:
    """TR Registry와의 통합 테스트"""

    def test_all_implemented_kiwoom_api_ids_in_client(self):
        """TR Registry에서 구현 완료로 표시된 모든 Kiwoom API ID가 클라이언트에서 지원되는지 확인"""
        from src.api_gateway.hub.tr_registry import list_tr_ids, Provider
        
        client = KiwoomClient(api_key="test", secret_key="test")
        
        kiwoom_implemented = [
            s.tr_id for s in list_tr_ids(provider=Provider.KIWOOM, implemented_only=True)
        ]
        
        for api_id in kiwoom_implemented:
            # 클라이언트가 해당 API ID를 처리할 수 있는지 확인
            params = client._build_request_body(api_id, {"symbol": "005930"})
            assert "stk_cd" in params, \
                f"Implemented API ID {api_id} not properly handled by KiwoomClient"

    def test_tr_registry_endpoints_match(self):
        """TR Registry의 endpoint와 KiwoomClient get_url_for_tr_id가 일치하는지 확인"""
        from src.api_gateway.hub.tr_registry import get_tr_spec
        
        client = KiwoomClient(api_key="test", secret_key="test")
        
        api_ids = ["ka10080", "ka10079"]
        
        for api_id in api_ids:
            spec = get_tr_spec(api_id)
            if spec:
                client_url = client.get_url_for_tr_id(api_id)
                assert spec.endpoint == client_url, \
                    f"API ID {api_id}: Registry endpoint {spec.endpoint} != Client URL {client_url}"

    def test_tr_registry_implementation_status(self):
        """TR Registry의 구현 상태가 실제 클라이언트 구현과 일치하는지 확인"""
        from src.api_gateway.hub.tr_registry import get_tr_spec
        
        # ka10080: 구현 완료
        spec = get_tr_spec("ka10080")
        assert spec is not None
        assert spec.implemented is True
        
        # ka10079: 구현 완료 (2026-01-23)
        spec = get_tr_spec("ka10079")
        assert spec is not None
        assert spec.implemented is True

    def test_kiwoom_100_percent_coverage(self):
        """Kiwoom TR ID 100% 구현 완료 확인"""
        from src.api_gateway.hub.tr_registry import KIWOOM_REGISTRY
        
        total = len(KIWOOM_REGISTRY)
        implemented = len([s for s in KIWOOM_REGISTRY.values() if s.implemented])
        
        assert implemented == total, \
            f"Kiwoom coverage not 100%: {implemented}/{total} implemented"
        assert total == 2, "Expected 2 Kiwoom API IDs (ka10080, ka10079)"
