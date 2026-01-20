# ISSUE-008: Chart UI Controls Overlap

**Status**: In Progress
**Priority**: P1 (High)
**Type**: Bug
**Created**: 2026-01-17
**Assignee**: Frontend Engineer

## Problem Description
Real-time OrderBook (Hoga) data streaming is required for day traders. Bandwidth usage must be optimized by sending only deltas (changes) rather than full snapshots every time.

## Acceptance Criteria
- [ ] Implement `stream_orderbook` handler.
- [ ] Send OrderBook Deltas to reduce bandwidth.

## Technical Details
- **Source**: KIS WebSocket (H0STASP0)
- **Optimization**: Check diff before broadcast.
