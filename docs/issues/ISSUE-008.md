# ISSUE-008: OrderBook Streaming

**Status**: Open
**Priority**: P1 (Critical)
**Type**: Feature
**Created**: 2026-01-17
**Assignee**: Backend Engineer

## Problem Description
Real-time OrderBook (Hoga) data streaming is required for day traders. Bandwidth usage must be optimized by sending only deltas (changes) rather than full snapshots every time.

## Acceptance Criteria
- [ ] Implement `stream_orderbook` handler.
- [ ] Send OrderBook Deltas to reduce bandwidth.

## Technical Details
- **Source**: KIS WebSocket (H0STASP0)
- **Optimization**: Check diff before broadcast.
