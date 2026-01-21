# ISSUE-004: 차트 줌 오류 및 휴장일 처리 (Chart Zoom Glitch & Market Holiday Handling)

**Status**: Resolved (Code Merged)
**Priority**: P1 (High)
**Type**: Bug / Data Quality
**Created**: 2026-01-17
**Assignee**: Developer

## 문제 설명 (Problem Description)
1. **휴장일 로직 부재**: 현 시스템(`isMarketOpen`, 데이터 수집)이 한국/미국 휴장일을 인지하지 못해, 휴일에도 "Mock Data Mode"가 잘못 활성화되거나 데이터 누락 로그가 발생하는 문제.
2. **차트 줌 및 분봉 겹침**: 차트 줌 인/아웃 시 분봉(`1m`) 캔들이 시각적으로 겹치거나 깨지는 현상 발생 (lightweight-charts `timeScale` 설정 미흡).

## 완료 조건 (Acceptance Criteria)
- [x] **휴일 인식**: 2026년 주요 공휴일을 식별하는 `MarketCalendar` 서비스 구현.
    - [x] `isMarketOpen()`이 휴일에 `false` 반환.
- [x] **차트 줌 수정**:
    - [x] `CandleChart.tsx`의 `timeScale` 설정 최적화 (`minBarSpacing`, `fixLeftEdge` 등).
    - [x] 1분봉 캔들이 줌 레벨에 관계없이 겹치지 않고 정상 렌더링 확인.

## 기술 상세 (Technical Details)
- **Frontend**: `src/web/src/components/CandleChart.tsx`, `src/web/src/mocks/marketHoursMock.ts`
- **Library**: `lightweight-charts` v4+

## 해결 계획 (Resolution Plan)
1. (완료) `marketHoursMock.ts`에 2026년 휴일 추가.
2. (완료) `CandleChart.tsx` 줌 동작 수정.
3. (완료) E2E 테스트 `map-first-layout.spec.ts` 검증.

## 관련 (Related)
- Replaces legacy `ISSUE-001` entry (which is now Virtual Investment).
- Code merged in `02940b1`.
