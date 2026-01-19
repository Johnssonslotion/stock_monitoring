# Project Backlog: Backend Integration & Data Pipeline

> **Governance Notice**: 
> 본 백로그의 작업은 **Live Market Data Collection**에 영향을 주지 않도록, 장 마감 후 또는 별도의 Staging 환경에서 진행해야 합니다.

## Issues (All Work Items)

**Note (v2.10)**: RFC는 폐지되었습니다. 복잡한 작업은 ISSUE 내 `## Design` 섹션으로 관리합니다.

- [ ] **ISSUE-001**: 데이터 누락 감지 및 채우기 로직 (Data Gap Detection) | P2
- [x] **ISSUE-002**: 백로그 이슈 ID 표준화 | P1 | ✅ 완료
- [ ] **ISSUE-003**: API 에러 핸들링 및 로깅 (API Error Handling & Logging) | P2
- [x] **ISSUE-004**: 차트 줌 오류 및 휴장일 처리 | P1 | ✅ 완료
- [ ] **ISSUE-005**: 가상 투자 시뮬레이션 플랫폼 (Virtual Investment) | P1 | Epic
- [ ] **ISSUE-006**: DB 뷰 및 집계 복구 (DB Aggregation Restoration) | P0
- [ ] **ISSUE-007**: 웹소켓 연결 관리자 (WebSocket Manager) | P1 | Epic
- [ ] **ISSUE-008**: 차트 UI 컨트롤 겹침 현상 (Chart Controls Overlap) | P1 | Bug

---

## 참고: 재정렬 내역 (2026-01-17)

**v2.10 변경** (Issue-First Principle):
- RFC-005~010 삭제 (RFC는 연간 0~2개만)
- 모든 작업은 ISSUE로 통합
- 복잡한 작업은 ISSUE 내 Design 섹션 추가

**이전 재정렬** (v2.8):
- `ISSUE-005` → `ISSUE-001` (Data Gap Detection)
- `ISSUE-006` → `ISSUE-003` (API Error Handling)
- `ISSUE-007` → `ISSUE-004` (Chart Zoom - 완료)
- `ISSUE-010` → `ISSUE-005` (Virtual Investment)
- `ISSUE-011` → `ISSUE-006` (DB Aggregation)
- `ISSUE-013` → `ISSUE-007` (WebSocket Manager)

상세: `docs/governance/issue_reorganization_plan_2026-01-17.md`
