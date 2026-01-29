"""
Unit Tests for KISClient

KISClient의 TR ID 파라미터 빌딩 및 URL 매핑 테스트
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.api_gateway.hub.clients.kis_client import KISClient
from src.api_gateway.hub.clients.exceptions import APIError


class TestKISClientInitialization:
    """KISClient 초기화 테스트"""

    def test_init_with_explicit_credentials(self):
        """명시적 credentials로 초기화"""
        client = KISClient(
            app_key="test_key",
            app_secret="test_secret"
        )
        assert client.app_key == "test_key"
        assert client.app_secret == "test_secret"
        assert client.provider == "KIS"

    def test_init_without_credentials_raises_error(self):
        """Credentials 없이 초기화 시 에러 발생"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="KIS_APP_KEY and KIS_APP_SECRET are required"):
                KISClient()


class TestTRURLMapping:
    """TR ID → URL 매핑 테스트"""

    def test_all_tr_ids_have_url_mapping(self):
        """모든 구현된 TR ID가 URL 매핑을 가지고 있는지 확인"""
        from src.api_gateway.hub.tr_registry import list_tr_ids, Provider
        
        kis_implemented = [
            s for s in list_tr_ids(provider=Provider.KIS)
            if s.implemented
        ]
        
        client = KISClient(app_key="test", app_secret="test")
        
        for spec in kis_implemented:
            tr_id = spec.tr_id
            assert tr_id in client.TR_URL_MAP, f"TR ID {tr_id} missing URL mapping"
            url = client.TR_URL_MAP[tr_id]
            assert url.startswith("/"), f"URL {url} should start with /"

    def test_tr_url_map_completeness(self):
        """TR_URL_MAP에 모든 필수 TR ID가 포함되어 있는지 확인"""
        client = KISClient(app_key="test", app_secret="test")
        
        required_tr_ids = {
            "FHKST01010100",
            "FHKST01010300",
            "FHKST01010400",
            "FHKST03010200",
            "HHDFS76950200"
        }
        
        for tr_id in required_tr_ids:
            assert tr_id in client.TR_URL_MAP, f"Missing {tr_id} in TR_URL_MAP"

    def test_get_url_for_tr_id(self):
        """get_url_for_tr_id 메소드 테스트"""
        client = KISClient(app_key="test", app_secret="test")
        
        url = client.get_url_for_tr_id("FHKST01010100")
        assert url == "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
        
        url = client.get_url_for_tr_id("FHKST01010400")
        assert url == "/uapi/domestic-stock/v1/quotations/inquire-ccnl"


class TestRequestBodyBuilding:
    """요청 파라미터 빌딩 테스트"""

    def test_build_fhkst01010100_params(self):
        """FHKST01010100 파라미터 빌딩"""
        client = KISClient(app_key="test", app_secret="test")
        
        params = client._build_request_body("FHKST01010100", {
            "symbol": "005930",
            "time": "150000"
        })
        
        assert params["FID_COND_MRKT_DIV_CODE"] == "J"
        assert params["FID_INPUT_ISCD"] == "005930"
        assert params["FID_INPUT_HOUR_1"] == "150000"
        assert params["FID_PW_DATA_INCU_YN"] == "Y"

    def test_build_fhkst01010300_params(self):
        """FHKST01010300 (틱 데이터) 파라미터 빌딩"""
        client = KISClient(app_key="test", app_secret="test")
        
        params = client._build_request_body("FHKST01010300", {
            "symbol": "005930",
            "time": "153000"
        })
        
        assert params["FID_COND_MRKT_DIV_CODE"] == "J"
        assert params["FID_INPUT_ISCD"] == "005930"
        assert params["FID_INPUT_HOUR_1"] == "153000"

    def test_build_fhkst01010400_params(self):
        """FHKST01010400 (현재가 분봉) 파라미터 빌딩"""
        client = KISClient(app_key="test", app_secret="test")
        
        # 1. symbol 키 사용
        params = client._build_request_body("FHKST01010400", {
            "symbol": "005930"
        })
        
        assert params["FID_COND_MRKT_DIV_CODE"] == "J"
        assert params["FID_INPUT_ISCD"] == "005930"
        
        # 2. FID_INPUT_ISCD 직접 사용
        params = client._build_request_body("FHKST01010400", {
            "FID_INPUT_ISCD": "000660"
        })
        
        assert params["FID_INPUT_ISCD"] == "000660"

    def test_build_fhkst03010200_params(self):
        """FHKST03010200 (기간별 분봉) 파라미터 빌딩"""
        client = KISClient(app_key="test", app_secret="test")
        
        # 1. 간단한 파라미터
        params = client._build_request_body("FHKST03010200", {
            "symbol": "005930",
            "time": "150000"
        })
        
        assert params["fid_cond_mrkt_div_code"] == "J"
        assert params["fid_input_iscd"] == "005930"
        assert params["fid_input_hour_1"] == "150000"
        assert params["fid_pw_data_incu_yn"] == "Y"
        assert params["fid_etc_cls_code"] == ""
        
        # 2. 전체 파라미터
        params = client._build_request_body("FHKST03010200", {
            "fid_input_iscd": "035420",
            "fid_input_hour_1": "093000",
            "fid_pw_data_incu_yn": "N"
        })
        
        assert params["fid_input_iscd"] == "035420"
        assert params["fid_input_hour_1"] == "093000"
        assert params["fid_pw_data_incu_yn"] == "N"

    def test_build_hhdfs76950200_params(self):
        """HHDFS76950200 (해외주식 분봉) 파라미터 빌딩"""
        client = KISClient(app_key="test", app_secret="test")
        
        # 1. 간단한 파라미터
        params = client._build_request_body("HHDFS76950200", {
            "symbol": "AAPL",
            "EXCD": "NAS",
            "BYMD": "20260101"
        })
        
        assert params["EXCD"] == "NAS"
        assert params["SYMB"] == "AAPL"
        assert params["BYMD"] == "20260101"
        assert params["GUBN"] == "0"
        assert params["MODP"] == "1"
        assert params["AUTH"] == ""
        
        # 2. SYMB 직접 사용
        params = client._build_request_body("HHDFS76950200", {
            "SYMB": "TSLA",
            "EXCD": "NYS",
            "BYMD": "20260120"
        })
        
        assert params["SYMB"] == "TSLA"
        assert params["EXCD"] == "NYS"

    def test_unknown_tr_id_returns_params_as_is(self):
        """알 수 없는 TR ID는 params를 그대로 반환"""
        client = KISClient(app_key="test", app_secret="test")
        
        params = client._build_request_body("UNKNOWN_TR_ID", {
            "key1": "value1",
            "key2": "value2"
        })
        
        assert params == {"key1": "value1", "key2": "value2"}


