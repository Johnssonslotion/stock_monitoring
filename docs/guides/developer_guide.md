# API Hub v2 - 개발자 가이드

API Hub v2 개발과 관련된 모든 가이드와 템플릿을 모아놓은 문서입니다.

---

## 📚 문서 목차

### 1. 개요 및 아키텍처
- [API Hub v2 Overview](../specs/api_hub_v2_overview.md) - 전체 아키텍처 및 설계
- [Ground Truth Policy](../governance/ground_truth_policy.md) - TR ID 및 문서 정책
- [API Hub Migration Guide](./api_hub_migration_guide.md) - 기존 시스템 마이그레이션

### 2. TR ID 관리
- [TR Registry 소스코드](../../src/api_gateway/hub/tr_registry.py) - 중앙화된 TR ID 레지스트리
- [KIS TR ID Reference](../specs/api_reference/kis_tr_id_reference.md) - 한국투자증권 TR ID 목록
- [Kiwoom TR ID Reference](../specs/api_reference/kiwoom_tr_id_reference.md) - 키움증권 API ID 목록

### 3. 구현 가이드
- [Container Migration Guide](./container_migration_guide.md) - 컨테이너 통합 가이드
- [API Schema Discovery Guide](../operations/testing/api_schema_discovery_guide.md) - API 스키마 자동 수집

---

## 🛠️ TR ID 추가 템플릿

새로운 TR ID를 추가할 때 사용하는 단계별 가이드입니다.

### KIS TR ID 추가
**파일**: [docs/templates/add_kis_tr_id.md](../templates/add_kis_tr_id.md)

**대상**: 한국투자증권(KIS) REST API의 새 TR ID 추가

**포함 내용**:
- ✅ 사전 조사 체크리스트
- ✅ TR Registry 등록 방법
- ✅ KISClient 구현 가이드
- ✅ 테스트 작성 가이드
- ✅ 문서화 방법
- ✅ 커밋 예제

**사용 시나리오**:
```bash
# 1. 템플릿 읽기
cat docs/templates/add_kis_tr_id.md

# 2. 새 TR ID 추가 (예: FHKST01010500)
# - src/api_gateway/hub/tr_registry.py 수정
# - src/api_gateway/hub/clients/kis_client.py 수정
# - tests/unit/api_gateway/test_kis_client.py 수정
# - docs/specs/api_reference/kis_tr_id_reference.md 수정

# 3. 테스트 실행
PYTHONPATH=. poetry run pytest tests/unit/api_gateway/test_kis_client.py -v

# 4. 커밋
git add -A
git commit -m "feat(api-hub): add KIS TR ID FHKST01010500 (description)"
```

---

### Kiwoom API ID 추가
**파일**: [docs/templates/add_kiwoom_api_id.md](../templates/add_kiwoom_api_id.md)

**대상**: 키움증권(Kiwoom) REST API의 새 API ID 추가

**포함 내용**:
- ✅ 사전 조사 체크리스트 (REST API ID + OpenAPI+ TR ID)
- ✅ TR Registry 등록 방법
- ✅ KiwoomClient 구현 가이드
- ✅ OpenAPI+ 매핑 가이드
- ✅ 테스트 작성 가이드
- ✅ 문서화 방법
- ✅ 커밋 예제

**사용 시나리오**:
```bash
# 1. 템플릿 읽기
cat docs/templates/add_kiwoom_api_id.md

# 2. 새 API ID 추가 (예: ka10082)
# - src/api_gateway/hub/tr_registry.py 수정
# - src/api_gateway/hub/clients/kiwoom_client.py 수정
# - tests/unit/api_gateway/test_kiwoom_client.py 수정
# - docs/specs/api_reference/kiwoom_tr_id_reference.md 수정

# 3. 테스트 실행
PYTHONPATH=. poetry run pytest tests/unit/api_gateway/test_kiwoom_client.py -v

# 4. 커밋
git add -A
git commit -m "feat(api-hub): add Kiwoom API ID ka10082 (description)"
```

---

### 통합 템플릿 (레거시)
**파일**: [docs/templates/tr_id_addition_template.md](../templates/tr_id_addition_template.md)

