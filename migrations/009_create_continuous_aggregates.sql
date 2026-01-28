-- ============================================================================
-- TimescaleDB Continuous Aggregates for Multi-Interval Candles
-- ============================================================================
-- Purpose: Generate 1m, 5m, 1h, 1d intervals from market_ticks
-- Author: Antigravity AI
-- Date: 2026-01-28
-- ============================================================================

-- Drop existing views if recreating (idempotent)
DROP MATERIALIZED VIEW IF EXISTS market_candles_1d_view CASCADE;
DROP MATERIALIZED VIEW IF EXISTS market_candles_1h_view CASCADE;
DROP MATERIALIZED VIEW IF EXISTS market_candles_5m_view CASCADE;
DROP MATERIALIZED VIEW IF EXISTS market_candles_1m_view CASCADE;

-- ============================================================================
-- 1. 1-Minute Candles (1m)
-- ============================================================================
CREATE MATERIALIZED VIEW market_candles_1m_view
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS time,
    symbol,
    FIRST(price, time) AS open,
    MAX(price) AS high,
    MIN(price) AS low,
    LAST(price, time) AS close,
    SUM(volume) AS volume
FROM market_ticks
GROUP BY time_bucket('1 minute', time), symbol
WITH NO DATA;

-- SELECT add_continuous_aggregate_policy('market_candles_1m_view',
--     start_offset => INTERVAL '1 hour',
--     end_offset => INTERVAL '1 minute',
--     schedule_interval => INTERVAL '1 minute');

-- COMMENT ON MATERIALIZED VIEW market_candles_1m_view IS 
-- '1-minute candles aggregated from market_ticks.';

-- ============================================================================
-- 2. 5-Minute Candles (5m)
-- ============================================================================
CREATE MATERIALIZED VIEW market_candles_5m_view
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', time) AS time,
    symbol,
    FIRST(price, time) AS open,
    MAX(price) AS high,
    MIN(price) AS low,
    LAST(price, time) AS close,
    SUM(volume) AS volume
FROM market_ticks
GROUP BY time_bucket('5 minutes', time), symbol
WITH NO DATA;

-- SELECT add_continuous_aggregate_policy('market_candles_5m_view',
--    start_offset => INTERVAL '2 hours',
--    end_offset => INTERVAL '5 minutes',
--    schedule_interval => INTERVAL '5 minutes');

-- COMMENT ON MATERIALIZED VIEW market_candles_5m_view IS 
-- '5-minute candles aggregated from market_ticks.';

-- ============================================================================
-- 3. 1-Hour Candles (1h)
-- ============================================================================
CREATE MATERIALIZED VIEW market_candles_1h_view
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS time,
    symbol,
    FIRST(price, time) AS open,
    MAX(price) AS high,
    MIN(price) AS low,
    LAST(price, time) AS close,
    SUM(volume) AS volume
FROM market_ticks
GROUP BY time_bucket('1 hour', time), symbol
WITH NO DATA;

-- SELECT add_continuous_aggregate_policy('market_candles_1h_view',
--    start_offset => INTERVAL '2 days',
--    end_offset => INTERVAL '1 hour',
--    schedule_interval => INTERVAL '1 hour');

-- COMMENT ON MATERIALIZED VIEW market_candles_1h_view IS 
-- '1-hour candles aggregated from market_ticks.';

-- ============================================================================
-- 4. Daily Candles (1d)
-- ============================================================================
CREATE MATERIALIZED VIEW market_candles_1d_view
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS time,
    symbol,
    FIRST(price, time) AS open,
    MAX(price) AS high,
    MIN(price) AS low,
    LAST(price, time) AS close,
    SUM(volume) AS volume
FROM market_ticks
GROUP BY time_bucket('1 day', time), symbol
WITH NO DATA;

-- SELECT add_continuous_aggregate_policy('market_candles_1d_view',
--     start_offset => INTERVAL '7 days',
--     end_offset => INTERVAL '1 day',
--     schedule_interval => INTERVAL '1 day');

-- COMMENT ON MATERIALIZED VIEW market_candles_1d_view IS 
-- 'Daily candles aggregated from market_ticks.';
