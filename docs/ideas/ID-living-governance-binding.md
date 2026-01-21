# IDEA: Living Governance (Constitution-Workflow Binding)
**Status**: 🌿 Sprouting (Drafting)
**Priority**: P1

## 1. 개요 (Abstract)
- **Problem**: 거버넌스 원칙(`ai-rules.md`), 실행 도구(`.agent/workflows/`), 그리고 기록물(`docs/governance/`)이 물리적으로 분리되어 있어, 원칙이 실제 작업에 강제되지 않거나 워크플로우 결과가 문서에 자동으로 반영되지 않는 "Governance Gap" 발생.
- **Opportunity**: 원칙과 실행을 유기적으로 결합하여 AI 에이전트가 별도의 판단 없이 원칙에 따라 워크플로우를 호출하고 결과를 아카이빙하는 자동화된 통치(Living Governance) 체계 구축.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- [가설] `ai-rules.md`의 각 원칙에 대응하는 `Workflow ID`를 명시하고, 워크플로우 실행 시 관련 문서를 자동으로 업데이트하도록 하면 거버넌스 준수율이 100%에 수렴할 것이다.
- [기대 효과] 수동 Gap Analysis 비용 전면 제거, SSoT의 실시간 무결성 보장.

## 3. 구체화 세션 (Elaboration)
### 3.1. Unified Governance Architecture (3-Layer)
1.  **Constitutional Layer (`.ai-rules.md`)**: 최상위 원칙 및 워크플로우 호출 트리거 정의.
    - 예: "모든 아키텍처 변경은 `@/council-review`를 거쳐야 한다."
2.  **Executive Layer (`.agent/workflows/*.md`)**: 원칙을 실현하는 구체적인 행동 매뉴얼.
    - 예: `/council-review` 실행 시 `implementation_plan.md`에 페르소나 의견 자동 기록.
3.  **Judicial/Record Layer (`docs/governance/`, `HISTORY.md`)**: 실행 결과 및 의사결정 이력 보존.
    - 예: `HISTORY.md`에 모든 헌법 개정 및 주요 결정 사항 자동 인덱싱.

### 3.2. 핵심 바인딩(Binding) 전략
- **Workflow-driven Documentation**: 모든 워크플로우는 완료 시 `docs/README.md` 또는 관련 인덱스 문서를 자동으로 업데이트해야 함.
- **Rule-to-Workflow Mapping**: `ai-rules.md` 내에 각 규칙을 검증하거나 실행할 수 있는 슬래시 커맨드(`@/command`)를 태그 형태로 삽입.

## 4. 로드맵 연동 시나리오
- **Pillar**: SDLC & Governance Automation
- **Target**: 단계적 `ai-rules.md` 리팩토링을 통해 규칙마다 실행 가능한 워크플로우를 매핑 (Phase 8의 핵심 과제로 승격).
