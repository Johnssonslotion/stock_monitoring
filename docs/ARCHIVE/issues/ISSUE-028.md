# ISSUE-028: [Bug] Chart UI Controls Overlap & Env Indicator

**Status**: In Progress  
**Priority**: P2  
**Type**: bug  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- 차트 상단의 Timeframe selector, Zoom controls가 가격 축(Price Axis) 및 차트 영역과 겹쳐서 클릭이 어렵거나 시인성이 떨어짐.
- 현재 환경(Local/Prod)을 구분할 수 있는 시각적 지표(Indicator)가 없어 오해의 소지가 있음.
- 차트 데이터 로딩 중 빈 화면이 노출되어 사용자 경험 저하.

## Acceptance Criteria
- [ ] **UI Overlap Fix**: Timeframe selector와 Zoom control을 우측 상단으로 그룹화하여 배치하고, 가격 축과 겹치지 않도록 레이아웃 조정 (Z-index 및 Margin 조정).
- [ ] **Environment Indicator**: 화면 상단(헤더 또는 차트 영역)에 현재 연결된 환경(Local/Prod)을 표시하는 배지(Badge) 추가.
- [ ] **Loading State**: 차트 데이터 로딩 시 Spinner 또는 Skeleton UI를 표시하여 빈 화면 방지.
- [ ] **E2E Test**: 수정된 UI에 대한 스크린샷 기반 E2E 테스트 통과.
