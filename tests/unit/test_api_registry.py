"""
API Target Registry 단위 테스트
===============================
RFC-008 Appendix F TC-F001~F006
"""
import pytest
from src.verification.api_registry import (
    APITargetRegistry,
    APITarget,
    APIProvider,
    APIEndpointType
)


class TestAPITargetRegistry:
    """API Target Registry 단위 테스트"""

    @pytest.fixture
    def registry(self):
        """새 레지스트리 인스턴스"""
        return APITargetRegistry()

    # TC-F001: 기본 타겟 로드 확인
    def test_default_targets_loaded(self, registry):
        """기본 KIS/Kiwoom 타겟이 로드되어야 함"""
        # Kiwoom 분봉 (Primary)
        kiwoom_minute = registry.get_target(
            APIEndpointType.MINUTE_CANDLE,
            APIProvider.KIWOOM
        )
        assert kiwoom_minute is not None
        assert kiwoom_minute.tr_id == "ka10080"
        assert kiwoom_minute.priority == 1  # Primary

        # KIS 분봉 (Secondary)
        kis_minute = registry.get_target(
            APIEndpointType.MINUTE_CANDLE,
            APIProvider.KIS
        )
        assert kis_minute is not None
        assert kis_minute.tr_id == "FHKST03010200"
        assert kis_minute.priority == 2  # Secondary

    # TC-F002: 틱 히스토리 타겟 확인
    def test_tick_history_targets(self, registry):
        """틱 히스토리 타겟 검증"""
        # Kiwoom 틱 (enabled)
        kiwoom_tick = registry.get_target(
            APIEndpointType.TICK_HISTORY,
            APIProvider.KIWOOM
        )
        assert kiwoom_tick is not None
        assert kiwoom_tick.tr_id == "ka10079"
        assert kiwoom_tick.enabled is True

        # KIS 틱 (disabled - VTS에서 Empty 반환)
        kis_tick = registry.get_target(
            APIEndpointType.TICK_HISTORY,
            APIProvider.KIS
        )
        # disabled이므로 None 반환
        assert kis_tick is None

    # TC-F003: 우선순위 기반 선택
    def test_priority_based_selection(self, registry):
        """provider 미지정 시 우선순위 기반 선택"""
        # 분봉은 Kiwoom이 priority 1 (Primary)
        target = registry.get_target(APIEndpointType.MINUTE_CANDLE)
        assert target is not None
        assert target.provider == APIProvider.KIWOOM
        assert target.priority == 1

    # TC-F004: 듀얼 타겟 조회
    def test_get_all_targets_for_dual_verification(self, registry):
        """듀얼 검증용 전체 타겟 조회"""
        targets = registry.get_all_targets(APIEndpointType.MINUTE_CANDLE)

        # 최소 2개 (KIS, Kiwoom)
        assert len(targets) >= 2

        providers = [t.provider for t in targets]
        assert APIProvider.KIS in providers
        assert APIProvider.KIWOOM in providers

        # 우선순위 순서 확인 (Kiwoom first)
        assert targets[0].provider == APIProvider.KIWOOM

    # TC-F005: 비활성화 타겟 필터링
    def test_disabled_target_filtered(self, registry):
        """enabled=False 타겟은 get_target에서 제외"""
        # KIS 틱은 disabled
        kis_tick = registry.get_target(
            APIEndpointType.TICK_HISTORY,
            APIProvider.KIS
        )
        assert kis_tick is None

        # get_all_targets에서도 제외
        all_tick_targets = registry.get_all_targets(APIEndpointType.TICK_HISTORY)
        kis_targets = [t for t in all_tick_targets if t.provider == APIProvider.KIS]
        assert len(kis_targets) == 0

    # TC-F006: 커스텀 타겟 등록
    def test_custom_target_registration(self, registry):
        """새 타겟 등록 기능"""
        custom = APITarget(
            provider=APIProvider.KIS,
            endpoint_type=APIEndpointType.CURRENT_PRICE,
            tr_id="FHKST01010100",
            path="/uapi/domestic-stock/v1/quotations/inquire-price",
            enabled=True,
            priority=1
        )
        registry.register(custom)

        # 등록 확인
        target = registry.get_target(
            APIEndpointType.CURRENT_PRICE,
            APIProvider.KIS
        )
        assert target is not None
        assert target.tr_id == "FHKST01010100"

    # TC-F007: 타겟 비활성화/활성화
    def test_disable_enable_target(self, registry):
        """타겟 동적 비활성화/활성화"""
        # 초기 상태: Kiwoom 분봉 활성화
        target = registry.get_target(
            APIEndpointType.MINUTE_CANDLE,
            APIProvider.KIWOOM
        )
        assert target is not None

        # 비활성화
        result = registry.disable_target(
            APIProvider.KIWOOM,
            APIEndpointType.MINUTE_CANDLE
        )
        assert result is True

        # 비활성화 후 조회
        target = registry.get_target(
            APIEndpointType.MINUTE_CANDLE,
            APIProvider.KIWOOM
        )
        assert target is None

        # 재활성화
        registry.enable_target(
            APIProvider.KIWOOM,
            APIEndpointType.MINUTE_CANDLE
        )
        target = registry.get_target(
            APIEndpointType.MINUTE_CANDLE,
            APIProvider.KIWOOM
        )
        assert target is not None

    # TC-F008: Rate Limit Key 자동 설정
    def test_rate_limit_key_auto_set(self, registry):
        """rate_limit_key 미지정 시 provider.upper()로 자동 설정"""
        target = registry.get_target(
            APIEndpointType.MINUTE_CANDLE,
            APIProvider.KIWOOM
        )
        assert target.rate_limit_key == "KIWOOM"

        target = registry.get_target(
            APIEndpointType.MINUTE_CANDLE,
            APIProvider.KIS
        )
        assert target.rate_limit_key == "KIS"

    # TC-F009: Response Mapping 확인
    def test_response_mapping(self, registry):
        """응답 필드 매핑 확인"""
        kiwoom = registry.get_target(
            APIEndpointType.MINUTE_CANDLE,
            APIProvider.KIWOOM
        )
        assert "volume" in kiwoom.response_mapping
        assert kiwoom.response_mapping["volume"] == "trde_qty"
        assert kiwoom.response_mapping.get("data_key") == "stk_min_pole_chart_qry"

    # TC-F010: Provider 목록 조회
    def test_get_providers(self, registry):
        """특정 엔드포인트 타입 지원 Provider 조회"""
        providers = registry.get_providers(APIEndpointType.MINUTE_CANDLE)
        assert APIProvider.KIS in providers
        assert APIProvider.KIWOOM in providers

        # 틱 히스토리는 Kiwoom만 (KIS disabled)
        tick_providers = registry.get_providers(APIEndpointType.TICK_HISTORY)
        assert APIProvider.KIWOOM in tick_providers
        assert APIProvider.KIS not in tick_providers
