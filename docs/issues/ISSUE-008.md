# ISSUE-008: 차트 UI 컨트롤 겹침 현상 (Chart UI Controls Overlap)

**Status**: In Progress
**Priority**: P1 (High)
**Type**: Bug
**Created**: 2026-01-17
**Assignee**: Frontend Engineer

## Problem Description
프론트엔드 차트에서 분봉 선택 드롭다운(Timeframe Selector)과 줌 인/아웃 컨트롤이 UI 상에서 겹쳐서 표시되어 사용성이 저하됩니다.

## Acceptance Criteria
- [ ] 분봉 선택 드롭다운과 줌 컨트롤이 겹치지 않도록 재배치
- [ ] 모든 해상도(Desktop, Tablet, Mobile)에서 정상 표시 확인
- [ ] 기존 차트 기능에 영향 없음

## Technical Details
- **파일**: `src/web/src/components/Chart.tsx` 또는 관련 스타일 파일
- **예상 원인**: CSS z-index 또는 position 충돌
- **해결 방향**: Layout 조정 또는 컨트롤 위치 재배치

## Related PRs
(To be added)
