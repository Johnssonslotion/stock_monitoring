-- Daily Data Quality Validation Framework
-- Created: 2026-01-15
-- Purpose: Automated data completeness verification

-- ============================================
-- 1. Quality Metrics Table
-- ============================================
CREATE TABLE IF NOT EXISTS data_quality_metrics (
    date DATE PRIMARY KEY,
    total_ticks BIGINT NOT NULL,
    symbol_coverage INT NOT NULL,
    expected_symbols INT NOT NULL DEFAULT 20,
    first_tick_time TIMESTAMPTZ,
    last_tick_time TIMESTAMPTZ,
    market_hours_coverage DECIMAL(5,2),  -- % of 9:00-15:30 covered
    status VARCHAR(10) CHECK (status IN ('PASS', 'WARN', 'FAIL')),
    gap_hours INT[],  -- Array of hours with <1000 ticks
    orderbook_count BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dqm_status ON data_quality_metrics(status);
CREATE INDEX IF NOT EXISTS idx_dqm_date ON data_quality_metrics(date DESC);

COMMENT ON TABLE data_quality_metrics IS 'Daily data quality validation results';
COMMENT ON COLUMN data_quality_metrics.status IS 'PASS: >100K ticks, WARN: 50K-100K, FAIL: <50K';

-- ============================================
-- 2. Validation Function
-- ============================================
CREATE OR REPLACE FUNCTION calculate_daily_quality(target_date DATE)
RETURNS TABLE(
    total_ticks BIGINT,
    symbol_coverage INT,
    expected_symbols INT,
    first_tick TIMESTAMPTZ,
    last_tick TIMESTAMPTZ,
    market_coverage DECIMAL,
    status TEXT,
    gap_hours INT[]
) AS $$
DECLARE
    market_start TIMESTAMPTZ := (target_date || ' 09:00:00+09')::TIMESTAMPTZ;
    market_end TIMESTAMPTZ := (target_date || ' 15:30:00+09')::TIMESTAMPTZ;
    total_market_hours DECIMAL := 6.5;
    covered_hours DECIMAL;
    low_volume_hours INT[];
BEGIN
    -- Calculate hourly gaps
    SELECT ARRAY_AGG(EXTRACT(HOUR FROM hour_bucket)::INT)
    INTO low_volume_hours
    FROM (
        SELECT 
            DATE_TRUNC('hour', time AT TIME ZONE 'Asia/Seoul') as hour_bucket,
            COUNT(*) as tick_count
        FROM market_ticks
        WHERE time::date = target_date
        GROUP BY hour_bucket
        HAVING COUNT(*) < 1000
    ) sub;
    
    -- Calculate coverage percentage
    SELECT 
        COUNT(DISTINCT DATE_TRUNC('hour', time AT TIME ZONE 'Asia/Seoul'))::DECIMAL / total_market_hours * 100
    INTO covered_hours
    FROM market_ticks
    WHERE time::date = target_date
      AND time AT TIME ZONE 'Asia/Seoul' BETWEEN market_start AND market_end;
    
    -- Main query
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_ticks,
        COUNT(DISTINCT symbol)::INT as symbol_coverage,
        20::INT as expected_symbols,
        MIN(time) as first_tick,
        MAX(time) as last_tick,
        COALESCE(covered_hours, 0) as market_coverage,
        CASE 
            WHEN COUNT(*) >= 100000 AND COUNT(DISTINCT symbol) = 20 THEN 'PASS'
            WHEN COUNT(*) >= 50000 THEN 'WARN'
            ELSE 'FAIL'
        END as status,
        COALESCE(low_volume_hours, ARRAY[]::INT[]) as gap_hours
    FROM market_ticks
    WHERE time::date = target_date;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_daily_quality IS 'Calculate daily data quality metrics for a given date';

-- ============================================
-- 3. Store Quality Metrics Procedure
-- ============================================
CREATE OR REPLACE PROCEDURE store_daily_quality(target_date DATE)
LANGUAGE plpgsql AS $$
DECLARE
    quality_result RECORD;
    orderbook_cnt BIGINT;
BEGIN
    -- Get quality metrics
    SELECT * INTO quality_result
    FROM calculate_daily_quality(target_date);
    
    -- Get orderbook count
    SELECT COUNT(*) INTO orderbook_cnt
    FROM market_orderbook
    WHERE time::date = target_date;
    
    -- Insert or update
    INSERT INTO data_quality_metrics (
        date,
        total_ticks,
        symbol_coverage,
        expected_symbols,
        first_tick_time,
        last_tick_time,
        market_hours_coverage,
        status,
        gap_hours,
        orderbook_count
    ) VALUES (
        target_date,
        quality_result.total_ticks,
        quality_result.symbol_coverage,
        quality_result.expected_symbols,
        quality_result.first_tick,
        quality_result.last_tick,
        quality_result.market_coverage,
        quality_result.status,
        quality_result.gap_hours,
        orderbook_cnt
    )
    ON CONFLICT (date) DO UPDATE SET
        total_ticks = EXCLUDED.total_ticks,
        symbol_coverage = EXCLUDED.symbol_coverage,
        first_tick_time = EXCLUDED.first_tick_time,
        last_tick_time = EXCLUDED.last_tick_time,
        market_hours_coverage = EXCLUDED.market_hours_coverage,
        status = EXCLUDED.status,
        gap_hours = EXCLUDED.gap_hours,
        orderbook_count = EXCLUDED.orderbook_count,
        created_at = NOW();
    
    RAISE NOTICE 'Quality metrics stored for %: % (% ticks, % symbols)', 
        target_date, quality_result.status, quality_result.total_ticks, quality_result.symbol_coverage;
END;
$$;

COMMENT ON PROCEDURE store_daily_quality IS 'Store daily quality metrics to data_quality_metrics table';

-- ============================================
-- 4. Usage Examples
-- ============================================

-- Check today's quality
-- SELECT * FROM calculate_daily_quality(CURRENT_DATE);

-- Check yesterday's quality
-- SELECT * FROM calculate_daily_quality(CURRENT_DATE - 1);

-- Store yesterday's metrics
-- CALL store_daily_quality(CURRENT_DATE - 1);

-- View all quality metrics
-- SELECT * FROM data_quality_metrics ORDER BY date DESC LIMIT 30;

-- Find failed days
-- SELECT date, total_ticks, symbol_coverage, status, gap_hours
-- FROM data_quality_metrics
-- WHERE status = 'FAIL'
-- ORDER BY date DESC;
