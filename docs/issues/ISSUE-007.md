# ISSUE-007: Chart Zoom Glitch & Market Holiday Handling

**Status**: Open (Doc Synced)
**Priority**: P1 (High)
**Type**: Bug / Data Quality
**Created**: 2026-01-17
**Assignee**: Developer

## Problem Description
1. **Market Holiday Logic Missing**:
   The current system (`isMarketOpen`, data ingestion) did not account for KR/US market holidays. This led to "Mock Data Mode" incorrectly activating on holidays.
   
2. **Chart Zoom & Minute Candle Overlap**:
   Zoome in/out caused visual conflicts/overlaps with minute candles (`1m`), likely due to improper `timeScale` settings in `lightweight-charts`.

## Acceptance Criteria
- [x] **Holiday Awareness**: Implement `MarketCalendar` service to identify major 2026 holidays.
    - [x] `isMarketOpen()` returns `false` on holidays.
- [x] **Chart Zoom Fix**:
    - [x] Configure `CandleChart.tsx` `timeScale` (`minBarSpacing`, `fixLeftEdge`, etc).
    - [x] Ensure 1-minute candles render correctly without overlap.

## Technical Details
- **Frontend**: `src/web/src/components/CandleChart.tsx`, `src/web/src/mocks/marketHoursMock.ts`
- **Library**: `lightweight-charts` v4+

## Resolution Plan
1. (Done) Update `marketHoursMock.ts` with 2026 holidays.
2. (Done) Fix `CandleChart.tsx` zoom behavior.
3. (Done) Verify with E2E test `map-first-layout.spec.ts`.

## Related
- Replaces legacy `ISSUE-001` entry (which is now Virtual Investment).
- Code merged in `02940b1`.
