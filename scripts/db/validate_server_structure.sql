-- ============================================================================
-- Server DB Validation Script
-- ============================================================================
-- Run this on the production server to validate DB structure
-- Usage: docker exec stock-timescale psql -U postgres -d stockval -f validate_db.sql
-- ============================================================================

-- 1. Check table structure
\echo '\n=== 1. market_candles Table Structure ==='
\d market_candles

-- 2. Check if Hypertable
\echo '\n=== 2. Hypertable Status ==='
SELECT hypertable_name, num_dimensions 
FROM timescaledb_information.hypertables 
WHERE hypertable_name = 'market_candles';

-- 3. Check existing data by interval
\echo '\n=== 3. Existing Data Summary ==='
SELECT 
    interval, 
    COUNT(*) as rows,
    COUNT(DISTINCT symbol) as symbols,
    MIN(time)::date as earliest,
    MAX(time)::date as latest
FROM market_candles 
GROUP BY interval 
ORDER BY interval;

-- 4. Check TimescaleDB extension
\echo '\n=== 4. TimescaleDB Extension ==='
SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';

-- 5. Check table size
\echo '\n=== 5. Table Size ==='
SELECT 
    pg_size_pretty(pg_total_relation_size('market_candles')) as total_size,
    pg_size_pretty(pg_relation_size('market_candles')) as table_size,
    pg_size_pretty(pg_indexes_size('market_candles')) as index_size;
