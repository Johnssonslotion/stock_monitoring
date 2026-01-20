# ISSUE-021: Critical KIS Auth Failure Remediation

**Status**: Resolved
**Priority**: P0 (Critical - Hotfix)
**Type**: Bug
**Created**: 2026-01-20
**Assignee**: Developer

## Problem Description
The active collector container (`stoic_maxwell`) is failing with `EGW00104: secretkey는 필수입니다` errors.
This indicates the `KIS_APP_SECRET` environment variable is missing in the runtime environment.
Market open is imminent (or passed), causing data loss.

## Acceptance Criteria
- [x] Container restarted with correct `.env` loading.
- [x] KIS WebSocket connects successfully without 'secretkey' errors.
- [x] Real-time tick collection verified (Persistence fixed).

## Resolution Summary
- Identified `stoic_maxwell` (legacy container) was the source of Auth errors.
- Discovered `deploy-kis-service` lacked data volume persistence.
- Recovered Trapped Data from Kiwoom container.
- Patched `docker-compose.yml` to mount `../data`.
- Restarted KIS service. Verified `ws_raw_...` file creation.

## Resolution Plan
1.  Verify `.env` keys.
2.  Stop/Remove broken container.
3.  Run new container with `--env-file .env`.
