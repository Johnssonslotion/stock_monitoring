#!/bin/bash
# scripts/run_recovery_job.sh
# Orchestrates KIS Tick Recovery: Backfill -> Merge

set -e
export PYTHONPATH=.


# Default to "Auto" mode (all symbols in config)
# Or accept symbols as args
SYMBOLS="$@"

echo "🚀 Starting Data Recovery Job..."
date

# 1. Run Backfill
# Capture output DB path from stdout line "OUTPUT_DB=..."
echo "▶️  Step 1: Fetching ticks from KIS API..."
if [ -z "$SYMBOLS" ]; then
    CMD="poetry run python src/data_ingestion/recovery/backfill_manager.py"
else
    CMD="poetry run python src/data_ingestion/recovery/backfill_manager.py --symbols $SYMBOLS"
fi

OUTPUT=$(eval $CMD)
echo "$OUTPUT"

# Extract DB Path (last line or check specific prefix)
DB_PATH=$(echo "$OUTPUT" | grep "OUTPUT_DB=" | cut -d'=' -f2)

if [ -z "$DB_PATH" ]; then
    echo "❌ Backfill failed or no DB path returned."
    exit 1
fi

echo "✅ Backfill complete. Temp DB: $DB_PATH"

# 2. Run Merge
# 2. Run Merge (Deprecated - handled by DuckDBArchiver)
# echo "▶️  Step 2: Merging into Main DB..."
# poetry run python src/data_ingestion/recovery/merge_worker.py --cleanup

echo "✅ Recovery Job Complete. (Archiver will pick up the file automatically)"
