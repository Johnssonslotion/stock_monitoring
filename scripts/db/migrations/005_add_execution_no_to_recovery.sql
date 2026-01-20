-- Migration: Add execution_no and update unique constraint (Hypertable Compliant)
ALTER TABLE market_ticks_recovery ADD COLUMN IF NOT EXISTS execution_no TEXT;

-- Drop failed or old indices
DROP INDEX IF EXISTS idx_ticks_recovery_dedup;
DROP INDEX IF EXISTS idx_ticks_recovery_execution_dedup;
DROP INDEX IF EXISTS idx_ticks_recovery_fuzzy_dedup;

-- Create Hypertable-compliant unique indices (must include 'time')
-- 1. For sources with execution_no (Kiwoom)
CREATE UNIQUE INDEX IF NOT EXISTS idx_ticks_recovery_execution_dedup 
ON market_ticks_recovery (time, symbol, source, execution_no) 
WHERE execution_no IS NOT NULL;

-- 2. For sources without execution_no (KIS - Fuzzy Dedup)
CREATE UNIQUE INDEX IF NOT EXISTS idx_ticks_recovery_fuzzy_dedup 
ON market_ticks_recovery (time, symbol, price, volume, source) 
WHERE execution_no IS NULL;
