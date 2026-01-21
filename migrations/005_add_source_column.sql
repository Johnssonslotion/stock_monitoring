-- Migration: Add source column to market_ticks
-- Description: 데이터 출처(KIS/KIWOOM) 구분을 위한 source 컬럼 공식 추가
-- Date: 2026-01-21

-- 1. market_ticks 테이블에 source 컬럼 추가
ALTER TABLE public.market_ticks 
    ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'KIS';

-- 2. 주석 추가
COMMENT ON COLUMN public.market_ticks.source IS '데이터 출처 (예: KIS, KIWOOM)';

-- 3. 이력 통계 정보 업데이트
ANALYZE public.market_ticks;
