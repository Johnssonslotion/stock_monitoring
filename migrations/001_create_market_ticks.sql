-- Migration: Create market_ticks and system_metrics
-- Description: 실시간 틱 데이터 및 시스템 상테 저장을 위한 테이블 생성
-- Author: Antigravity AI
-- Date: 2026-01-21

-- 1. market_ticks
CREATE TABLE IF NOT EXISTS public.market_ticks (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    change DOUBLE PRECISION,
    broker TEXT,
    broker_time TIMESTAMPTZ,
    received_time TIMESTAMPTZ DEFAULT NOW(),
    sequence_number BIGINT,
    source TEXT DEFAULT 'KIS'
);

SELECT create_hypertable('market_ticks', 'time', if_not_exists => TRUE);

-- 2. system_metrics (for Sentinel etc)
CREATE TABLE IF NOT EXISTS public.system_metrics (
    time TIMESTAMPTZ NOT NULL,
    metric_name TEXT NOT NULL,
    value DOUBLE PRECISION,
    labels JSONB
);

SELECT create_hypertable('system_metrics', 'time', if_not_exists => TRUE);

-- 3. data_quality_metrics
CREATE TABLE IF NOT EXISTS public.data_quality_metrics (
    date DATE PRIMARY KEY,
    total_ticks BIGINT,
    symbol_coverage INTEGER,
    expected_symbols INTEGER,
    first_tick_time TIMESTAMPTZ,
    last_tick_time TIMESTAMPTZ,
    market_hours_coverage NUMERIC,
    status TEXT,
    gap_hours INTEGER[],
    orderbook_count BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
