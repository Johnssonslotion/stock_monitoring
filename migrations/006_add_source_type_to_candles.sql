-- Migration: Add source_type column to market_candles
-- Description: [RFC-009] Ground Truth Policy 구현 - 데이터 출처 및 신뢰도 구분
-- Author: Antigravity AI (Council of Six Approved)
-- Date: 2026-01-22

-- 1. market_candles 테이블에 source_type 컬럼 추가
ALTER TABLE public.market_candles 
    ADD COLUMN IF NOT EXISTS source_type TEXT DEFAULT 'TICK_AGGREGATION_UNVERIFIED';

-- 2. 주석 추가 (Ground Truth Policy 명세)
COMMENT ON COLUMN public.market_candles.source_type IS 
    '[RFC-009] 데이터 출처 및 신뢰도:
    - REST_API_KIS: KIS REST API 분봉 (참값, 1순위)
    - REST_API_KIWOOM: Kiwoom REST API 분봉 (참값, 1순위)
    - TICK_AGGREGATION_VERIFIED: Volume Check 통과한 틱 집계 (준참값, 2순위)
    - TICK_AGGREGATION_UNVERIFIED: 미검증 틱 집계 (임시, 3순위)';

-- 3. Ground Truth 쿼리 최적화를 위한 부분 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_candles_ground_truth 
ON public.market_candles(symbol, time) 
WHERE source_type IN ('REST_API_KIS', 'REST_API_KIWOOM');

-- 4. 기존 데이터의 source_type 추정 업데이트 (안전한 기본값 유지)
-- 기존 데이터는 대부분 틱 집계이므로 UNVERIFIED로 유지
-- 검증 후 수동으로 VERIFIED로 업그레이드 필요

-- 5. 이력 통계 정보 업데이트
ANALYZE public.market_candles;
