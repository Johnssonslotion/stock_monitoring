-- Migration: Add market_orderbook table (Fix Gap Analysis & Alignment)
-- Created: 2026-01-21 (Verified with Prod DB)
-- Description: 실제 운영 DB 구조와 100% 일치하는 호가 테이블 명세 (Metadata 포함)

-- 1. Create Table
CREATE TABLE IF NOT EXISTS public.market_orderbook (
    "time" TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    broker TEXT,
    broker_time TIMESTAMPTZ,
    received_time TIMESTAMPTZ DEFAULT NOW(),
    sequence_number BIGINT,
    source TEXT DEFAULT 'KIS',
    ask_price1 DOUBLE PRECISION, ask_vol1 DOUBLE PRECISION,
    ask_price2 DOUBLE PRECISION, ask_vol2 DOUBLE PRECISION,
    ask_price3 DOUBLE PRECISION, ask_vol3 DOUBLE PRECISION,
    ask_price4 DOUBLE PRECISION, ask_vol4 DOUBLE PRECISION,
    ask_price5 DOUBLE PRECISION, ask_vol5 DOUBLE PRECISION,
    ask_price6 DOUBLE PRECISION, ask_vol6 DOUBLE PRECISION,
    ask_price7 DOUBLE PRECISION, ask_vol7 DOUBLE PRECISION,
    ask_price8 DOUBLE PRECISION, ask_vol8 DOUBLE PRECISION,
    ask_price9 DOUBLE PRECISION, ask_vol9 DOUBLE PRECISION,
    ask_price10 DOUBLE PRECISION, ask_vol10 DOUBLE PRECISION,
    bid_price1 DOUBLE PRECISION, bid_vol1 DOUBLE PRECISION,
    bid_price2 DOUBLE PRECISION, bid_vol2 DOUBLE PRECISION,
    bid_price3 DOUBLE PRECISION, bid_vol3 DOUBLE PRECISION,
    bid_price4 DOUBLE PRECISION, bid_vol4 DOUBLE PRECISION,
    bid_price5 DOUBLE PRECISION, bid_vol5 DOUBLE PRECISION,
    bid_price6 DOUBLE PRECISION, bid_vol6 DOUBLE PRECISION,
    bid_price7 DOUBLE PRECISION, bid_vol7 DOUBLE PRECISION,
    bid_price8 DOUBLE PRECISION, bid_vol8 DOUBLE PRECISION,
    bid_price9 DOUBLE PRECISION, bid_vol9 DOUBLE PRECISION,
    bid_price10 DOUBLE PRECISION, bid_vol10 DOUBLE PRECISION,
    CONSTRAINT market_orderbook_pkey PRIMARY KEY ("time", symbol)
);

-- 2. Convert to Hypertable (TimescaleDB)
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
