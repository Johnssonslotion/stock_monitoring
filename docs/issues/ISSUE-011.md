# ISSUE-011: Whale Alert System

**Status**: Open
**Priority**: P3 (Analytical)
**Type**: Feature
**Created**: 2026-01-17
**Assignee**: Backend Engineer

## Problem Description
Send external notifications (Slack/Discord) when significant market events (Whale trades) occur.

## Acceptance Criteria
- [ ] Webhook integration for Slack/Discord.
- [ ] Configurable thresholds for alerts.
- [ ] Async dispatch to avoid blocking main thread.

## Technical Details
- **Queue**: Redis Queue (RQ) or Celery recommended.
