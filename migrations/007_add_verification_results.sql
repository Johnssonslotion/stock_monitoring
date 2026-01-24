-- Migration: Add market_verification_results table
-- Description: [RFC-008 Extension] Auto-recovery system with DB audit trail
-- Author: OpenCode AI Assistant
-- Date: 2026-01-23

-- 1. Create verification results table
CREATE TABLE IF NOT EXISTS public.market_verification_results (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    kis_vol DOUBLE PRECISION,
    kiwoom_vol DOUBLE PRECISION,
    vol_delta_kis DOUBLE PRECISION,
    vol_delta_kiwoom DOUBLE PRECISION,
    status TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. Convert to hypertable for time-series optimization
SELECT create_hypertable(
    'public.market_verification_results', 
    'time', 
    if_not_exists => TRUE,
    migrate_data => TRUE
);

-- 3. Add indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_verification_symbol_time 
ON public.market_verification_results (symbol, time DESC);

CREATE INDEX IF NOT EXISTS idx_verification_status 
ON public.market_verification_results (status, time DESC);

CREATE INDEX IF NOT EXISTS idx_verification_created_at 
ON public.market_verification_results (created_at DESC);

-- 4. Add table comment
COMMENT ON TABLE public.market_verification_results IS 
'[RFC-008 Extension] KIS vs Kiwoom cross-validation results with auto-recovery trigger.
Stores verification results from verification-worker for data quality monitoring.
Status values: PASS, NEEDS_RECOVERY, ERROR, NO_DATA_KIS, NO_DATA_KIWOOM';

-- 5. Add column comments
COMMENT ON COLUMN public.market_verification_results.time IS 
'Target verification time (the minute being verified)';

COMMENT ON COLUMN public.market_verification_results.symbol IS 
'Stock symbol (e.g., 005930 for Samsung)';

COMMENT ON COLUMN public.market_verification_results.kis_vol IS 
'Volume from KIS API (ground truth reference)';

COMMENT ON COLUMN public.market_verification_results.kiwoom_vol IS 
'Volume from Kiwoom API (ground truth reference)';

COMMENT ON COLUMN public.market_verification_results.vol_delta_kis IS 
'Delta percentage: |KIS - Kiwoom| / max(KIS, Kiwoom). Triggers recovery if >= 0.1%';

COMMENT ON COLUMN public.market_verification_results.vol_delta_kiwoom IS 
'Delta percentage: |Kiwoom - KIS| / max(KIS, Kiwoom). Same as vol_delta_kis';

COMMENT ON COLUMN public.market_verification_results.status IS 
'Verification status: PASS, NEEDS_RECOVERY, ERROR, NO_DATA_KIS, NO_DATA_KIWOOM';

COMMENT ON COLUMN public.market_verification_results.created_at IS 
'Timestamp when verification result was recorded';

-- 6. Update table statistics
ANALYZE public.market_verification_results;
