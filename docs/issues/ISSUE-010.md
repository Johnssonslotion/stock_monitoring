# ISSUE-010: Candle Data Service

**Status**: Open
**Priority**: P2 (Major)
**Type**: Feature
**Created**: 2026-01-17
**Assignee**: Backend Engineer

## Problem Description
Expose historical candle data via REST API (`GET /api/candles`). Support various timeframes and efficient querying from TimescaleDB.

## Acceptance Criteria
- [ ] `GET /api/candles` endpoint.
- [ ] Support 1m, 5m, 1h, 1d, 1w intervals.
- [ ] Performance: < 100ms for standard range queries.

## Technical Details
- **DB**: TimescaleDB
- **Integration**: Linked with ISSUE-005 (Gap Handling).
