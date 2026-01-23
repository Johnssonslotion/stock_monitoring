"""
Unit Tests for TR Registry

TR Registry의 검증 및 기능 테스트
"""
import pytest

from src.api_gateway.hub.tr_registry import (
    Provider,
    TRCategory,
    TRIDSpec,
    UseCase,
    validate_tr_id,
    get_tr_spec,
    get_endpoint,
    get_tr_id_for_use_case,
    list_tr_ids,
    get_implementation_stats,
    KIS_REGISTRY,
    KIWOOM_REGISTRY,
    TR_REGISTRY,
)


class TestTRIDSpec:
    """TRIDSpec 데이터클래스 테스트"""

    def test_valid_kis_tr_id(self):
        """유효한 KIS TR ID 생성"""
        spec = TRIDSpec(
            tr_id="FHKST01010100",
            provider=Provider.KIS,
            category=TRCategory.HISTORICAL_CANDLE,
            description="Test TR ID",
            endpoint="/test/endpoint"
        )
        assert spec.tr_id == "FHKST01010100"
        assert spec.provider == Provider.KIS

    def test_valid_kiwoom_api_id(self):
        """유효한 Kiwoom API ID 생성"""
        spec = TRIDSpec(
            tr_id="ka10080",
            provider=Provider.KIWOOM,
            category=TRCategory.HISTORICAL_CANDLE,
            description="Test API ID",
            endpoint="/api/dostk/chart",
            method="POST"
        )
        assert spec.tr_id == "ka10080"
        assert spec.provider == Provider.KIWOOM

    def test_invalid_kis_tr_id_format(self):
        """잘못된 KIS TR ID 형식 - 소문자"""
        with pytest.raises(ValueError, match="Invalid KIS TR ID format"):
            TRIDSpec(
                tr_id="fhkst01010100",  # 소문자 (잘못됨)
                provider=Provider.KIS,
                category=TRCategory.HISTORICAL_CANDLE,
                description="Test",
                endpoint="/test"
            )

    def test_invalid_kis_tr_id_too_short(self):
        """잘못된 KIS TR ID 형식 - 너무 짧음"""
        with pytest.raises(ValueError, match="Invalid KIS TR ID format"):
            TRIDSpec(
                tr_id="FHKST",  # 너무 짧음
                provider=Provider.KIS,
                category=TRCategory.HISTORICAL_CANDLE,
                description="Test",
                endpoint="/test"
            )

    def test_invalid_kiwoom_api_id_format(self):
        """잘못된 Kiwoom API ID 형식"""
        with pytest.raises(ValueError, match="Invalid Kiwoom API ID format"):
            TRIDSpec(
                tr_id="KIS_CL_PBC_04020",  # 잘못된 형식
                provider=Provider.KIWOOM,
                category=TRCategory.HISTORICAL_CANDLE,
                description="Test",
                endpoint="/test"
            )

    def test_invalid_kiwoom_api_id_wrong_prefix(self):
        """잘못된 Kiwoom API ID - 잘못된 prefix"""
        with pytest.raises(ValueError, match="Invalid Kiwoom API ID format"):
            TRIDSpec(
                tr_id="opt10081",  # opt prefix는 OpenAPI+ (사용 금지)
                provider=Provider.KIWOOM,
                category=TRCategory.HISTORICAL_CANDLE,
                description="Test",
                endpoint="/test"
            )


class TestValidation:
    """TR ID 검증 함수 테스트"""

    def test_validate_existing_kis_tr_id(self):
        """존재하는 KIS TR ID 검증"""
        assert validate_tr_id("FHKST01010100") is True
        assert validate_tr_id("FHKST01010300") is True

    def test_validate_existing_kiwoom_api_id(self):
        """존재하는 Kiwoom API ID 검증"""
        assert validate_tr_id("ka10080") is True

    def test_validate_non_existing_tr_id(self):
        """존재하지 않는 TR ID 검증"""
        assert validate_tr_id("INVALID_ID") is False
        assert validate_tr_id("KIS_CL_PBC_04020") is False

    def test_validate_with_provider_filter(self):
        """Provider 필터로 TR ID 검증"""
        assert validate_tr_id("FHKST01010100", "KIS") is True
        assert validate_tr_id("ka10080", "KIWOOM") is True
        assert validate_tr_id("FHKST01010100", "KIWOOM") is False
        assert validate_tr_id("ka10080", "KIS") is False


