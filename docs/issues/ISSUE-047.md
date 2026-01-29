# ISSUE-047: Tick Aggregation Verification & Auto-Recovery

**Status**: 🟡 In-Progress
**Priority**: P1 (Data Integrity)
**Assignee**: Developer
**Created**: 2026-01-29

## 1. Summary
Implementing "Tick Aggregation Verification" as a Tier 3 Quality Gate.
Post-market (16:10), the system verifies if the `market_candles_1m_view` (aggregated from ticks) matches the KIS REST API (Ground Truth). If there are significant discrepancies, it automatically upserts the KIS data to `market_candles` table to ensure data integrity.

## 2. Scope
- [ ] Modify `src/verification/worker.py` to support `verify_tick_aggregation` task type.
- [ ] Implement query logic: DB View vs API Hub (KIS).
- [ ] Implement recovery logic: Upsert KIS data to `market_candles`.
- [ ] Register new cron schedule (16:10 KST) in `run_verification_worker`.

## 3. Implementation Details
- **VerificationConsumer**: Add `_handle_aggregation_verification`.
- **Threshold**: Volume mismatch > 1% or missing rows.
- **Recovery**: Use `impute_candles_batch` logic or direct INSERT ON CONFLICT.

## 4. Verification
- Manual trigger of the task.
- Verify `market_verification_results` table for audit log.
