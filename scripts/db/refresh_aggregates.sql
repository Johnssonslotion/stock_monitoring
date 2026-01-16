-- ============================================================================
-- Initial Refresh for Continuous Aggregates
-- ============================================================================
-- Purpose: Populate materialized views with historical 1m data
-- Run this AFTER create_continuous_aggregates.sql
-- ============================================================================

-- Refresh all views with NULL parameters = full refresh
CALL refresh_continuous_aggregate('market_candles_5m', NULL, NULL);
CALL refresh_continuous_aggregate('market_candles_15m', NULL, NULL);
CALL refresh_continuous_aggregate('market_candles_1h', NULL, NULL);
CALL refresh_continuous_aggregate('market_candles_1d', NULL, NULL);

-- Verify data population
SELECT 
    'market_candles_5m' AS view_name,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT symbol) AS unique_symbols,
    MIN(time) AS earliest,
    MAX(time) AS latest
FROM market_candles_5m
UNION ALL
SELECT 
    'market_candles_15m',
    COUNT(*),
    COUNT(DISTINCT symbol),
    MIN(time),
    MAX(time)
FROM market_candles_15m
UNION ALL
SELECT 
    'market_candles_1h',
    COUNT(*),
    COUNT(DISTINCT symbol),
    MIN(time),
    MAX(time)
FROM market_candles_1h
UNION ALL
SELECT 
    'market_candles_1d',
    COUNT(*),
    COUNT(DISTINCT symbol),
    MIN(time),
    MAX(time)
FROM market_candles_1d
ORDER BY view_name;
