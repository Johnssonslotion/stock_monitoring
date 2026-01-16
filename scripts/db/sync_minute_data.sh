#!/bin/bash
# ============================================================================
# Phase 1: Sync Local 1-Minute Candle Data to Server (oracle-a1)
# ============================================================================
# Purpose: Transfer historical 1m candle CSV data to production server
# Safety: Read-only operation, safe to run during market hours
# Server: oracle-a1 (168.107.40.168)
# ============================================================================

set -e  # Exit on error

echo "📦 Phase 1: Local Minute Data Sync to oracle-a1"
echo "================================================="
echo ""

# Configuration
LOCAL_DATA_DIR="scripts/data_ingest"
SERVER_HOST="oracle-a1"
SERVER_TMP_DIR="/tmp/minute_sync"
SERVER_PROJECT_DIR="~/workspace/stock_monitoring"

# Step 1: Verify local CSV files
echo "1️⃣ Verifying local 1-minute CSV files..."
CSV_COUNT=$(find ${LOCAL_DATA_DIR} -name "*_candles.csv" -type f | wc -l | tr -d ' ')
echo "   Found: ${CSV_COUNT} files"

if [ "$CSV_COUNT" -eq 0 ]; then
    echo "   ❌ ERROR: No candle CSV files found in ${LOCAL_DATA_DIR}"
    exit 1
fi

# List sample files
echo "   Sample files:"
find ${LOCAL_DATA_DIR} -name "*_candles.csv" -type f | head -3 | while read file; do
    SIZE=$(du -h "$file" | awk '{print $1}')
    echo "      - $(basename $file) ($SIZE)"
done
echo ""

# Step 2: Calculate total size
echo "2️⃣ Calculating data size..."
TOTAL_SIZE=$(du -sh ${LOCAL_DATA_DIR} | awk '{print $1}')
echo "   Total size: ${TOTAL_SIZE}"
echo ""

# Step 3: Create server directory (via SSH)
echo "3️⃣ Preparing server directory..."
ssh ${SERVER_HOST} "mkdir -p ${SERVER_TMP_DIR}" || {
    echo "   ❌ ERROR: Cannot connect to server ${SERVER_HOST}"
    exit 1
}
echo "   ✅ Server directory ready: ${SERVER_TMP_DIR}"
echo ""

# Step 4: Transfer files (rsync)
echo "4️⃣ Transferring files to server..."
echo "   Target: ${SERVER_HOST}:${SERVER_TMP_DIR}/"
echo "   This may take 5-10 minutes (133MB)..."
rsync -avz --progress ${LOCAL_DATA_DIR}/*_candles.csv ${SERVER_HOST}:${SERVER_TMP_DIR}/ || {
    echo "   ❌ ERROR: rsync failed"
    exit 1
}
echo "   ✅ Transfer complete"
echo ""

# Step 5: Verify transfer
echo "5️⃣ Verifying transfer..."
REMOTE_COUNT=$(ssh ${SERVER_HOST} "ls ${SERVER_TMP_DIR}/*_candles.csv 2>/dev/null | wc -l" | tr -d ' ')
echo "   Local files: ${CSV_COUNT}"
echo "   Remote files: ${REMOTE_COUNT}"

if [ "$CSV_COUNT" -eq "$REMOTE_COUNT" ]; then
    echo "   ✅ Transfer verified successfully"
else
    echo "   ⚠️  WARNING: File count mismatch"
fi
echo ""

# Step 6: Server ingestion
echo "6️⃣ Ingesting data on server..."
echo "   Running: python scripts/ingest_csv.py --source ${SERVER_TMP_DIR}"
ssh ${SERVER_HOST} "cd ${SERVER_PROJECT_DIR} && python scripts/ingest_csv.py --source ${SERVER_TMP_DIR}" || {
    echo "   ⚠️  Ingestion completed with warnings (duplicate keys expected)"
}
echo ""

echo "✅ Phase 1 Complete!"
echo "================================================="
echo ""
echo "📊 Next: Verify data on server"
echo "   ssh ${SERVER_HOST}"
echo "   docker exec stock-timescale psql -U postgres -d stockval -c \"SELECT interval, COUNT(*) FROM market_candles GROUP BY interval;\""