class TestQuery:
    """TR ID 조회 함수 테스트"""

    def test_get_tr_spec(self):
        """TR ID 명세 조회"""
        spec = get_tr_spec("FHKST01010100")
        assert spec is not None
        assert spec.tr_id == "FHKST01010100"
        assert spec.provider == Provider.KIS
        assert spec.implemented is True

    def test_get_tr_spec_not_found(self):
        """존재하지 않는 TR ID 조회"""
        spec = get_tr_spec("INVALID_ID")
        assert spec is None

    def test_get_endpoint(self):
        """Endpoint 조회"""
        endpoint = get_endpoint("FHKST01010100")
        assert endpoint == "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"

        endpoint = get_endpoint("ka10080")
        assert endpoint == "/api/dostk/chart"

    def test_get_endpoint_not_found(self):
        """존재하지 않는 TR ID의 Endpoint 조회"""
        endpoint = get_endpoint("INVALID_ID")
        assert endpoint is None


class TestUseCaseMapping:
    """Use Case 매핑 테스트"""

    def test_get_tr_id_for_minute_candle_kis(self):
        """KIS 분봉 조회 Use Case"""
        tr_id = get_tr_id_for_use_case(UseCase.MINUTE_CANDLE_KIS)
        assert tr_id == "FHKST01010400"
        assert validate_tr_id(tr_id) is True

    def test_get_tr_id_for_minute_candle_kiwoom(self):
        """Kiwoom 분봉 조회 Use Case"""
        tr_id = get_tr_id_for_use_case(UseCase.MINUTE_CANDLE_KIWOOM)
        assert tr_id == "ka10080"
        assert validate_tr_id(tr_id) is True

    def test_get_tr_id_for_tick_data_kis(self):
        """KIS 틱 데이터 Use Case"""
        tr_id = get_tr_id_for_use_case(UseCase.TICK_DATA_KIS)
        assert tr_id == "FHKST01010300"
        assert validate_tr_id(tr_id) is True

    def test_get_tr_id_for_tick_data_kiwoom(self):
        """Kiwoom 틱 데이터 Use Case"""
        tr_id = get_tr_id_for_use_case(UseCase.TICK_DATA_KIWOOM)
        assert tr_id == "ka10079"
        assert validate_tr_id(tr_id) is True


class TestListFiltering:
    """TR ID 목록 필터링 테스트"""

    def test_list_all_tr_ids(self):
        """전체 TR ID 목록 조회"""
        all_specs = list_tr_ids()
        assert len(all_specs) == 7  # 5 KIS + 2 Kiwoom

    def test_list_kis_tr_ids(self):
        """KIS TR ID 목록 조회"""
        kis_specs = list_tr_ids(provider=Provider.KIS)
        assert len(kis_specs) == 5
        assert all(s.provider == Provider.KIS for s in kis_specs)

    def test_list_kiwoom_tr_ids(self):
        """Kiwoom API ID 목록 조회"""
        kiwoom_specs = list_tr_ids(provider=Provider.KIWOOM)
        assert len(kiwoom_specs) == 2
        assert all(s.provider == Provider.KIWOOM for s in kiwoom_specs)

    def test_list_implemented_only(self):
        """구현 완료된 TR ID만 조회"""
        implemented = list_tr_ids(implemented_only=True)
        assert len(implemented) == 7  # FHKST01010100, FHKST01010300, FHKST01010400, FHKST03010200, HHDFS76950200, ka10080, ka10079
        assert all(s.implemented is True for s in implemented)

    def test_list_by_category(self):
        """카테고리별 TR ID 조회"""
        candles = list_tr_ids(category=TRCategory.HISTORICAL_CANDLE)
        assert len(candles) >= 4
        assert all(s.category == TRCategory.HISTORICAL_CANDLE for s in candles)


