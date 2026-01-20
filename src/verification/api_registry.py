"""
API Target Registry for Verification System
============================================
RFC-008 Appendix E.3 구현

KIS/Kiwoom API 엔드포인트를 중앙 관리하여 듀얼 검증 및 Failover를 지원한다.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
import yaml
import os


class APIProvider(Enum):
    """API 제공자"""
    KIS = "kis"
    KIWOOM = "kiwoom"


class APIEndpointType(Enum):
    """API 엔드포인트 유형"""
    MINUTE_CANDLE = "minute_candle"   # 분봉 조회
    TICK_HISTORY = "tick_history"     # 틱 히스토리
    CURRENT_PRICE = "current_price"   # 현재가


@dataclass
class APITarget:
    """
    API 엔드포인트 타겟 정의

    Attributes:
        provider: API 제공자 (KIS/Kiwoom)
        endpoint_type: 엔드포인트 유형
        tr_id: TR ID (예: FHKST03010200, ka10080)
        path: API 경로
        method: HTTP Method (GET/POST)
        rate_limit_key: Rate Limiter에서 사용할 키
        calls_per_second: 초당 호출 제한
        response_mapping: 응답 필드 매핑
        enabled: 활성화 여부
        priority: 우선순위 (낮을수록 우선)
    """
    provider: APIProvider
    endpoint_type: APIEndpointType
    tr_id: str
    path: str = ""
    method: str = "GET"
    rate_limit_key: str = ""
    calls_per_second: int = 30
    burst_limit: int = 5
    request_template: Dict[str, Any] = field(default_factory=dict)
    response_mapping: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 1
    timeout_sec: float = 10.0

    def __post_init__(self):
        if not self.rate_limit_key:
            self.rate_limit_key = self.provider.value.upper()


class APITargetRegistry:
    """
    API 타겟 중앙 관리 레지스트리

    Usage:
        registry = APITargetRegistry()

        # 특정 provider의 타겟 조회
        kis_minute = registry.get_target(APIEndpointType.MINUTE_CANDLE, APIProvider.KIS)

        # 듀얼 검증용 모든 타겟 조회
        all_minute_targets = registry.get_all_targets(APIEndpointType.MINUTE_CANDLE)
    """

    def __init__(self, config_path: Optional[str] = None):
        self._targets: Dict[tuple, List[APITarget]] = {}
        self._load_default_targets()

        if config_path and os.path.exists(config_path):
            self._load_from_yaml(config_path)

    def _load_default_targets(self):
        """기본 API 타겟 로드 (RFC-008 Appendix F 기반)"""

        # === KIS API Targets ===

        # KIS 분봉 API (검증용)
        self.register(APITarget(
            provider=APIProvider.KIS,
            endpoint_type=APIEndpointType.MINUTE_CANDLE,
            tr_id="FHKST03010200",
            path="/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
            method="GET",
            priority=2,  # Kiwoom보다 낮은 우선순위 (VTS 제한)
            response_mapping={
                "open": "stck_oprc",
                "high": "stck_hgpr",
                "low": "stck_lwpr",
                "close": "stck_prpr",
                "volume": "cntg_vol",
                "timestamp": "stck_bsop_date"
            }
        ))

        # KIS 틱 히스토리 API (복구용) - VTS에서 Empty 반환으로 disabled
        self.register(APITarget(
            provider=APIProvider.KIS,
            endpoint_type=APIEndpointType.TICK_HISTORY,
            tr_id="FHKST01010300",
            path="/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion",
            method="GET",
            priority=2,
            enabled=False,  # VTS 환경에서 Empty 반환 확인됨
            response_mapping={
                "price": "stck_prpr",
                "volume": "cntg_vol",
                "timestamp": "stck_cntg_hour"
            }
        ))

        # === Kiwoom API Targets ===

        # Kiwoom 분봉 API (검증용) - Production Ready
        self.register(APITarget(
            provider=APIProvider.KIWOOM,
            endpoint_type=APIEndpointType.MINUTE_CANDLE,
            tr_id="ka10080",
            path="/api/dostk/chart",
            method="POST",
            priority=1,  # Primary (Production Ready 확인됨)
            request_template={
                "stk_cd": "{symbol}",
                "chart_type": "1"  # 1분봉
            },
            response_mapping={
                "open": "open_pr",
                "high": "high_pr",
                "low": "low_pr",
                "close": "close_pr",
                "volume": "trde_qty",
                "timestamp": "dt",
                # 실제 응답 필드명 (collector_kiwoom.py에서 확인)
                "data_key": "stk_min_pole_chart_qry"
            }
        ))

        # Kiwoom 틱 차트 API (복구용) - Rate Limited
        self.register(APITarget(
            provider=APIProvider.KIWOOM,
            endpoint_type=APIEndpointType.TICK_HISTORY,
            tr_id="ka10079",
            path="/api/dostk/chart",
            method="POST",
            priority=1,
            calls_per_second=10,  # Rate Limit 빈번 발생으로 낮춤
            request_template={
                "stk_cd": "{symbol}",
                "tic_scope": "1",
                "upd_stkpc_tp": "0"
            },
            response_mapping={
                "price": "price",
                "volume": "volume",
                "timestamp": "time",
                "data_key": "stk_tic_chart_qry"
            }
        ))

    def _load_from_yaml(self, config_path: str):
        """YAML 설정 파일에서 타겟 로드"""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        for provider_name, endpoints in config.get('targets', {}).items():
            provider = APIProvider(provider_name.lower())

            for endpoint_name, settings in endpoints.items():
                endpoint_type = APIEndpointType(endpoint_name)

                target = APITarget(
                    provider=provider,
                    endpoint_type=endpoint_type,
                    tr_id=settings.get('tr_id', ''),
                    path=settings.get('path', ''),
                    method=settings.get('method', 'GET'),
                    priority=settings.get('priority', 1),
                    enabled=settings.get('enabled', True),
                    calls_per_second=settings.get('rate_limit', {}).get('calls_per_second', 30),
                    burst_limit=settings.get('rate_limit', {}).get('burst', 5)
                )
                self.register(target)

    def register(self, target: APITarget) -> None:
        """타겟 등록"""
        key = (target.provider, target.endpoint_type)
        if key not in self._targets:
            self._targets[key] = []

        # 중복 제거 (동일 tr_id)
        self._targets[key] = [t for t in self._targets[key] if t.tr_id != target.tr_id]
        self._targets[key].append(target)

        # 우선순위 정렬
        self._targets[key].sort(key=lambda t: t.priority)

    def get_target(
        self,
        endpoint_type: APIEndpointType,
        provider: Optional[APIProvider] = None
    ) -> Optional[APITarget]:
        """
        타겟 조회

        Args:
            endpoint_type: 엔드포인트 유형
            provider: API 제공자 (None이면 우선순위 기반 선택)

        Returns:
            APITarget 또는 None
        """
        if provider:
            key = (provider, endpoint_type)
            targets = self._targets.get(key, [])
            enabled_targets = [t for t in targets if t.enabled]
            return enabled_targets[0] if enabled_targets else None

        # 모든 provider에서 enabled && 최우선순위 선택
        all_targets = []
        for (p, e), targets in self._targets.items():
            if e == endpoint_type:
                all_targets.extend([t for t in targets if t.enabled])

        all_targets.sort(key=lambda t: t.priority)
        return all_targets[0] if all_targets else None

    def get_all_targets(self, endpoint_type: APIEndpointType) -> List[APITarget]:
        """
        특정 타입의 모든 활성화된 타겟 조회 (듀얼 검증용)

        Args:
            endpoint_type: 엔드포인트 유형

        Returns:
            활성화된 APITarget 리스트 (우선순위 순)
        """
        result = []
        for (p, e), targets in self._targets.items():
            if e == endpoint_type:
                result.extend([t for t in targets if t.enabled])
        return sorted(result, key=lambda t: t.priority)

    def get_providers(self, endpoint_type: APIEndpointType) -> List[APIProvider]:
        """특정 엔드포인트 타입을 지원하는 모든 Provider 조회"""
        providers = set()
        for (p, e), targets in self._targets.items():
            if e == endpoint_type:
                enabled = [t for t in targets if t.enabled]
                if enabled:
                    providers.add(p)
        return list(providers)

    def disable_target(self, provider: APIProvider, endpoint_type: APIEndpointType) -> bool:
        """특정 타겟 비활성화 (Failover 시 사용)"""
        key = (provider, endpoint_type)
        targets = self._targets.get(key, [])
        for target in targets:
            target.enabled = False
        return len(targets) > 0

    def enable_target(self, provider: APIProvider, endpoint_type: APIEndpointType) -> bool:
        """특정 타겟 활성화"""
        key = (provider, endpoint_type)
        targets = self._targets.get(key, [])
        for target in targets:
            target.enabled = True
        return len(targets) > 0


# 글로벌 레지스트리 인스턴스
api_registry = APITargetRegistry()