class TestHeaderBuilding:
    """헤더 빌딩 테스트"""

    def test_build_headers(self):
        """KIS API 헤더 빌딩"""
        client = KISClient(app_key="test_key", app_secret="test_secret")
        client._access_token = "test_token"
        
        headers = client._build_headers("FHKST01010100")
        
        assert headers["authorization"] == "Bearer test_token"
        assert headers["appkey"] == "test_key"
        assert headers["appsecret"] == "test_secret"
        assert headers["tr_id"] == "FHKST01010100"
        assert headers["custtype"] == "P"
        assert headers["Content-Type"] == "application/json; charset=utf-8"


class TestMethodSelection:
    """HTTP Method 자동 선택 테스트"""

    def test_get_trs_set(self):
        """GET_TRS 세트에 모든 구현된 TR ID가 포함되어 있는지 확인"""
        client = KISClient(app_key="test", app_secret="test")
        
        expected_get_trs = {
            "FHKST01010100",
            "FHKST01010300",
            "FHKST01010400",
            "FHKST01010900",  # Pillar 8: 주식현재가 투자자
            "FHKST03010200",
            "HHDFS76950200"
        }
        
        assert client.GET_TRS == expected_get_trs


class TestTRRegistryIntegration:
    """TR Registry와의 통합 테스트"""

    def test_all_implemented_kis_tr_ids_in_url_map(self):
        """TR Registry에서 구현 완료로 표시된 모든 KIS TR ID가 URL_MAP에 있는지 확인"""
        from src.api_gateway.hub.tr_registry import list_tr_ids, Provider
        
        client = KISClient(app_key="test", app_secret="test")
        
        kis_implemented = [
            s.tr_id for s in list_tr_ids(provider=Provider.KIS, implemented_only=True)
        ]
        
        for tr_id in kis_implemented:
            assert tr_id in client.TR_URL_MAP, \
                f"Implemented TR ID {tr_id} not in KISClient.TR_URL_MAP"

    def test_all_implemented_kis_tr_ids_in_get_trs(self):
        """TR Registry의 모든 KIS TR ID가 GET_TRS에 있는지 확인 (GET method)"""
        from src.api_gateway.hub.tr_registry import list_tr_ids, Provider
        
        client = KISClient(app_key="test", app_secret="test")
        
        kis_implemented = [
            s for s in list_tr_ids(provider=Provider.KIS, implemented_only=True)
        ]
        
        for spec in kis_implemented:
            if spec.method == "GET":
                assert spec.tr_id in client.GET_TRS, \
                    f"GET TR ID {spec.tr_id} not in KISClient.GET_TRS"

    def test_tr_registry_endpoints_match_url_map(self):
        """TR Registry의 endpoint와 KISClient URL_MAP이 일치하는지 확인"""
        from src.api_gateway.hub.tr_registry import get_tr_spec
        
        client = KISClient(app_key="test", app_secret="test")
        
        for tr_id, url in client.TR_URL_MAP.items():
            spec = get_tr_spec(tr_id)
            if spec:  # TR Registry에 있는 TR ID만 확인
                assert spec.endpoint == url, \
                    f"TR ID {tr_id}: Registry endpoint {spec.endpoint} != URL_MAP {url}"
