-- Migration: Create Serving Views for API/UI
-- Description: [ISSUE-044] Ground Truth Policy - Union Priority Logic for data serving
-- Author: Antigravity AI (Council of Six Approved)
-- Date: 2026-01-28
--
-- 이 Migration은 API/Dashboard에서 사용할 통합 뷰를 생성합니다.
-- Ground Truth Policy에 따라 데이터 우선순위를 적용합니다:
-- 1순위: REST API 분봉 (market_candles, source_type = REST_API_*)
-- 2순위: 틱 집계 분봉 (market_candles_1m_view)

-- ============================================
-- Step 1: 1분봉 통합 서빙 뷰
-- ============================================
-- REST API 원본이 있으면 우선 사용, 없으면 틱 집계 사용

CREATE OR REPLACE VIEW market_candles_1m_serving AS
WITH combined AS (
    -- Priority 1: REST API Ground Truth
    SELECT
        time,
        symbol,
        open,
        high,
        low,
        close,
        volume,
        source_type,
        1 as priority
    FROM market_candles
    WHERE source_type IN ('REST_API_KIS', 'REST_API_KIWOOM')
      AND interval = '1m'

    UNION ALL

    -- Priority 2: Tick Aggregation (from Continuous Aggregate)
    SELECT
        time,
        symbol,
        open,
        high,
        low,
        close,
        volume,
        'TICK_AGGREGATION' as source_type,
        2 as priority
    FROM market_candles_1m_view
)
SELECT DISTINCT ON (time, symbol)
    time,
    symbol,
    open,
    high,
    low,
    close,
    volume,
    source_type
FROM combined
ORDER BY time, symbol, priority;

COMMENT ON VIEW market_candles_1m_serving IS
    '[ISSUE-044] API/UI 서빙용 1분봉 통합 뷰.
    Ground Truth Policy에 따라 REST API 원본 우선, 없으면 틱 집계 사용.';

-- ============================================
-- Step 2: 5분봉 통합 서빙 뷰
-- ============================================

CREATE OR REPLACE VIEW market_candles_5m_serving AS
WITH combined AS (
    SELECT
        time,
        symbol,
        open,
        high,
        low,
        close,
        volume,
        source_type,
        1 as priority
    FROM market_candles
    WHERE source_type IN ('REST_API_KIS', 'REST_API_KIWOOM')
      AND interval = '5m'

    UNION ALL

    SELECT
        time,
        symbol,
        open,
        high,
        low,
        close,
        volume,
        'TICK_AGGREGATION' as source_type,
        2 as priority
    FROM market_candles_5m_view
)
SELECT DISTINCT ON (time, symbol)
    time,
    symbol,
    open,
    high,
    low,
    close,
    volume,
    source_type
FROM combined
ORDER BY time, symbol, priority;

-- ============================================
-- Step 3: 1시간봉 통합 서빙 뷰
-- ============================================

CREATE OR REPLACE VIEW market_candles_1h_serving AS
WITH combined AS (
    SELECT
        time,
        symbol,
        open,
        high,
        low,
        close,
        volume,
        source_type,
        1 as priority
    FROM market_candles
    WHERE source_type IN ('REST_API_KIS', 'REST_API_KIWOOM')
      AND interval = '1h'

    UNION ALL

    SELECT
        time,
        symbol,
        open,
        high,
        low,
        close,
        volume,
        'TICK_AGGREGATION' as source_type,
        2 as priority
    FROM market_candles_1h_view
)
SELECT DISTINCT ON (time, symbol)
    time,
    symbol,
    open,
    high,
    low,
    close,
    volume,
    source_type
FROM combined
ORDER BY time, symbol, priority;

-- ============================================
-- Step 4: 1일봉 통합 서빙 뷰
-- ============================================

CREATE OR REPLACE VIEW market_candles_1d_serving AS
WITH combined AS (
    SELECT
        time,
        symbol,
        open,
        high,
        low,
        close,
        volume,
        source_type,
        1 as priority
    FROM market_candles
    WHERE source_type IN ('REST_API_KIS', 'REST_API_KIWOOM')
      AND interval = '1d'

    UNION ALL

    SELECT
        time,
        symbol,
        open,
        high,
        low,
        close,
        volume,
        'TICK_AGGREGATION' as source_type,
        2 as priority
    FROM market_candles_1d_view
)
SELECT DISTINCT ON (time, symbol)
    time,
    symbol,
    open,
    high,
    low,
    close,
    volume,
    source_type
FROM combined
ORDER BY time, symbol, priority;

-- ============================================
-- Step 5: 데이터 품질 모니터링 뷰
-- ============================================

CREATE OR REPLACE VIEW candle_data_quality AS
SELECT
    date_trunc('day', time) as date,
    symbol,
    COUNT(*) FILTER (WHERE source_type IN ('REST_API_KIS', 'REST_API_KIWOOM')) as rest_api_count,
    COUNT(*) FILTER (WHERE source_type = 'TICK_AGGREGATION') as tick_agg_count,
    COUNT(*) as total_count,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE source_type IN ('REST_API_KIS', 'REST_API_KIWOOM')) / NULLIF(COUNT(*), 0),
        2
    ) as ground_truth_pct
FROM market_candles_1m_serving
GROUP BY date_trunc('day', time), symbol
ORDER BY date DESC, symbol;

COMMENT ON VIEW candle_data_quality IS
    '[ISSUE-044] 일별/종목별 분봉 데이터 품질 모니터링.
    ground_truth_pct: REST API 원본 비율 (100%면 완벽한 Ground Truth)';

-- ============================================
-- Step 6: Refresh Status 모니터링 뷰
-- ============================================

CREATE OR REPLACE VIEW continuous_aggregate_status AS
SELECT
    view_name,
    materialization_hypertable_schema,
    materialization_hypertable_name,
    view_definition
FROM timescaledb_information.continuous_aggregates
WHERE view_name LIKE 'market_candles_%_view'
ORDER BY view_name;

COMMENT ON VIEW continuous_aggregate_status IS
    '[ISSUE-044] Continuous Aggregates 상태 모니터링 뷰';
