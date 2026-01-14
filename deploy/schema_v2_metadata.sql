-- Create symbol_metadata table for Phase 2B
CREATE TABLE IF NOT EXISTS symbol_metadata (
    symbol VARCHAR(20) PRIMARY KEY,
    market_cap BIGINT,
    sector VARCHAR(50),
    is_kospi200 BOOLEAN,
    is_halted BOOLEAN DEFAULT FALSE,
    is_managed BOOLEAN DEFAULT FALSE,  -- 관리종목
    is_delisting BOOLEAN DEFAULT FALSE, -- 정리매매
    per FLOAT,
    dividend_yield FLOAT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for filtering
CREATE INDEX IF NOT EXISTS idx_sector ON symbol_metadata(sector);
CREATE INDEX IF NOT EXISTS idx_market_cap ON symbol_metadata(market_cap DESC);
