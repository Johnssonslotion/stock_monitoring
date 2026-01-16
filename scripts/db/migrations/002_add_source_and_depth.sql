-- Migration: Add Source Column and Extend Orderbook to 10 Depth
-- Created: 2026-01-16

-- 1. Add 'source' column to identifying data origin (KIS vs Kiwoom)
-- Default to 'KIS' for existing data
ALTER TABLE market_ticks ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'KIS';
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'KIS';

-- 2. Extend Orderbook to 10 Depth (Add Ask/Bid 6~10)
-- Ask Price/Vol 6~10
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS ask_price6 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS ask_vol6 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS ask_price7 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS ask_vol7 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS ask_price8 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS ask_vol8 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS ask_price9 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS ask_vol9 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS ask_price10 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS ask_vol10 DOUBLE PRECISION;

-- Bid Price/Vol 6~10
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS bid_price6 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS bid_vol6 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS bid_price7 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS bid_vol7 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS bid_price8 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS bid_vol8 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS bid_price9 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS bid_vol9 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS bid_price10 DOUBLE PRECISION;
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS bid_vol10 DOUBLE PRECISION;

-- 3. Update Indexes (Optional but recommended if source querying is frequent)
-- CREATE INDEX IF NOT EXISTS idx_market_ticks_source ON market_ticks (source, time DESC);
