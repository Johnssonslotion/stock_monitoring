# IDEA: Governance-Issue Mapping Optimization
**Status**: 🌿 Sprouting (Drafting)
**Priority**: P2

## 1. 개요 (Abstract)
- **Problem**: `docs/governance/` 디렉토리에 이슈 관리 프로토콜, 과거 감사 기록, 개편 계획 등이 혼재되어 있어 거버넌스 폴더 본연의 '규정(Rule)' 성격이 희석됨. 
- **Opportunity**: 이슈 관련 문서를 `docs/issues/` (실행/전술)와 `docs/ARCHIVE/` (과거 기록)로 재배치하여 거버넌스 폴더를 핵심 규정 중심으로 슬림화함.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- [가설] 이슈 관리 방법론(Protocol)을 `docs/issues/` 폴더의 가이드로 이동하고, 과거 기록을 아카이브로 격리하면 이슈 관리의 응집도가 높아질 것이다.
- [기대 효과] 거버넌스 문서 탐색성 50% 향상, 이슈 관리 SSoT 강화.

## 3. 구체화 세션 (Elaboration)
### 3.1. 문서 재배치 매핑 (Mapping)
1.  **Issue Protocol (`issue_management_protocol.md`)**
    - **Current**: `docs/governance/`
    - **Target**: `docs/issues/` (이슈 관리의 실질적 가이드로 활용)
2.  **Historical Audit/Plan (`issue_rfc_audit_*.md`, `issue_reorganization_plan_*.md`)**
    - **Current**: `docs/governance/`
    - **Target**: `docs/ARCHIVE/issues/` (과거 이슈 구조 변경 이력으로 보존)
3.  **Governance Audits (`governance_audit_*.md`, `session_review_*.md`)**
    - **Current**: `docs/governance/`
    - **Target**: `docs/ARCHIVE/governance/` (과거 규정 준수 감사 이력)

### 3.2. Governance Core (남겨야 할 것)
- `ai-rules.md` (Root)
- `development.md`, `infrastructure.md`, `documentation_standard.md`, `personas.md`
- `HISTORY.md` (프로젝트 전체 이력)
- `decisions/` (ADR), `managed_policies.md`

## 4. 로드맵 연동 시나리오
- **Pillar**: Infrastructure & Maintenance (Phase 8: Living Governance)
- **Action**: `@/manage-docs`를 통한 폴더 클린업 2단계 완료.
