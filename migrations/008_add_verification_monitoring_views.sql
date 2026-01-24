-- Migration: Add monitoring views for verification health
-- Description: [RFC-008 Extension] SQL views for verification system monitoring
-- Author: OpenCode AI Assistant
-- Date: 2026-01-23

-- ============================================================================
-- View 1: Daily Verification Summary
-- ============================================================================
-- Purpose: High-level daily statistics for verification system health
-- Usage: SELECT * FROM verification_daily_summary ORDER BY date DESC LIMIT 7;

CREATE OR REPLACE VIEW public.verification_daily_summary AS
SELECT 
    date_trunc('day', time)::date as date,
    COUNT(*) as total_verifications,
    SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
    SUM(CASE WHEN status = 'NEEDS_RECOVERY' THEN 1 ELSE 0 END) as gaps_detected,
    SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) as errors,
    SUM(CASE WHEN status IN ('NO_DATA_KIS', 'NO_DATA_KIWOOM') THEN 1 ELSE 0 END) as no_data,
    ROUND((AVG(vol_delta_kis) * 100)::numeric, 4) as avg_delta_pct,
    ROUND((MAX(vol_delta_kis) * 100)::numeric, 4) as max_delta_pct,
    ROUND(
        (100.0 * SUM(CASE WHEN status = 'NEEDS_RECOVERY' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0))::numeric,
        2
    ) as gap_rate_pct
FROM public.market_verification_results
GROUP BY date_trunc('day', time)
ORDER BY date DESC;

COMMENT ON VIEW public.verification_daily_summary IS 
'Daily aggregated statistics for verification system health monitoring.
Shows total checks, pass/fail counts, and gap detection rates by day.';


-- ============================================================================
-- View 2: Gap Detection Rate by Symbol
-- ============================================================================
-- Purpose: Identify symbols with consistently high gap rates (potential data quality issues)
-- Usage: SELECT * FROM verification_gap_rate WHERE gap_rate_pct > 5.0;

CREATE OR REPLACE VIEW public.verification_gap_rate AS
SELECT 
    symbol,
    COUNT(*) as total_checks,
    SUM(CASE WHEN status = 'NEEDS_RECOVERY' THEN 1 ELSE 0 END) as gaps_found,
    SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
    SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) as errors,
    ROUND(
        (100.0 * SUM(CASE WHEN status = 'NEEDS_RECOVERY' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0))::numeric,
        2
    ) as gap_rate_pct,
    ROUND((AVG(vol_delta_kis) * 100)::numeric, 4) as avg_delta_pct,
    MAX(time) as last_checked
FROM public.market_verification_results
WHERE time >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY symbol
ORDER BY gap_rate_pct DESC, total_checks DESC;

COMMENT ON VIEW public.verification_gap_rate IS 
'Gap detection rate per symbol for the last 7 days.
High gap rates (>5%) may indicate data collection issues for specific symbols.';


-- ============================================================================
-- View 3: Recent Verification Results (Last 24 Hours)
-- ============================================================================
-- Purpose: Real-time monitoring of verification activity
-- Usage: SELECT * FROM verification_recent WHERE status = 'NEEDS_RECOVERY';

CREATE OR REPLACE VIEW public.verification_recent AS
SELECT 
    time,
    symbol,
    status,
    kis_vol,
    kiwoom_vol,
    ROUND((vol_delta_kis * 100)::numeric, 4) as delta_pct,
    created_at,
    EXTRACT(EPOCH FROM (created_at - time)) as processing_delay_sec
FROM public.market_verification_results
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
ORDER BY created_at DESC;

COMMENT ON VIEW public.verification_recent IS 
'Recent verification results (last 24 hours) with processing delay.
Useful for real-time monitoring and alerting on recovery triggers.';


-- ============================================================================
-- View 4: Verification System Health Score
-- ============================================================================
-- Purpose: Single metric for overall system health (last 7 days)
-- Usage: SELECT * FROM verification_health_score;

