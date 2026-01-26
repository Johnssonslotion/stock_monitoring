-- Up Migration
-- Add new columns for OHLCV verification
ALTER TABLE market_verification_results
ADD COLUMN IF NOT EXISTS local_vol DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS api_vol DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS price_match BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS details JSONB;

-- Comment on columns
COMMENT ON COLUMN market_verification_results.local_vol IS 'Aggregated Volume from Local Ticks';
COMMENT ON COLUMN market_verification_results.api_vol IS 'Volume from Broker API Candle';
COMMENT ON COLUMN market_verification_results.price_match IS 'Whether OHLC prices match exactly (1e-9 tolerance)';
COMMENT ON COLUMN market_verification_results.details IS 'Detailed mismatch info (high_diff, etc)';