KIS와 Kiwoom 모두를 포함하는 통합 템플릿입니다. 특정 provider에 집중하려면 위의 개별 템플릿 사용을 권장합니다.

---

## 📋 빠른 참조

### TR ID 네이밍 규칙
| Provider | 형식 | 예시 | 설명 |
|----------|------|------|------|
| KIS | 대문자 영숫자 10+ 글자 | `FHKST01010100` | 한국투자증권 TR ID |
| Kiwoom | `ka` + 5자리 숫자 | `ka10080` | 키움증권 REST API ID |

### 주요 파일 위치
```
stock_monitoring/
├── src/api_gateway/hub/
│   ├── tr_registry.py              # TR ID 레지스트리 (Ground Truth)
│   └── clients/
│       ├── kis_client.py           # KIS API 클라이언트
│       └── kiwoom_client.py        # Kiwoom API 클라이언트
├── tests/unit/api_gateway/
│   ├── test_tr_registry.py         # TR Registry 테스트
│   ├── test_kis_client.py          # KISClient 테스트
│   └── test_kiwoom_client.py       # KiwoomClient 테스트
└── docs/
    ├── specs/api_reference/
    │   ├── kis_tr_id_reference.md       # KIS TR ID 목록
    │   └── kiwoom_tr_id_reference.md    # Kiwoom API ID 목록
    └── templates/
        ├── add_kis_tr_id.md             # KIS TR ID 추가 가이드
        └── add_kiwoom_api_id.md         # Kiwoom API ID 추가 가이드
```

### 테스트 실행 명령어
```bash
# TR Registry 테스트
PYTHONPATH=. poetry run pytest tests/unit/api_gateway/test_tr_registry.py -v

# KISClient 테스트
PYTHONPATH=. poetry run pytest tests/unit/api_gateway/test_kis_client.py -v

# KiwoomClient 테스트
PYTHONPATH=. poetry run pytest tests/unit/api_gateway/test_kiwoom_client.py -v

# 전체 API Gateway 테스트
PYTHONPATH=. poetry run pytest tests/unit/api_gateway/ -v
```

### Implementation Stats 확인
```python
from src.api_gateway.hub.tr_registry import get_implementation_stats

stats = get_implementation_stats()
print(f"Overall: {stats['implemented']}/{stats['total']} ({stats['completion_rate']*100:.1f}%)")
print(f"KIS: {stats['by_provider']['KIS']['implemented']}/{stats['by_provider']['KIS']['total']}")
print(f"Kiwoom: {stats['by_provider']['KIWOOM']['implemented']}/{stats['by_provider']['KIWOOM']['total']}")
```

---

## 🔍 TR ID 검색 및 조회

### TR ID 존재 여부 확인
```python
from src.api_gateway.hub.tr_registry import validate_tr_id

# TR ID 검증
is_valid = validate_tr_id("FHKST01010100")  # True
is_valid = validate_tr_id("INVALID_ID")     # False
```

### TR ID 스펙 조회
```python
from src.api_gateway.hub.tr_registry import get_tr_spec

spec = get_tr_spec("FHKST01010100")
print(f"Provider: {spec.provider}")
print(f"Endpoint: {spec.endpoint}")
print(f"Method: {spec.method}")
print(f"Implemented: {spec.implemented}")
```

### UseCase로 TR ID 찾기
```python
from src.api_gateway.hub.tr_registry import UseCase, get_tr_id_for_use_case

# KIS 분봉 TR ID
tr_id = get_tr_id_for_use_case(UseCase.MINUTE_CANDLE_KIS)  # "FHKST01010400"

# Kiwoom 분봉 API ID
tr_id = get_tr_id_for_use_case(UseCase.MINUTE_CANDLE_KIWOOM)  # "ka10080"
```

### 전체 TR ID 목록 조회
```python
from src.api_gateway.hub.tr_registry import list_tr_ids, Provider, TRCategory

# 전체 TR ID
all_specs = list_tr_ids()

# Provider별 필터
kis_specs = list_tr_ids(provider=Provider.KIS)
kiwoom_specs = list_tr_ids(provider=Provider.KIWOOM)

# 카테고리별 필터
candles = list_tr_ids(category=TRCategory.HISTORICAL_CANDLE)

# 구현 완료만
implemented = list_tr_ids(implemented_only=True)
```

