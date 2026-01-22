# 🏛️ Governance Index (거버넌스 및 규정)

본 문서는 프로젝트 운영 원칙, 의사결정 기록, 문서 표준을 관리하는 인덱스입니다.

## 1. 핵심 규정 (Core Regulations)
- **[ai-rules.md](../../.ai-rules.md)**: 최상위 절대 원칙 (Constitution, v2.17).
- **[Development Standard](development.md)**: 개발 가이드라인 및 품질 게이트.
- **[Infrastructure & DB](infrastructure.md)**: 인프라 물리 구조 및 DB 격리 규정.
- **[Documentation Standard](documentation_standard.md)**: RFC, ADR 등 문서 작성 규격.
- **[Ground Truth Policy](ground_truth_policy.md)**: 데이터 참값 정책 (REST API 분봉 = 참값, v2.16+).

## 2. 의사결정 및 이력 (Decisions & History)
- **[Governance History](HISTORY.md)**: 거버넌스 변경 이력 및 Constitution v2.x 로그.
- **[Decision Records (ADR)](decisions/)**: 주요 기술적 의사결정 모음.
  - **[ADR-010: Governance Sync Gate](decisions/010_governance_sync_gate.md)** (v2.17)
- **[RFC Records](rfc/)**: 기술 제안 및 표준화 기록.
- **[Deferred Work Registry](deferred_work.md)**: 승인되었으나 연기된 작업 목록.

## 3. RFC 목록 (Active RFCs)

| ID | Title | Status | Date | Link |
|:--:|-------|--------|------|------|
| RFC-001 | Single Socket Enforcement | Approved | 2026-01-17 | [Link](decisions/RFC-001_single_socket_enforcement.md) |
| RFC-002 | Strategy Spec Standard | Approved | 2026-01-17 | [Link](decisions/RFC-002_strategy_spec_standard.md) |
| RFC-003 | Config Management Standard | Approved | 2026-01-17 | [Link](decisions/RFC-003_config_management_standard.md) |
| RFC-004 | Dual AI Workflow Sync | Approved | 2026-01-17 | [Link](decisions/RFC-004_dual_ai_workflow_sync.md) |
| RFC-005 | Virtual Investment | Draft | 2026-01-17 | [Link](rfc/RFC-005-virtual-investment.md) |
| RFC-006 | Security & Governance | Approved | 2026-01-17 | [Link](rfc/RFC-006-security-governance.md) |
| RFC-007 | Collector Isolation | Approved | 2026-01-19 | [Link](rfc/RFC-007-collector-isolation.md) |
| RFC-008 | Tick Completeness QA | Implemented | 2026-01-20 | [Link](rfc/RFC-008-tick-completeness-qa.md) |
| **RFC-009** | **Ground Truth & API Control** | **Approved** | **2026-01-22** | **[Link](rfc/RFC-009-ground-truth-api-control.md)** |

## 4. 페르소나 및 운영 (Personas & Operations)
- **[Personas & Council](personas.md)**: 6인 페르소나 및 협의 프로토콜.
- **[Operations Guide](operations.md)**: 일상적 시스템 운영 규정.
- **[Database Migration Strategy](database_migration_strategy.md)**: DB 스키마 변경 및 데이터 이관 전략.
- **[Managed Policies](managed_policies.md)**: 외부 라이브러리 및 의존성 관리 정책.

## 5. 분석 및 검토 (Audits & Reviews)
- **[Knowledge Base (INDEX)](knowledge_base.md)**: 기술 분석 및 의사결정 이력 허브.
- **[Test Completeness Review](reviews/002_test_completeness_review_2026-01-19.md)**
- **[Dashboard UX Review](reviews/001_dashboard_review.md)**

## 6. 템플릿 (Templates)
- **[Document Templates](templates/)**: RFC, ISSUE, 실험 보고서 등 각종 문서 양식.

---
> [!IMPORTANT]
> 거버넌스 변경은 `/amend-constitution` 및 `/council-review` 워크플로우를 통해서만 가능합니다.
