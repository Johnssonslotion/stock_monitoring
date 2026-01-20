-- Migration: Create market_ticks_recovery for comparison
CREATE TABLE IF NOT EXISTS market_ticks_recovery (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    source TEXT NOT NULL,
    received_time TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable
SELECT create_hypertable('market_ticks_recovery', 'time', if_not_exists => TRUE);

-- Index for comparison performance
CREATE INDEX IF NOT EXISTS idx_ticks_recovery_lookup ON market_ticks_recovery (symbol, time DESC);
