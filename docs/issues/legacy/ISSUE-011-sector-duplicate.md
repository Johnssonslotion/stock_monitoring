# ISSUE-011: Market Sector Service

**Status**: Open
**Priority**: P2 (Major)
**Type**: Feature
**Created**: 2026-01-17
**Assignee**: Data Engineer

## Problem Description
Calculate and serve real-time market sector performance (e.g., Semiconductor, Bio). Requires a batch job to aggregate constituent stock returns.

## Acceptance Criteria
- [ ] 10-second batch job to aggregate sector returns.
- [ ] `GET /api/market/sectors` endpoint.

## Technical Details
- **Computation**: Weighted average of constituent stocks.
