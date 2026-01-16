-- Migration: Add Timestamp Layers and Deduplication Support
-- Description: 타임스탬프 3계층 구조 추가 및 중복 데이터 방지 인덱스 생성
-- Author: Antigravity AI
-- Date: 2026-01-16

-- 1. market_ticks 테이블에 타임스탬프 계층 추가
ALTER TABLE market_ticks
    ADD COLUMN IF NOT EXISTS broker_time TIMESTAMPTZ COMMENT '브로커가 제공한 원본 시간',
    ADD COLUMN IF NOT EXISTS received_time TIMESTAMPTZ DEFAULT NOW() COMMENT '서버 수신 시간 (Primary Key 기준)',
    ADD COLUMN IF NOT EXISTS sequence_number BIGINT COMMENT '브로커별 시퀀스 번호 (중복 방지용)';

-- 2. 기존 time 컬럼을 stored_time으로 의미 변경
COMMENT ON COLUMN market_ticks.time IS 'DB 저장 시간 (TimescaleDB Hypertable 파티션 키)';

-- 3. sequence_number에 대한 자동 증가 시퀀스 생성
CREATE SEQUENCE IF NOT EXISTS market_ticks_seq_kis START 1;
CREATE SEQUENCE IF NOT EXISTS market_ticks_seq_mirae START 1;
CREATE SEQUENCE IF NOT EXISTS market_ticks_seq_kiwoom_re START 1;

-- 4. 중복 방지 유니크 인덱스 (broker + symbol + sequence_number)
CREATE UNIQUE INDEX IF NOT EXISTS idx_market_ticks_dedup
    ON market_ticks(broker, symbol, sequence_number)
    WHERE sequence_number IS NOT NULL;

-- 5. received_time 기반 조회 성능 최적화 인덱스
CREATE INDEX IF NOT EXISTS idx_market_ticks_received_time
    ON market_ticks(received_time DESC, symbol);

-- 6. Time Bucket 집계용 인덱스 (1분 단위)
CREATE INDEX IF NOT EXISTS idx_market_ticks_time_bucket
    ON market_ticks(time_bucket('1 minute', received_time), symbol);

-- 7. broker별 레이턴시 분석용 인덱스
CREATE INDEX IF NOT EXISTS idx_market_ticks_broker_latency
    ON market_ticks(broker, received_time)
    INCLUDE (broker_time);

-- 8. market_orderbook 테이블에도 동일 구조 적용
ALTER TABLE market_orderbook
    ADD COLUMN IF NOT EXISTS broker_time TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS received_time TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS sequence_number BIGINT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_market_orderbook_dedup
    ON market_orderbook(broker, symbol, sequence_number)
    WHERE sequence_number IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_market_orderbook_received_time
    ON market_orderbook(received_time DESC, symbol);

-- 9. 기존 데이터 마이그레이션 (received_time이 NULL인 경우 time으로 채움)
UPDATE market_ticks
SET received_time = time
WHERE received_time IS NULL;

UPDATE market_orderbook
SET received_time = time
WHERE received_time IS NULL;

-- 10. 통계 정보 업데이트
ANALYZE market_ticks;
ANALYZE market_orderbook;

-- Migration 완료 확인
DO $$
BEGIN
    RAISE NOTICE 'Migration 003 completed successfully';
    RAISE NOTICE 'Added columns: broker_time, received_time, sequence_number';
    RAISE NOTICE 'Created indexes: dedup, received_time, time_bucket, broker_latency';
END $$;
