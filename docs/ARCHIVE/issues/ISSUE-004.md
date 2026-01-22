# ISSUE-004: Fix Market Open Failure (Kiwoom NameError & KIS Protocol Fix)

**Status**: Resolved
**Priority**: P0  
**Type**: bug  
**Created**: 2026-01-19  
**Assignee**: Developer

## Problem Description
Real-time data collection failed during the market open on 2026-01-19. 
1. **Kiwoom Crash**: `KiwoomWSCollector` failed immediately with `NameError: name 'logger' is not defined` in multiple places.
2. **KIS Subscription Error**: KIS returned `invalid approval : NOT FOUND` for WebSocket subscriptions. This was traced to a missing `"encrypt": "N"` header field and an invalid/expired App Key in the production environment.
3. **Startup Regressions**: Restarting the `real-collector` revealed `ImportError` (`get_redis_connection`) and `AttributeError` (`load_config` vs `load_symbols`) caused by worktree inconsistencies.

## Acceptance Criteria
- [x] `KiwoomWSCollector` starts without `NameError`.
- [x] KIS WebSocket subscriptions succeed with `"encrypt": "N"` header.
- [x] `real-collector` container starts without any Python startup errors.
- [x] `ticker.kr` channel on Redis receives data from both sources.

## Technical Details
- Log snippet (Kiwoom): `exception=NameError("name 'logger' is not defined")`
- Log snippet (KIS): `msg1: invalid approval : NOT FOUND`
- Affected files:
    - `src/data_ingestion/price/kr/kiwoom_ws.py`
    - `src/data_ingestion/price/common/websocket_base.py`
    - `src/data_ingestion/price/common/websocket_dual.py`
    - `src/data_ingestion/price/unified_collector.py`
    - `src/core/config.py`

## Resolution Plan
1. **Fix Kiwoom**: Define `logger` in `kiwoom_ws.py`.
2. **Fix KIS Protocol**: Apply `"encrypt": "N"` to KIS headers.
3. **Sync Environment**: Ensure `stock_monitoring/.env` matches the verified working key.
4. **Fix Regressions**: Restore `get_redis_connection` and fix method calls in `unified_collector.py`.
5. **Rebuild & Verify**: `docker compose up -d --build` for all collectors.

## Related
- Branch: `bug/ISSUE-003-market-open-failure`
