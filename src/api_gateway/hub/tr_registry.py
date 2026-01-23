"""
TR ID Registry - Ground Truth
==============================
API Hub v2에서 사용하는 모든 TR ID의 중앙화된 레지스트리.

모든 TR ID는 공식 API 문서에서 검증되어야 합니다.

Reference:
    - docs/specs/api_reference/kis_tr_id_reference.md
    - docs/specs/api_reference/kiwoom_tr_id_reference.md
    - docs/governance/ground_truth_policy.md Section 2.2

Version: 1.0
Last Updated: 2026-01-23
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Literal, Any, List


class Provider(str, Enum):
    """API Provider"""
    KIS = "KIS"
    KIWOOM = "KIWOOM"


class TRCategory(str, Enum):
    """TR ID 카테고리"""
    REALTIME_QUOTE = "REALTIME_QUOTE"      # 실시간 시세
    HISTORICAL_CANDLE = "HISTORICAL_CANDLE"  # 과거 분봉/일봉
    TICK_DATA = "TICK_DATA"                # 체결 데이터
    OVERSEAS = "OVERSEAS"                   # 해외주식


@dataclass(frozen=True)
class TRIDSpec:
    """
    TR ID 명세
    
    Attributes:
        tr_id: TR ID (KIS) or API ID (Kiwoom)
        provider: API Provider
        category: TR 카테고리
        description: 용도 설명
        endpoint: API Endpoint Path
        method: HTTP Method
        implemented: 구현 완료 여부
        priority: 우선순위 (P0=필수, P1=선택)
        documentation_url: 공식 문서 URL (선택)
    """
    tr_id: str
    provider: Provider
    category: TRCategory
    description: str
    endpoint: str
    method: Literal["GET", "POST"] = "GET"
    implemented: bool = False
    priority: Literal["P0", "P1", "P2"] = "P1"
    documentation_url: Optional[str] = None

    def __post_init__(self):
        """검증: TR ID 네이밍 규칙"""
        if self.provider == Provider.KIS:
            # KIS TR ID는 대문자 영숫자 조합
            if not self.tr_id.isupper() or len(self.tr_id) < 10:
                raise ValueError(
                    f"Invalid KIS TR ID format: {self.tr_id}. "
                    "Expected format: FHKST01010100 (uppercase, 10+ chars)"
                )
        elif self.provider == Provider.KIWOOM:
            # Kiwoom REST API ID는 'ka' + 5자리 숫자
            if not (self.tr_id.startswith("ka") and len(self.tr_id) == 7):
                raise ValueError(
                    f"Invalid Kiwoom API ID format: {self.tr_id}. "
                    "Expected format: ka10080 (ka + 5 digits)"
                )


# ============================================================================
# KIS TR ID Registry (Ground Truth)
# ============================================================================

KIS_REGISTRY: Dict[str, TRIDSpec] = {
    # === 구현 완료 ===
    "FHKST01010100": TRIDSpec(
        tr_id="FHKST01010100",
        provider=Provider.KIS,
        category=TRCategory.HISTORICAL_CANDLE,
        description="국내주식 시간별체결가 (분봉 조회)",
        endpoint="/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
        method="GET",
        implemented=True,
        priority="P0",
        documentation_url="https://apiportal.koreainvestment.com/apiservice/apiservice-domestic-stock-quotations"
    ),
    "FHKST01010300": TRIDSpec(
        tr_id="FHKST01010300",
        provider=Provider.KIS,
        category=TRCategory.TICK_DATA,
        description="국내주식 시간별체결 (틱 데이터)",
        endpoint="/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion",
        method="GET",
        implemented=True,
        priority="P0",
        documentation_url="https://apiportal.koreainvestment.com/apiservice/apiservice-domestic-stock-quotations"
    ),

    # === 구현 필요 (P0) ===
    "FHKST01010400": TRIDSpec(
        tr_id="FHKST01010400",
        provider=Provider.KIS,
        category=TRCategory.HISTORICAL_CANDLE,
        description="국내주식 현재가 분봉 조회",
        endpoint="/uapi/domestic-stock/v1/quotations/inquire-ccnl",
        method="GET",
        implemented=True,  # 2026-01-23 구현 완료
        priority="P0",
        documentation_url="https://apiportal.koreainvestment.com/apiservice/apiservice-domestic-stock-quotations"
    ),
    "FHKST03010200": TRIDSpec(
        tr_id="FHKST03010200",
        provider=Provider.KIS,
        category=TRCategory.HISTORICAL_CANDLE,
        description="국내주식 기간별 분봉 조회",
        endpoint="/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
        method="GET",
        implemented=True,  # 2026-01-23 구현 완료
        priority="P0",
        documentation_url="https://apiportal.koreainvestment.com/apiservice/apiservice-domestic-stock-quotations"
    ),

    # === 구현 필요 (P1) ===
    "HHDFS76950200": TRIDSpec(
        tr_id="HHDFS76950200",
        provider=Provider.KIS,
        category=TRCategory.OVERSEAS,
        description="해외주식 기간별 분봉 조회",
        endpoint="/uapi/overseas-price/v1/quotations/inquire-daily-chartprice",
        method="GET",
        implemented=True,  # 2026-01-23 구현 완료
        priority="P1",
        documentation_url="https://apiportal.koreainvestment.com/apiservice/apiservice-overseas-stock"
    ),
}


# ============================================================================
# Kiwoom API ID Registry (Ground Truth)
# ============================================================================

KIWOOM_REGISTRY: Dict[str, TRIDSpec] = {
    # === 구현 완료 ===
    "ka10080": TRIDSpec(
        tr_id="ka10080",
        provider=Provider.KIWOOM,
        category=TRCategory.HISTORICAL_CANDLE,
        description="국내주식 분봉 조회 (REST API)",
        endpoint="/api/dostk/chart",
        method="POST",
        implemented=True,
        priority="P0",
        documentation_url="https://apiportal.kiwoom.com"
    ),

    # === 구현 완료 ===
    "ka10079": TRIDSpec(
        tr_id="ka10079",
        provider=Provider.KIWOOM,
        category=TRCategory.TICK_DATA,
        description="국내주식 틱 조회 (REST API)",
        endpoint="/api/dostk/chart",
        method="POST",
        implemented=True,  # 2026-01-23 구현 완료 (KiwoomClient 이미 지원)
        priority="P1",
        documentation_url="https://apiportal.kiwoom.com"
    ),
}


# ============================================================================
# Unified Registry
# ============================================================================

TR_REGISTRY: Dict[str, TRIDSpec] = {
    **KIS_REGISTRY,
    **KIWOOM_REGISTRY,
}


# ============================================================================
# Validation Functions
# ============================================================================

def validate_tr_id(tr_id: str, provider: Optional[str] = None) -> bool:
    """
    TR ID 검증
    
    Args:
        tr_id: 검증할 TR ID
        provider: Provider 지정 (선택)
    
    Returns:
        True if valid, False otherwise
    
    Examples:
        >>> validate_tr_id("FHKST01010100")
        True
        >>> validate_tr_id("ka10080", "KIWOOM")
        True
        >>> validate_tr_id("INVALID_ID")
        False
    """
    if tr_id not in TR_REGISTRY:
        return False
    
    if provider:
        spec = TR_REGISTRY[tr_id]
        return spec.provider.value == provider
    
    return True


def get_tr_spec(tr_id: str) -> Optional[TRIDSpec]:
    """
    TR ID 명세 조회
    
    Args:
        tr_id: TR ID
    
    Returns:
        TRIDSpec if found, None otherwise
    
    Examples:
        >>> spec = get_tr_spec("FHKST01010100")
        >>> spec.description
        '국내주식 시간별체결가 (분봉 조회)'
    """
    return TR_REGISTRY.get(tr_id)


def get_endpoint(tr_id: str) -> Optional[str]:
    """
    TR ID에 대한 API Endpoint 조회
    
    Args:
        tr_id: TR ID
    
    Returns:
        Endpoint path if found, None otherwise
    
    Examples:
        >>> get_endpoint("FHKST01010100")
        '/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice'
    """
    spec = TR_REGISTRY.get(tr_id)
    return spec.endpoint if spec else None


def list_tr_ids(
    provider: Optional[Provider] = None,
    category: Optional[TRCategory] = None,
    implemented_only: bool = False
) -> list[TRIDSpec]:
    """
    TR ID 목록 조회 (필터링 지원)
    
    Args:
        provider: Provider 필터
        category: Category 필터
        implemented_only: 구현 완료된 것만 조회
    
    Returns:
        List of TRIDSpec
    
    Examples:
        >>> kis_specs = list_tr_ids(provider=Provider.KIS)
        >>> len(kis_specs)
        5
        >>> implemented = list_tr_ids(implemented_only=True)
        >>> len(implemented)
        3
    """
    specs = list(TR_REGISTRY.values())
    
    if provider:
        specs = [s for s in specs if s.provider == provider]
    
    if category:
        specs = [s for s in specs if s.category == category]
    
    if implemented_only:
        specs = [s for s in specs if s.implemented]
    
    return specs


def get_implementation_stats() -> Dict[str, Any]:
    """
    구현 통계 조회
    
    Returns:
        Dict with implementation statistics
    
    Examples:
        >>> stats = get_implementation_stats()
        >>> stats['completion_rate']
        0.42857142857142855  # 3/7
    """
    total = len(TR_REGISTRY)
    implemented = len([s for s in TR_REGISTRY.values() if s.implemented])
    
    kis_total = len(KIS_REGISTRY)
    kis_implemented = len([s for s in KIS_REGISTRY.values() if s.implemented])
    
    kiwoom_total = len(KIWOOM_REGISTRY)
    kiwoom_implemented = len([s for s in KIWOOM_REGISTRY.values() if s.implemented])
    
    return {
        "total": total,
        "implemented": implemented,
        "pending": total - implemented,
        "completion_rate": implemented / total if total > 0 else 0,
        "by_provider": {
            "KIS": {
                "total": kis_total,
                "implemented": kis_implemented,
                "completion_rate": kis_implemented / kis_total if kis_total > 0 else 0
            },
            "KIWOOM": {
                "total": kiwoom_total,
                "implemented": kiwoom_implemented,
                "completion_rate": kiwoom_implemented / kiwoom_total if kiwoom_total > 0 else 0
            }
        }
    }


# ============================================================================
# Semantic Mapping (Use Case → TR ID)
# ============================================================================

class UseCase(str, Enum):
    """API 사용 목적"""
    MINUTE_CANDLE_KIS = "MINUTE_CANDLE_KIS"
    MINUTE_CANDLE_KIWOOM = "MINUTE_CANDLE_KIWOOM"
    TICK_DATA_KIS = "TICK_DATA_KIS"
    TICK_DATA_KIWOOM = "TICK_DATA_KIWOOM"
    HISTORICAL_CANDLE_KIS = "HISTORICAL_CANDLE_KIS"
    OVERSEAS_CANDLE_KIS = "OVERSEAS_CANDLE_KIS"


# Use Case → TR ID 매핑
USE_CASE_MAPPING: Dict[UseCase, str] = {
    UseCase.MINUTE_CANDLE_KIS: "FHKST01010400",
    UseCase.MINUTE_CANDLE_KIWOOM: "ka10080",
    UseCase.TICK_DATA_KIS: "FHKST01010300",
    UseCase.TICK_DATA_KIWOOM: "ka10079",
    UseCase.HISTORICAL_CANDLE_KIS: "FHKST03010200",
    UseCase.OVERSEAS_CANDLE_KIS: "HHDFS76950200",
}


def get_tr_id_for_use_case(use_case: UseCase) -> str:
    """
    Use Case에 맞는 TR ID 조회
    
    Args:
        use_case: UseCase enum
    
    Returns:
        TR ID string
    
    Raises:
        ValueError: If use case not found
    
    Examples:
        >>> get_tr_id_for_use_case(UseCase.MINUTE_CANDLE_KIS)
        'FHKST01010400'
        >>> get_tr_id_for_use_case(UseCase.MINUTE_CANDLE_KIWOOM)
        'ka10080'
    """
    tr_id = USE_CASE_MAPPING.get(use_case)
    if not tr_id:
        raise ValueError(f"No TR ID mapped for use case: {use_case}")
    return tr_id


# ============================================================================
# Legacy Support (Deprecated)
# ============================================================================

# DEPRECATED: 하위 호환성을 위해 유지 (사용 금지)
# 대신 USE_CASE_MAPPING과 get_tr_id_for_use_case() 사용할 것
DEPRECATED_API_TR_MAPPING = {
    "KIS": {
        "minute_candle": "FHKST01010400",
        "tick_data": "FHKST01010300",
    },
    "KIWOOM": {
        "minute_candle": "ka10080",  # Fixed: 2026-01-23 (was KIS_CL_PBC_04020)
    }
}


def get_legacy_tr_id(provider: str, use_case: str) -> Optional[str]:
    """
    DEPRECATED: Legacy TR ID 조회 (하위 호환성 전용)
    
    Use get_tr_id_for_use_case() with UseCase enum instead.
    
    Args:
        provider: "KIS" or "KIWOOM"
        use_case: "minute_candle" or "tick_data"
    
    Returns:
        TR ID if found, None otherwise
    """
    import warnings
    warnings.warn(
        "get_legacy_tr_id() is deprecated. Use get_tr_id_for_use_case() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return DEPRECATED_API_TR_MAPPING.get(provider, {}).get(use_case)
