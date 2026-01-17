# ISSUE-005: Data Gap Detection & Filling Logic

**Status**: Open
**Priority**: P2 (Medium)
**Type**: Data Quality
**Created**: 2026-01-17
**Assignee**: Data Engineer

## Problem Description
Market data often has gaps due to network issues or low liquidity. The API should detect these gaps and optionally fill them (Zero-Order Hold) to provide a continuous chart experience.

## Acceptance Criteria
- [ ] `get_candles` logic detects missing timestamps.
- [ ] Implement Zero-Order Hold (fill with previous close).
- [ ] Add `is_filled` flag to response metadata.

## Technical Details
- **API**: `src/backend/api/candles.py`
- **Algorithm**: Check expected vs actual timestamps.
