-- Up Migration
CREATE TABLE IF NOT EXISTS market_ticks_imputed (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    volume BIGINT NOT NULL,
    source TEXT NOT NULL, -- 'KIS' or 'KIWOOM' (The target source)
    execution_no TEXT,
    imputed_from TEXT, -- Source of the data (e.g. 'KIWOOM' -> filled KIS gap)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (time, symbol, source, execution_no)
);

-- Hypertable
SELECT create_hypertable('market_ticks_imputed', 'time', if_not_exists => TRUE);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ticks_imputed_symbol_time ON market_ticks_imputed (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_ticks_imputed_source ON market_ticks_imputed (source, time DESC);
