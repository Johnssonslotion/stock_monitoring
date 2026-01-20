---
description: Run manual data recovery (backfill) for missing ticks using KIS REST API
---

# Workflow: Run Data Recovery

This workflow triggers the **KIS Tick Recovery** process (ISSUE-018). It recovers missing tick data for specific symbols or all configured symbols by querying the KIS `inquire-time-itemconclusion` API and merging the results into the main DuckDB.

## Prerequisites
- Valid KIS API Token (handled by `KISAuthManager`)
- `configs/kr_symbols.yaml` or explicit symbol list

## Steps

1. **Check Environment**
   Ensure you are in the project root.
   ```bash
   cd /home/ubuntu/workspace/stock_monitoring
   ```

2. **Run Recovery (All Symbols)**
   To recover data for ALL symbols in `configs/kr_symbols.yaml` (Warning: Takes time):
   ```bash
   // turbo
   ./scripts/run_recovery_job.sh
   ```

3. **Run Recovery (Specific Symbols)**
   To recover specific symbols (e.g., Samsung Electronics):
   ```bash
   // turbo
   ./scripts/run_recovery_job.sh 005930
   ```
   For multiple symbols:
   ```bash
   // turbo
   ./scripts/run_recovery_job.sh 005930 000660
   ```

4. **Verify Results**
   Check the logs or query DuckDB to confirm data count.
   ```bash
   python scripts/check_duckdb_integrity.py
   ```

## Technical Details
- **Backfill**: `src/data_ingestion/recovery/backfill_manager.py` fetches data and saves to `data/recovery/recovery_temp_{timestamp}.duckdb`.
- **Merge**: `src/data_ingestion/recovery/merge_worker.py` merges the temp DB into `data/ticks.duckdb` using `ATTACH` and `INSERT OR IGNORE`.