CREATE OR REPLACE VIEW public.verification_health_score AS
SELECT 
    CURRENT_DATE as report_date,
    COUNT(*) as total_checks_7d,
    ROUND(
        (100.0 * SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0))::numeric,
        2
    ) as pass_rate_pct,
    ROUND(
        (100.0 * SUM(CASE WHEN status = 'NEEDS_RECOVERY' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0))::numeric,
        2
    ) as gap_rate_pct,
    ROUND(
        (100.0 * SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0))::numeric,
        2
    ) as error_rate_pct,
    ROUND((AVG(vol_delta_kis) * 100)::numeric, 4) as avg_delta_pct,
    COUNT(DISTINCT symbol) as symbols_checked,
    CASE 
        WHEN 100.0 * SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) >= 99.0 THEN 'HEALTHY'
        WHEN 100.0 * SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) >= 95.0 THEN 'GOOD'
        WHEN 100.0 * SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) >= 90.0 THEN 'FAIR'
        ELSE 'NEEDS_ATTENTION'
    END as health_status
FROM public.market_verification_results
WHERE time >= CURRENT_DATE - INTERVAL '7 days';

COMMENT ON VIEW public.verification_health_score IS 
'Overall verification system health score for the last 7 days.
Health status: HEALTHY (>=99%), GOOD (>=95%), FAIR (>=90%), NEEDS_ATTENTION (<90%).';


-- ============================================================================
-- View 5: Hourly Verification Activity
-- ============================================================================
-- Purpose: Detect hourly patterns and anomalies in verification activity
-- Usage: SELECT * FROM verification_hourly WHERE date = CURRENT_DATE;

CREATE OR REPLACE VIEW public.verification_hourly AS
SELECT 
    date_trunc('day', time)::date as date,
    EXTRACT(HOUR FROM time) as hour,
    COUNT(*) as checks_count,
    SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
    SUM(CASE WHEN status = 'NEEDS_RECOVERY' THEN 1 ELSE 0 END) as gaps,
    ROUND((AVG(vol_delta_kis) * 100)::numeric, 4) as avg_delta_pct,
    COUNT(DISTINCT symbol) as unique_symbols
FROM public.market_verification_results
WHERE time >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY date_trunc('day', time), EXTRACT(HOUR FROM time)
ORDER BY date DESC, hour DESC;

COMMENT ON VIEW public.verification_hourly IS 
'Hourly aggregation of verification activity for pattern analysis.
Shows verification counts by hour for the last 7 days.';


-- ============================================================================
-- View 6: Recovery Task Performance
-- ============================================================================
-- Purpose: Monitor recovery task effectiveness (requires joining with market_ticks)
-- Usage: SELECT * FROM verification_recovery_performance WHERE date >= CURRENT_DATE - 7;

CREATE OR REPLACE VIEW public.verification_recovery_performance AS
WITH recovery_tasks AS (
    SELECT 
        date_trunc('day', time)::date as date,
        COUNT(*) as gaps_detected,
        array_agg(DISTINCT symbol) as symbols_with_gaps
    FROM public.market_verification_results
    WHERE status = 'NEEDS_RECOVERY'
        AND time >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY date_trunc('day', time)
),
recovered_ticks AS (
    SELECT 
        date_trunc('day', time)::date as date,
        COUNT(DISTINCT (symbol, time)) as ticks_recovered
    FROM public.market_ticks
    WHERE source = 'KIS_RECOVERY'
        AND time >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY date_trunc('day', time)
)
SELECT 
    COALESCE(r.date, t.date) as date,
    COALESCE(r.gaps_detected, 0) as gaps_detected,
    COALESCE(t.ticks_recovered, 0) as ticks_recovered,
    CASE 
        WHEN r.gaps_detected > 0 THEN 
            ROUND((100.0 * t.ticks_recovered / r.gaps_detected)::numeric, 2)
        ELSE NULL
    END as recovery_success_rate_pct,
    r.symbols_with_gaps
FROM recovery_tasks r
FULL OUTER JOIN recovered_ticks t ON r.date = t.date
ORDER BY date DESC;

COMMENT ON VIEW public.verification_recovery_performance IS 
'Recovery task effectiveness tracking (last 30 days).
Shows gap detection vs actual recovery completion rate.';
