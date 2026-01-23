# IDEA: 백로그 및 이연 작업 관리 체계 통합 (Unified Backlog Management)

**Status**: 🌿 Sprouting (Drafting)  
**Priority**: P1  
**Category**: Governance / Workflow

## 1. 개요 (Abstract)
현재 프로젝트는 **Tier 2 (BACKLOG.md, 단기)**와 **Deferred Work (deferred_work.md, 이연된 RFC/ADR)**를 분리하여 관리하고 있습니다. 사용자는 이 두 문서의 구분 필요성에 대해 의문을 제기하였으며, 이를 하나로 통합하여 관리 효율성을 높일 수 있는지 검토합니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
### 가설
- 백로그와 이연 작업을 하나의 SSoT(Single Source of Truth)로 통합하면, 작업의 우선순위 가시성이 확보되고 관리 포인트가 줄어들 것이다.
- `BACKLOG.md` 내에서 `Status` 필드(e.g., `DEFERRED`, `TODO`, `IN_PROGRESS`)를 통해 충분히 구분이 가능할 것이다.

### 기대 효과
- **관리 효율성**: 두 문서를 동시에 업데이트해야 하는 번거로움 해소.
- **가시성**: 전체 작업 목록을 한눈에 파악하여 리소스 배분 최적화.
- **단순화**: 거버넌스 규칙의 복잡도 감소.

## 3. 구조 비교 (Comparison)

| 구분 | 현행 (Separated) | 제안 (Unified) |
| :--- | :--- | :--- |
| **문서 수** | 2개 (`BACKLOG.md`, `deferred_work.md`) | 1개 (`BACKLOG.md`) |
| **Tier 구분** | 단출한 백로그 vs 상세한 이연 레지스트리 | 백로그 내 상세 정보 포함 또는 링크 |
| **복잡도** | 높음 (업데이트 시 두 곳 확인 필요) | 낮음 (하나의 파일만 관리) |
| **Risk** | 정보 파편화 (이연 작업 망각 위험) | 백로그 비대화 (단기 집중도 하락) |

## 4. 구체화 세션 (Initial Thoughts)
- **Problem**: `BACKLOG.md`가 너무 길어지면 "지금 당장 해야 할 일"이 흐려질 수 있음.
- **Solution**: `BACKLOG.md` 상단에 "Active Items"를 두고, 하단에 "Deferred / Future Backlog" 섹션을 두어 구분하는 방식 제안.

## 5. 로드맵 연동 시나리오
- 이 아이디어는 **Pillar 0 (Governance)**에 포함되며, 승인 시 `ai-rules.md` v2.18로 개정될 예정입니다.
