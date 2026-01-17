# ISSUE-003: DB View & Aggregation Restoration

**Status**: Open
**Priority**: P0 (Critical)
**Type**: Bug / Data Quality
**Created**: 2026-01-17
**Assignee**: Backend Engineer

## Problem Description
Database views and continuous aggregates for candle data (1m, 5m, 1h, 1d) need to be verified and restored if missing. This is critical for data integrity and query performance.

## Acceptance Criteria
- [ ] `market_candles` retention policy checked.
- [ ] `public.candles_1m` view recreated.
- [ ] Continuous Aggregates (5m, 1h, 1d) created with refresh policies.
- [ ] `SELECT count(*)` verification shows data for all timeframes.

## Technical Details
- **DB**: TimescaleDB
- **Key Tables**: `market_candles`, `candles_1m`, `candles_5m`, etc.
