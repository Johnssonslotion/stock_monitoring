# ISSUE-045: Fix CPU Monitoring Display

**Status**: Open  
**Priority**: P0  
**Type**: bug  
**Created**: 2026-01-17  
**Assignee**: Developer

## Problem Description
실시간 모니터링 시스템(ISSUE-044) 적용 후, `SystemDashboard`에서 Memory와 Disk 정보는 정상적으로 차트에 표시되나 **CPU 차트 라인이 나타나지 않는 현상**이 보고되었습니다.

## Acceptance Criteria
- [ ] `SystemDashboard`의 LineChart에서 CPU % 데이터가 실시간으로 렌더링되어야 함.
- [ ] 초기 로딩 시 과거 CPU 데이터가 정상적으로 표시되어야 함.
- [ ] Sentinel이 CPU 데이터를 올바른 형식으로 송신하고 있는지 확인 필요.

## Technical Details
- **Sentinel**: `metric_data.append({"type": "cpu", "value": cpu})`로 전송 중.
- **Frontend**: `handleMetric` 함수에서 `['cpu', 'memory', 'disk'].includes(m.type)` 필터링 중.
- **Possible Cause**: 
    1. Sentinel의 수집 간격(5s) 내에서 CPU 값이 0이거나 데이터 누락 가능성.
    2. Recharts의 `Line` 컴포넌트 `dataKey` 매칭 오류.
    3. 초기 데이터 fetch 시 `m.type === 'cpu'`인 진입점이 누락되었을 가능성.

## Related
- Branch: `bug/ISSUE-045-fix-cpu-monitoring`
- Roadmap: [Observability Roadmap](../strategies/observability_roadmap.md)
