-- Migration: Add market_orderbook table (Fix Gap Analysis)
-- Created: 2026-01-17
-- Description: 000_baseline에 누락된 호가(Orderbook) 테이블 추가

-- 1. Create Table
CREATE TABLE IF NOT EXISTS public.market_orderbook (
    "time" TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    total_ask_qty DOUBLE PRECISION,
    total_bid_qty DOUBLE PRECISION,
    ask_prices DOUBLE PRECISION[], -- Array of 10 levels
    ask_volumes DOUBLE PRECISION[],
    bid_prices DOUBLE PRECISION[],
    bid_volumes DOUBLE PRECISION[],
    CONSTRAINT market_orderbook_pkey PRIMARY KEY ("time", symbol)
);

-- 2. Convert to Hypertable (TimescaleDB)
-- chunk_time_interval: 1 day (호가 데이터는 용량이 크므로)
SELECT create_hypertable(
    'market_orderbook',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- 3. Set Compression Policy (After 7 days)
ALTER TABLE market_orderbook SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy('market_orderbook', INTERVAL '7 days');
