-- Migration: Baseline Schema (Cleaned)
-- Description: Core tables for market data (Minutes, Candles)
-- Author: Antigravity AI
-- Date: 2026-01-21

-- 1. Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 2. market_minutes
CREATE TABLE IF NOT EXISTS public.market_minutes (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    UNIQUE (time, symbol)
);

SELECT create_hypertable('market_minutes', 'time', if_not_exists => TRUE);

-- 3. market_candles
CREATE TABLE IF NOT EXISTS public.market_candles (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume DOUBLE PRECISION
);

SELECT create_hypertable('market_candles', 'time', if_not_exists => TRUE);
