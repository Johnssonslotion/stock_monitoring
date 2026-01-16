-- ============================================================================
-- TimescaleDB Continuous Aggregates for Multi-Interval Candles
-- ============================================================================
-- Purpose: Generate 5m, 15m, 1h, 1d intervals from 1m base data
-- Author: Antigravity AI
-- Date: 2026-01-15
-- ============================================================================

-- Drop existing views if recreating (idempotent)
DROP MATERIALIZED VIEW IF EXISTS market_candles_5m CASCADE;
DROP MATERIALIZED VIEW IF EXISTS market_candles_15m CASCADE;
DROP MATERIALIZED VIEW IF EXISTS market_candles_1h CASCADE;
DROP MATERIALIZED VIEW IF EXISTS market_candles_1d CASCADE;

-- ============================================================================
-- 1. 5-Minute Candles (5m)
-- ============================================================================
CREATE MATERIALIZED VIEW market_candles_5m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', time) AS time,
    symbol,
    FIRST(open, time) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, time) AS close,
    SUM(volume) AS volume
FROM market_candles
WHERE interval = '1m'
GROUP BY time_bucket('5 minutes', time), symbol
WITH NO DATA;

-- Add refresh policy: update every 1 minute for recent 1 hour of data
SELECT add_continuous_aggregate_policy('market_candles_5m',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute');

COMMENT ON MATERIALIZED VIEW market_candles_5m IS 
'5-minute candles aggregated from 1m base data. Auto-refreshed every minute.';

-- ============================================================================
-- 2. 15-Minute Candles (15m)
-- ============================================================================
CREATE MATERIALIZED VIEW market_candles_15m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('15 minutes', time) AS time,
    symbol,
    FIRST(open, time) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, time) AS close,
    SUM(volume) AS volume
FROM market_candles
WHERE interval = '1m'
GROUP BY time_bucket('15 minutes', time), symbol
WITH NO DATA;

-- Add refresh policy: update every 5 minutes for recent 1 day of data
SELECT add_continuous_aggregate_policy('market_candles_15m',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes');

COMMENT ON MATERIALIZED VIEW market_candles_15m IS 
'15-minute candles aggregated from 1m base data. Auto-refreshed every 5 minutes.';

-- ============================================================================
-- 3. 1-Hour Candles (1h)
-- ============================================================================
CREATE MATERIALIZED VIEW market_candles_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS time,
    symbol,
    FIRST(open, time) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, time) AS close,
    SUM(volume) AS volume
FROM market_candles
WHERE interval = '1m'
GROUP BY time_bucket('1 hour', time), symbol
WITH NO DATA;

-- Add refresh policy: update every 1 hour for recent 3 days of data
SELECT add_continuous_aggregate_policy('market_candles_1h',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

COMMENT ON MATERIALIZED VIEW market_candles_1h IS 
'1-hour candles aggregated from 1m base data. Auto-refreshed every hour.';

-- ============================================================================
-- 4. Daily Candles (1d)
-- ============================================================================
CREATE MATERIALIZED VIEW market_candles_1d
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS time,
    symbol,
    FIRST(open, time) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, time) AS close,
    SUM(volume) AS volume
FROM market_candles
WHERE interval = '1m'
GROUP BY time_bucket('1 day', time), symbol
WITH NO DATA;

-- Add refresh policy: update once a day for recent 7 days of data
SELECT add_continuous_aggregate_policy('market_candles_1d',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day');

COMMENT ON MATERIALIZED VIEW market_candles_1d IS 
'Daily candles aggregated from 1m base data. Auto-refreshed daily.';

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- List all continuous aggregates
SELECT view_name, materialized_only, compression_enabled
FROM timescaledb_information.continuous_aggregates
ORDER BY view_name;

-- Check refresh policies
SELECT view_name, schedule_interval, start_offset, end_offset
FROM timescaledb_information.jobs
WHERE proc_name = 'policy_refresh_continuous_aggregate'
ORDER BY view_name;

-- Preview data counts (after initial refresh)
-- SELECT 'market_candles_5m' AS view, COUNT(*) FROM market_candles_5m
-- UNION ALL
-- SELECT 'market_candles_15m', COUNT(*) FROM market_candles_15m
-- UNION ALL
-- SELECT 'market_candles_1h', COUNT(*) FROM market_candles_1h
-- UNION ALL
-- SELECT 'market_candles_1d', COUNT(*) FROM market_candles_1d;