---

## 🎯 실전 예제

### 예제 1: KIS 일봉 TR ID 추가

```python
# 1. TR Registry 등록 (src/api_gateway/hub/tr_registry.py)
KIS_REGISTRY: Dict[str, TRIDSpec] = {
    # ...
    "FHKST03010100": TRIDSpec(
        tr_id="FHKST03010100",
        provider=Provider.KIS,
        category=TRCategory.HISTORICAL_CANDLE,
        description="국내주식 기간별 일봉 조회",
        endpoint="/uapi/domestic-stock/v1/quotations/inquire-daily-price",
        method="GET",
        implemented=True,
        priority="P0",
        documentation_url="https://apiportal.koreainvestment.com/..."
    ),
}

# 2. KISClient 구현 (src/api_gateway/hub/clients/kis_client.py)
TR_URL_MAP = {
    # ...
    "FHKST03010100": "/uapi/domestic-stock/v1/quotations/inquire-daily-price",
}

GET_TRS = {
    # ...
    "FHKST03010100",
}

def _build_request_body(self, tr_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    # FHKST03010100 (일봉 조회)
    if tr_id == "FHKST03010100":
        return {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": params.get("symbol") or params.get("FID_INPUT_ISCD"),
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "1",
        }
```

### 예제 2: Kiwoom 일봉 API ID 추가

```python
# 1. TR Registry 등록 (src/api_gateway/hub/tr_registry.py)
KIWOOM_REGISTRY: Dict[str, TRIDSpec] = {
    # ...
    "ka10081": TRIDSpec(
        tr_id="ka10081",
        provider=Provider.KIWOOM,
        category=TRCategory.HISTORICAL_CANDLE,
        description="국내주식 일봉 조회 (REST API)",
        endpoint="/api/dostk/chart",
        method="POST",
        implemented=True,
        priority="P0",
        documentation_url="https://apiportal.kiwoom.com"
    ),
}

# 2. KiwoomClient 구현 (src/api_gateway/hub/clients/kiwoom_client.py)
def _build_headers(self, tr_id: str, **kwargs) -> Dict[str, str]:
    api_id_map = {
        # ...
        "opt10081": "ka10081",  # OpenAPI+ 매핑
    }
    # ...

def _build_request_body(self, tr_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    # ka10081 (일봉 조회)
    if tr_id in ["ka10081", "opt10081"]:
        return {
            "stk_cd": params["symbol"],
            "inq_strt_dt": params.get("start_date", ""),
            "inq_end_dt": params.get("end_date", ""),
            "upd_stkpc_tp": "1",
        }
```

---

## 🚀 다음 단계

### 새 TR ID 추가 후
1. **테스트 실행**: 모든 단위 테스트 통과 확인
2. **문서 업데이트**: TR ID Reference 문서 업데이트
3. **Integration Test**: 실제 API 호출 검증 (선택)
4. **커밋**: 의미 있는 커밋 메시지와 함께 변경사항 커밋

### 실제 API 검증
```bash
# Schema Discovery 테스트 실행 (Gateway Worker 필요)
PYTHONPATH=. poetry run pytest tests/integration/test_api_schema_discovery.py::test_single_schema_kis_your_tr_id -v -s -m manual
```

### 배포
1. Pull Request 생성
2. 코드 리뷰
3. 병합 후 배포

---

## 📞 도움말

### 문제 해결
- **TR ID 형식 오류**: TR Registry validation 규칙 확인
- **테스트 실패**: 파라미터 매핑 및 endpoint 확인
- **API 호출 실패**: 공식 API 문서와 비교

### 참고 자료
- [KIS API Portal](https://apiportal.koreainvestment.com/)
- [Kiwoom API Portal](https://apiportal.kiwoom.com/)
- [ISSUE-041](../issues/ISSUE-041.md) - API Hub v2 구현 이슈

### 연락처
- GitHub Issues: 프로젝트 이슈 트래커
- 문서 위치: `docs/guides/developer_guide.md`

---

**Guide Version**: 1.0  
**Last Updated**: 2026-01-23  
**Maintainer**: Developer Team
