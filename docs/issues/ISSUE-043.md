# ISSUE-043: Upgrade RealtimeVerifier to OHLCV Aggregation Logic

**Status**: Open
**Priority**: P1 (High)
**Type**: Enhancement
**Created**: 2026-01-26
**Assignee**: Agent

## Problem Description
Current `RealtimeVerifier` (`src/verification/realtime_verifier.py`) only verifies **Volume** sum against API data.
The user requirement is to verify the **integrity of local ticks** by aggregating them into 1-minute OHLCV candles and comparing them against the broker's official minute candles.
- **Current**: `Local DB Volume Sum` vs `API Volume` (2% tolerance)
- **Required**: `Local Tick Aggregation (OHLCV)` vs `API Candle (OHLCV)`

## Acceptance Criteria
- [ ] `RealtimeVerifier` queries TimescaleDB for `first(price)`, `max(price)`, `min(price)`, `last(price)`, `sum(volume)` for the target minute.
- [ ] Comparison Logic:
  - **Price (Open/High/Low/Close)**: Strict equality check (tolerance < 0.01 or exact match).
  - **Volume**: Existing tolerance (2%) maintained.
- [ ] Any Price mismatch or Volume gap triggers the existing `NEEDS_RECOVERY` flow.

## Technical Details
- **DB Function**: Use TimescaleDB's `first()` and `last()` aggregate functions.
- **File**: `src/verification/realtime_verifier.py`
- **Output**: `VerificationResult` should include price discrepancy details (e.g., "High Mismatch: Local 100 vs API 101").

## Related
- Derived from `ID-tick-aggregation-verification`
- [ISSUE-042](ISSUE-042.md) (Network Isolation Fix) - Pre-requisite for stable verification.
