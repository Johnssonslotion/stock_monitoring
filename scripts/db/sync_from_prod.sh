#!/bin/bash
# ============================================================================
# Database Data Sync (Prod -> Local)
# ============================================================================
# Purpose: Fetch recent data from Production (oracle-a1) to Local TimescaleDB
# Usage: ./scripts/db/sync_from_prod.sh [days]
# Default: 1 day (Last 24 hours) for Ticks/Minutes, 7 days for Candles
# ============================================================================

set -e

# Configuration
SOURCE_HOST="oracle-a1-tailscale"
SOURCE_USER="postgres"
SOURCE_DB="stockval"
LOCAL_CONTAINER="${DB_CONTAINER:-deploy-timescale}"
LOCAL_User="postgres"
LOCAL_DB="stockval"

DAYS="${1:-1}"
echo "📦 Starting Data Sync from ${SOURCE_HOST} (Interval: ${DAYS} days)"
echo "   Target Container: ${LOCAL_CONTAINER}"
echo "================================================="

# Check local container
if ! docker ps | grep -q "${LOCAL_CONTAINER}"; then
    echo "❌ Error: Local container '${LOCAL_CONTAINER}' is not running."
    exit 1
fi

# Function to copy data
sync_table_partial() {
    local table=$1
    local interval=$2
    local time_col="${3:-time}"

    echo "🔄 Syncing ${table} (Last ${interval})..."
    
    # 1. Truncate local (Optional? No, we might want to keep data. But for sync usually we want consistent state. MERGE is hard with COPY. We will just APPEND and ignore duplicates if possible, or DELETE overlapping range first).
    # Simple strategy: Delete local data in range, then copy.
    echo "   Cleaning local data > NOW - ${interval}..."
    docker exec -i ${LOCAL_CONTAINER} psql -U ${LOCAL_User} -d ${LOCAL_DB} -c "DELETE FROM ${table} WHERE ${time_col} > NOW() - INTERVAL '${interval}';" > /dev/null

    # 2. Copy from Remote to Local
    # Uses efficient COPY (BINARY) Protocol
    # SSH -> Remote PSQL (STDOUT) -> Local PSQL (STDIN)
    echo "   Fetching & Importing..."
    ssh ${SOURCE_HOST} "docker exec -i stock_prod-timescale psql -U ${SOURCE_USER} -d ${SOURCE_DB} -c \"COPY (SELECT * FROM ${table} WHERE ${time_col} > NOW() - INTERVAL '${interval}') TO STDOUT\"" | \
        docker exec -i ${LOCAL_CONTAINER} psql -U ${LOCAL_User} -d ${LOCAL_DB} -c "COPY ${table} FROM STDIN"

    echo "   ✅ Done"
}

sync_table_full() {
    local table=$1
    echo "🔄 Syncing ${table} (FULL)..."
    
    echo "   Truncating local..."
    docker exec -i ${LOCAL_CONTAINER} psql -U ${LOCAL_User} -d ${LOCAL_DB} -c "TRUNCATE TABLE ${table};" > /dev/null

    echo "   Fetching & Importing..."
    ssh ${SOURCE_HOST} "docker exec -i stock_prod-timescale psql -U ${SOURCE_USER} -d ${SOURCE_DB} -c \"COPY ${table} TO STDOUT\"" | \
        docker exec -i ${LOCAL_CONTAINER} psql -U ${LOCAL_User} -d ${LOCAL_DB} -c "COPY ${table} FROM STDIN"
        
    echo "   ✅ Done"
}

# --- Execution ---

# 1. Symbol Metadata - Skipped (Not in Prod)
# sync_table_full "symbol_metadata"

# 2. Market Candles (High Value, Low Volume) - Default 30 days if arg is 1, else use arg
CANDLE_DAYS="30 days"
if [ "$DAYS" -gt 30 ]; then
    CANDLE_DAYS="${DAYS} days"
fi
sync_table_partial "market_candles" "${CANDLE_DAYS}"

# 3. Market Minutes (Medium Volume) - Use arg
sync_table_partial "market_minutes" "${DAYS} days"

# 4. Market Ticks (High Volume) - Use arg (Be careful!)
sync_table_partial "market_ticks" "${DAYS} days"

# 5. Orderbook (High Volume) - Use arg
sync_table_partial "market_orderbook" "${DAYS} days"

# 6. System Metrics - Use arg
sync_table_partial "system_metrics" "${DAYS} days"

# 7. Quality & Verification
# sync_table_partial "data_quality_metrics" "${DAYS} days" "date" # date column, not time
# sync_table_partial "market_verification_results" "${DAYS} days"

echo "================================================="
echo "✅ Data Sync Complete!"
echo "   Verify with: docker exec -it ${LOCAL_CONTAINER} psql -U postgres -d stockval -c \"SELECT table_name, (SELECT count(*) FROM market_ticks) as ticks_count FROM information_schema.tables WHERE table_schema='public';\""
