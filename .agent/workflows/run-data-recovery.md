---
description: Run manual data recovery (backfill) for missing ticks using KIS REST API
---

This workflow guides you through manually recovering missing tick data using the KIS Tick API. It handles locking issues by using a temporary database and supports merging data back into the main storage.

1. **Prerequisites Check**
   - Ensure `KIS_APP_KEY` and `KIS_APP_SECRET` are valid in your `.env` or `.env.backtest`.
   - Decide on `KIS_BASE_URL`:
     - Real: `https://openapi.koreainvestment.com:9443`
     - Mock: `https://openapivts.koreainvestment.com:29443`

2. **Run Recovery Script (Lock-Safe Mode)**
   - This command uses a separate DuckDB file (`data/recovery_ticks.duckdb`) to avoid locking conflicts with running services.
   
   ```bash
   # Set for Real Environment (Default)
   export KIS_BASE_URL=https://openapi.koreainvestment.com:9443
   export PYTHONPATH=.
   
   # Load Env and Run
   export $(grep -v '^#' .env.backtest | xargs)
   poetry run python src/data_ingestion/recovery/backfill_manager.py
   ```

3. **Monitor Progress**
   - The script runs in the background or foreground.
   - Check progress by monitoring the output DB size:
   ```bash
   watch -n 5 "ls -lh data/recovery_ticks.duckdb"
   ```

4. **Verify Recovered Data**
   - Inspect the recovered data to ensure quality.
   ```bash
   poetry run python -c "import duckdb; conn=duckdb.connect('data/recovery_ticks.duckdb'); print(conn.execute('SELECT source, COUNT(*) FROM market_ticks GROUP BY source').fetchall())"
   ```

5. **Merge into Main Database (Maintenance Window Only)**
   - **WARNING**: Only run this step when the main collector/archiver is STOPPED to avoid lock conflicts on `data/ticks.duckdb`.
   
   ```bash
   # 1. Stop Services
   docker-compose stop sentinel kiwoom-service kis-service

   # 2. Merge Data
   poetry run python -c "import duckdb; conn=duckdb.connect('data/ticks.duckdb'); conn.execute(\"INSERT OR IGNORE INTO market_ticks SELECT * FROM 'data/recovery_ticks.duckdb'.market_ticks\"); print('Merge Complete')"

   # 3. Restart Services
   docker-compose up -d
   ```
