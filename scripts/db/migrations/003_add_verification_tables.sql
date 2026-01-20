-- [RFC-008] Minute Data Verification Tables

-- 1. Raw Verification Data (From KIS/Kiwoom REST APIs)
CREATE TABLE IF NOT EXISTS market_verification_raw (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    provider TEXT NOT NULL, -- 'KIS', 'KIWOOM'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Convert to Hypertable
SELECT create_hypertable('market_verification_raw', 'time', if_not_exists => TRUE);

-- Index for faster lookup
CREATE INDEX IF NOT EXISTS idx_verification_raw_sym_time ON market_verification_raw (symbol, time DESC, provider);

-- 2. Final Verification Results
CREATE TABLE IF NOT EXISTS market_verification_results (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    local_close DOUBLE PRECISION,    -- From DuckDB Aggregation
    kis_close DOUBLE PRECISION,      -- From KIS REST
    kiwoom_close DOUBLE PRECISION,   -- From Kiwoom REST
    local_vol DOUBLE PRECISION,      -- From DuckDB Aggregation
    kis_vol DOUBLE PRECISION,        -- From KIS REST
    kiwoom_vol DOUBLE PRECISION,     -- From Kiwoom REST
    price_delta_kis DOUBLE PRECISION, 
    price_delta_kiwoom DOUBLE PRECISION,
    vol_delta_kis DOUBLE PRECISION,
    vol_delta_kiwoom DOUBLE PRECISION,
    status TEXT,                     -- 'MATCH', 'MISMATCH', 'MISSING_PROVIDER'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Convert to Hypertable
SELECT create_hypertable('market_verification_results', 'time', if_not_exists => TRUE);

-- Index
CREATE INDEX IF NOT EXISTS idx_verification_res_sym_time ON market_verification_results (symbol, time DESC);
