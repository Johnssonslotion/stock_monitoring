# ISSUE-004: WebSocket Connection Manager Implementation

**Status**: Open
**Priority**: P1 (High)
**Type**: Feature
**Created**: 2026-01-17
**Assignee**: Backend Engineer

## Problem Description
The KIS API enforces a strict "Single Socket per Key" policy. A centralized `ConnectionManager` is needed to multiplex subscriptions and handle reconnections automatically.

## Acceptance Criteria
- [ ] **Single Socket Policy**: Enforce 1 socket per API key globally.
- [ ] **Multiplexing**: Handle multiple symbol subscriptions over one socket.
- [ ] **Recoverability**: Auto-reconnect within 60s on disconnection.
- [ ] **Redis Pub/Sub**: Publish ticks to `stock:ticks` channel.

## Technical Details
- **File**: `src/backend/ws/manager.py`
- **Redis**: Use pub/sub for decoupling ingestion from consumption.