class TestImplementationStats:
    """구현 통계 테스트"""

    def test_get_implementation_stats(self):
        """구현 통계 조회"""
        stats = get_implementation_stats()
        
        assert stats["total"] == 7
        assert stats["implemented"] == 7
        assert stats["pending"] == 0
        assert stats["completion_rate"] == pytest.approx(1.0)
        
        # Provider별 통계
        kis_stats = stats["by_provider"]["KIS"]
        assert kis_stats["total"] == 5
        assert kis_stats["implemented"] == 5
        assert kis_stats["completion_rate"] == pytest.approx(1.0)
        
        kiwoom_stats = stats["by_provider"]["KIWOOM"]
        assert kiwoom_stats["total"] == 2
        assert kiwoom_stats["implemented"] == 2
        assert kiwoom_stats["completion_rate"] == pytest.approx(1.0)


class TestRegistryIntegrity:
    """레지스트리 무결성 테스트"""

    def test_no_duplicate_tr_ids(self):
        """중복된 TR ID가 없는지 확인"""
        all_tr_ids = list(TR_REGISTRY.keys())
        assert len(all_tr_ids) == len(set(all_tr_ids))

    def test_all_kis_tr_ids_uppercase(self):
        """모든 KIS TR ID가 대문자인지 확인"""
        for tr_id, spec in KIS_REGISTRY.items():
            assert tr_id.isupper()
            assert spec.tr_id == tr_id

    def test_all_kiwoom_api_ids_start_with_ka(self):
        """모든 Kiwoom API ID가 'ka'로 시작하는지 확인"""
        for api_id, spec in KIWOOM_REGISTRY.items():
            assert api_id.startswith("ka")
            assert spec.tr_id == api_id

    def test_all_endpoints_are_valid(self):
        """모든 Endpoint가 유효한 경로인지 확인"""
        for spec in TR_REGISTRY.values():
            assert spec.endpoint.startswith("/")

    def test_all_use_cases_mapped(self):
        """모든 Use Case가 유효한 TR ID에 매핑되는지 확인"""
        for use_case in UseCase:
            tr_id = get_tr_id_for_use_case(use_case)
            assert validate_tr_id(tr_id) is True
            spec = get_tr_spec(tr_id)
            assert spec is not None


class TestDeprecatedSupport:
    """Legacy 지원 테스트 (Deprecated)"""

    def test_deprecated_api_tr_mapping_exists(self):
        """DEPRECATED_API_TR_MAPPING이 존재하는지 확인"""
        from src.api_gateway.hub.tr_registry import DEPRECATED_API_TR_MAPPING
        
        assert "KIS" in DEPRECATED_API_TR_MAPPING
        assert "KIWOOM" in DEPRECATED_API_TR_MAPPING
        assert DEPRECATED_API_TR_MAPPING["KIS"]["minute_candle"] == "FHKST01010400"
        assert DEPRECATED_API_TR_MAPPING["KIWOOM"]["minute_candle"] == "ka10080"

    def test_deprecated_function_warns(self):
        """get_legacy_tr_id()가 DeprecationWarning을 발생시키는지 확인"""
        from src.api_gateway.hub.tr_registry import get_legacy_tr_id
        
        with pytest.warns(DeprecationWarning):
            tr_id = get_legacy_tr_id("KIS", "minute_candle")
            assert tr_id == "FHKST01010400"


class TestBugFixes:
    """버그 수정 검증 테스트"""

    def test_kis_cl_pbc_04020_not_in_registry(self):
        """KIS_CL_PBC_04020이 레지스트리에 없는지 확인 (버그 수정 검증)"""
        assert "KIS_CL_PBC_04020" not in TR_REGISTRY
        assert validate_tr_id("KIS_CL_PBC_04020") is False

    def test_kiwoom_minute_candle_uses_ka10080(self):
        """Kiwoom 분봉 조회가 ka10080을 사용하는지 확인"""
        tr_id = get_tr_id_for_use_case(UseCase.MINUTE_CANDLE_KIWOOM)
        assert tr_id == "ka10080"
        assert tr_id != "KIS_CL_PBC_04020"
