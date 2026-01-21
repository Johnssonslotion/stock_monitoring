# ISSUE-018: Implement KIS Tick Recovery (Backfill Manager)

**Status**: Open
**Priority**: P2
**Type**: feature
**Created**: 2026-01-19
**Assignee**: Developer

## Problem Description
To ensure 100% data completeness, we need a mechanism to recover missing tick data using KIS REST API. The `backfill_manager.py` prototype exists but needs to be formalized and integrated into the system workflow.

## Acceptance Criteria
- [ ] **KIS Tick API Integration**: Use `FHKST01010300` (Tick History) instead of Minute Candles.
- [ ] **Lock-Safe Execution**: Ensure it can run without conflicting with the main DuckDB lock (use temp file + merge).
- [ ] **Workflow Integration**: Ensure `/run-data-recovery` workflow covers this process.

## Technical Details
- **File**: `src/data_ingestion/recovery/backfill_manager.py`
- **API**: KIS `inquire-time-itemconclusion`

## Resolution Plan
1. Finalize `backfill_manager.py` (already modified in verification phase).
2. Clean up imports and error handling.
3. Validate "Merge" logic in `DuckDBArchiver` or separate script.

## Related
- RFC: [RFC-008](../governance/rfc/RFC-008-tick-completeness-qa.md)
