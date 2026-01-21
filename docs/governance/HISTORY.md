# Governance History Log (Constitution Amendments)

이 문서는 프로젝트 헌법(`.ai-rules.md`)의 변경 이력을 요약(Index)합니다.
상세한 배경과 논의 내용은 `decisions/` 디렉토리의 원본 문서를 참조하십시오.

| Date | Ver | Title (Change Summary) | Rationale & Details |
| :--- | :--- | :--- | :--- |
| **2026-01-17** | **2.1** | **Systematization & Dual Socket**<br>- Dual Socket 공식 허용 (w/ Fallback)<br>- Schema Strictness 조항 신설<br>- Rule Change Protocol 도입 | [Decision-001](decisions/001_dual_socket_governance.md) |
| **2026-01-17** | **2.2** | **Dual Socket Deferral & Spec Gate**<br>- Law #2 복구 (Single Socket)<br>- Spec Verification Gate 신설<br>- Process First 원칙 확립 | [Decision-002](decisions/002_dual_socket_deferral.md) |
| **2026-01-17** | **2.3** | **Relative Path for Portability**<br>- 절대 경로 → 상대 경로 변경<br>- 워크트리/브랜치 독립성 확보 | [Decision-003](decisions/003_relative_path.md) |
| **2026-01-17** | **2.4** | **Risk Control & Spec Standard**<br>- Single Socket 강제 (RFC-001)<br>- Strategy Spec 의무화 (RFC-002) | [RFC-001](decisions/RFC-001_single_socket_enforcement.md)<br>[RFC-002](decisions/RFC-002_strategy_spec_standard.md) |
| **2026-01-17** | **2.5** | **Config Management Standard**<br>- Env(Infra) vs File(Logic) 이원화<br>- Frontend Port는 Env로 관리 | [RFC-003](decisions/RFC-003_config_management_standard.md) |
| **2026-01-17** | **2.6** | **Governance System v2**<br>- 9대 워크플로우(Slash Command) 도입<br>- Deferred Work Registry 신설<br>- 아이디어 인큐베이션 및 로드맵 자동화 | [Governance Audit](../ARCHIVE/governance/governance_audit_2026-01-17.md) |
| **2026-01-17** | **2.7** | **Mandate Doc Sync**<br>- 문서 작업 전 `git pull` 강제 (Pre-condition)<br>- ID 충돌 방지 및 거버넌스 최신화 | [ID-doc-sync-policy](../ideas/ID-doc-sync-policy.md) |
| **2026-01-17** | **2.8** | **RFC vs ISSUE Separation**<br>- 복잡도 기준 Decision Tree 도입<br>- `/create-issue`에 RFC 체크 자동화<br>- 설계(RFC) → 구현(ISSUE) 흐름 명확화 | [ID-rfc-issue-separation](../ARCHIVE/ideas/ID-rfc-issue-separation.md)<br>[Audit Report](../ARCHIVE/issues/issue_rfc_audit_2026-01-17.md) |
| **2026-01-17** | **2.8** | **Dual AI Workflow Support**<br>- Gemini Antigravity + Claude Code 동시 지원<br>- `.agent/workflows/` (SSoT) + `.claude/commands/` (심링크)<br>- Law #6 개정 (Workflow First, AI별 실행 방식 명시)<br>- Section 6 신설 (Dual AI Workflow Support) | [RFC-004](decisions/RFC-004_dual_ai_workflow_sync.md) |
| **2026-01-17** | **2.9** | **Task Management Unification**<br>- Git Branches = 실행 SSoT<br>- BACKLOG = 단기 작업 (자동 생성)<br>- Roadmap = 분기 전략 (수동 관리)<br>- 3-Tier 문서 역할 명확화 | [ID-backlog-roadmap-unified](../ideas/ID-backlog-roadmap-unified.md) |
| **2026-01-17** | **2.10** | **Issue-First Principle**<br>- ISSUE = 문제 + 설계 + 구현 (단일 스토리)<br>- RFC 기준 대폭 상향 (연간 0~2개)<br>- v2.8 수정: RFC 남발 방지<br>- Design 섹션 ISSUE 내 통합 | [ID-issue-first-workflow](../ARCHIVE/ideas/ID-issue-first-workflow.md) |
| **2026-01-19** | **2.11** | **Environment Integrity**<br>- 패키지 관리 Poetry 강제<br>- `pip install` 금지 및 CI 일관성 확보<br>- Law #8 추가 (Dependency Integrity) | User Request (Prevent Drift) |
| **2026-01-21** | **2.12** | **Living Governance Binding**<br>- 헌법 조항과 워크플로우(@/command) 직접 바인딩<br>- @/manage-docs, @/create-spec 등 실행 가이드 삽입<br>- 실시간 거버넌스 준수 체계 구축 | [ID-living-governance](../ideas/ID-living-governance-binding.md) |
