#!/bin/bash
# ============================================================================
# Server DB Validation Script
# ============================================================================
# Purpose: Check TimescaleDB status on production server
# Usage: Run this via Tailscale VPN connection
# ============================================================================

echo "🔍 Phase 3: Server DB Status Validation"
echo "========================================="
echo ""

# 1. Check TimescaleDB extension
echo "1️⃣ Checking TimescaleDB extension..."
docker exec stock-timescale psql -U postgres -d stockval -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';"
echo ""

# 2. Check if market_candles is a Hypertable
echo "2️⃣ Checking Hypertable status..."
docker exec stock-timescale psql -U postgres -d stockval -c "SELECT hypertable_schema, hypertable_name, num_dimensions FROM timescaledb_information.hypertables WHERE hypertable_name = 'market_candles';"
echo ""

# 3. Check existing Continuous Aggregates
echo "3️⃣ Checking existing Continuous Aggregates..."
docker exec stock-timescale psql -U postgres -d stockval -c "SELECT view_name, materialized_only, compression_enabled FROM timescaledb_information.continuous_aggregates ORDER BY view_name;"
echo ""

# 4. Check data counts
echo "4️⃣ Checking market_candles data..."
docker exec stock-timescale psql -U postgres -d stockval -c "SELECT interval, COUNT(*) as row_count, COUNT(DISTINCT symbol) as unique_symbols, MIN(time) as earliest, MAX(time) as latest FROM market_candles GROUP BY interval ORDER BY interval;"
echo ""

echo "✅ Validation complete!"
echo ""
echo "📋 Next Steps:"
echo "   - If TimescaleDB extension is missing: Run CREATE EXTENSION timescaledb;"
echo "   - If market_candles is not a Hypertable: Run create_hypertable migration"
echo "   - If Continuous Aggregates are missing: Run scripts/db/create_continuous_aggregates.sql"
