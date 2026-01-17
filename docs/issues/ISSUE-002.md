# ISSUE-002: 백로그 이슈 ID 표준화 (Standardize Backlog Issue IDs)

**Status**: Resolved
**Priority**: P1
**Type**: Refactor (Governance)
**Created**: 2026-01-17
**Assignee**: AI Assistant

## 문제 설명 (Problem Description)
현재 `BACKLOG.md`에 `TICKET-XXX` (초기 백엔드 스펙용)와 `ISSUE-XXX` 형식이 혼재되어 있거나 ID가 없는 항목이 있어 추적이 어렵습니다. `/create-issue` 워크플로우에 맞춰 `ISSUE-XXX` 포맷으로 통일이 필요합니다.

## 완료 조건 (Acceptance Criteria)
- [x] `BACKLOG.md` 내 모든 `TICKET-XXX` 항목을 `ISSUE-XXX`로 변경.
- [x] `ISSUE-001` (Chart Zoom) 항목이 올바르게 리스트업 되어야 함.
- [x] 번호가 순차적으로(002부터) 부여되어야 함.

## 계획 (Plan)
1. `TICKET-001` -> `ISSUE-003` (DB View)
2. `TICKET-002` -> `ISSUE-004` (WebSocket)
3. `TICKET-003` -> `ISSUE-005` (Data Gap)
4. `TICKET-004` -> `ISSUE-006` (API Error)
5. `BACKLOG.md` 내용 업데이트.

## 관련 (Related)
- Branch: `refactor/ISSUE-002-standardize-backlog`
