-- Migration: 007_pillar8_market_intelligence.sql
-- Description: Pillar 8 Market Intelligence tables for investor trends, short selling, program trading
-- RFC: RFC-010
-- Created: 2026-01-29
-- Author: AI Developer

-- ============================================================================
-- 1. 투자자별 매매동향 테이블 (Investor Trends)
-- ============================================================================

CREATE TABLE IF NOT EXISTS investor_trends (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    -- 외국인
    foreign_buy BIGINT,              -- 외국인 매수량
    foreign_sell BIGINT,             -- 외국인 매도량
    foreign_net BIGINT,              -- 외국인 순매수
    foreign_amount BIGINT,           -- 외국인 거래대금
    -- 기관
    institution_buy BIGINT,          -- 기관 매수량
    institution_sell BIGINT,         -- 기관 매도량
    institution_net BIGINT,          -- 기관 순매수
    institution_amount BIGINT,       -- 기관 거래대금
    -- 개인
    retail_buy BIGINT,               -- 개인 매수량
    retail_sell BIGINT,              -- 개인 매도량
    retail_net BIGINT,               -- 개인 순매수
    retail_amount BIGINT,            -- 개인 거래대금
    -- 메타
    source TEXT DEFAULT 'KIS',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT pk_investor_trends PRIMARY KEY (time, symbol)
);

-- TimescaleDB Hypertable 변환
SELECT create_hypertable('investor_trends', 'time', if_not_exists => TRUE);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_investor_trends_symbol_time
ON investor_trends (symbol, time DESC);

CREATE INDEX IF NOT EXISTS idx_investor_trends_foreign_net
ON investor_trends (foreign_net DESC)
WHERE foreign_net IS NOT NULL;

-- 30일 Retention Policy
SELECT add_retention_policy('investor_trends', INTERVAL '30 days', if_not_exists => TRUE);

COMMENT ON TABLE investor_trends IS 'Pillar 8: 투자자별(외국인/기관/개인) 매매동향 데이터';

-- ============================================================================
-- 2. 공매도 현황 테이블 (Short Selling)
-- ============================================================================

CREATE TABLE IF NOT EXISTS short_selling (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    -- 공매도 거래
    short_volume BIGINT,             -- 공매도 거래량
    short_amount BIGINT,             -- 공매도 거래대금
    short_ratio DECIMAL(5,2),        -- 공매도 비율 (%)
    -- 공매도 잔고
    balance_volume BIGINT,           -- 공매도 잔고
    balance_amount BIGINT,           -- 잔고 금액
    balance_ratio DECIMAL(5,2),      -- 잔고 비율 (%)
    -- 대차거래
    lending_volume BIGINT,           -- 대차 거래량
    lending_balance BIGINT,          -- 대차 잔고
    -- 메타
    source TEXT DEFAULT 'KIS',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT pk_short_selling PRIMARY KEY (time, symbol)
);

-- TimescaleDB Hypertable 변환
SELECT create_hypertable('short_selling', 'time', if_not_exists => TRUE);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_short_selling_symbol_time
ON short_selling (symbol, time DESC);

-- 공매도 과열 종목 필터 인덱스 (공매도 비율 20% 초과)
CREATE INDEX IF NOT EXISTS idx_short_selling_overheat
ON short_selling (short_ratio DESC)
WHERE short_ratio > 20;

-- 30일 Retention Policy
SELECT add_retention_policy('short_selling', INTERVAL '30 days', if_not_exists => TRUE);

COMMENT ON TABLE short_selling IS 'Pillar 8: 공매도 일별 거래량 및 잔고 현황';

-- ============================================================================
-- 3. 프로그램 매매 테이블 (Program Trading)
-- ============================================================================

CREATE TABLE IF NOT EXISTS program_trading (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    -- 차익 거래
    arb_buy BIGINT,                  -- 차익 매수
    arb_sell BIGINT,                 -- 차익 매도
    arb_net BIGINT,                  -- 차익 순매수
    arb_amount BIGINT,               -- 차익 거래대금
    -- 비차익 거래
    non_arb_buy BIGINT,              -- 비차익 매수
    non_arb_sell BIGINT,             -- 비차익 매도
    non_arb_net BIGINT,              -- 비차익 순매수
    non_arb_amount BIGINT,           -- 비차익 거래대금
    -- 합계
    total_buy BIGINT,                -- 전체 매수
    total_sell BIGINT,               -- 전체 매도
    total_net BIGINT,                -- 전체 순매수
    -- 메타
    source TEXT DEFAULT 'KIS',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT pk_program_trading PRIMARY KEY (time, symbol)
);

-- TimescaleDB Hypertable 변환
SELECT create_hypertable('program_trading', 'time', if_not_exists => TRUE);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_program_trading_symbol_time
ON program_trading (symbol, time DESC);

CREATE INDEX IF NOT EXISTS idx_program_trading_total_net
ON program_trading (total_net DESC)
WHERE total_net IS NOT NULL;

-- 30일 Retention Policy
SELECT add_retention_policy('program_trading', INTERVAL '30 days', if_not_exists => TRUE);

COMMENT ON TABLE program_trading IS 'Pillar 8: 프로그램매매(차익/비차익) 현황';

-- ============================================================================
-- 4. 섹터 순환매 분석 테이블 (Sector Rotation)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sector_rotation (
    time TIMESTAMPTZ NOT NULL,
    sector_code TEXT NOT NULL,
    sector_name TEXT,
    -- 자금 흐름 지표
    money_flow_index DECIMAL(10,2),  -- 자금 유입도 지수 (MFI)
    volume_flow BIGINT,              -- 거래량 흐름
    amount_flow BIGINT,              -- 거래대금 흐름
    -- 투자자별 순매수 합계
    foreign_flow BIGINT,             -- 외국인 순매수 합계
    institution_flow BIGINT,         -- 기관 순매수 합계
    retail_flow BIGINT,              -- 개인 순매수 합계
    -- 변동성
    price_change_pct DECIMAL(6,2),   -- 가격 변동률 (%)
    volume_change_pct DECIMAL(6,2),  -- 거래량 증감률 (%)
    -- 시그널
    rotation_signal TEXT,            -- INFLOW / OUTFLOW / NEUTRAL
    signal_strength DECIMAL(5,2),    -- 시그널 강도 (0~100)
    -- 메타
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT pk_sector_rotation PRIMARY KEY (time, sector_code)
);

-- TimescaleDB Hypertable 변환
SELECT create_hypertable('sector_rotation', 'time', if_not_exists => TRUE);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_sector_rotation_sector_time
ON sector_rotation (sector_code, time DESC);

CREATE INDEX IF NOT EXISTS idx_sector_rotation_signal
ON sector_rotation (rotation_signal, signal_strength DESC)
WHERE rotation_signal != 'NEUTRAL';

-- 90일 Retention Policy (섹터 분석은 더 긴 기간 필요)
SELECT add_retention_policy('sector_rotation', INTERVAL '90 days', if_not_exists => TRUE);

COMMENT ON TABLE sector_rotation IS 'Pillar 8: 섹터별 순환매 분석 및 자금 흐름';

-- ============================================================================
-- 5. 섹터 마스터 테이블 (참조 테이블)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sector_master (
    sector_code TEXT PRIMARY KEY,
    sector_name TEXT NOT NULL,
    sector_name_en TEXT,
    parent_sector_code TEXT,         -- 상위 섹터 코드 (계층 구조)
    market TEXT DEFAULT 'KOSPI',     -- KOSPI / KOSDAQ
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 기본 섹터 데이터 (KRX 업종분류 기준)
INSERT INTO sector_master (sector_code, sector_name, sector_name_en, market) VALUES
    ('001', '종합', 'Total Market', 'KOSPI'),
    ('002', '대형주', 'Large Cap', 'KOSPI'),
    ('003', '중형주', 'Mid Cap', 'KOSPI'),
    ('004', '소형주', 'Small Cap', 'KOSPI'),
    ('005', '음식료품', 'Food & Beverage', 'KOSPI'),
    ('006', '섬유의복', 'Textile & Apparel', 'KOSPI'),
    ('007', '종이목재', 'Paper & Wood', 'KOSPI'),
    ('008', '화학', 'Chemicals', 'KOSPI'),
    ('009', '의약품', 'Pharmaceuticals', 'KOSPI'),
    ('010', '비금속광물', 'Non-Metallic Minerals', 'KOSPI'),
    ('011', '철강금속', 'Iron & Steel', 'KOSPI'),
    ('012', '기계', 'Machinery', 'KOSPI'),
    ('013', '전기전자', 'Electrical & Electronics', 'KOSPI'),
    ('014', '의료정밀', 'Medical Precision', 'KOSPI'),
    ('015', '운수장비', 'Transportation Equipment', 'KOSPI'),
    ('016', '유통업', 'Wholesale & Retail', 'KOSPI'),
    ('017', '전기가스업', 'Utilities', 'KOSPI'),
    ('018', '건설업', 'Construction', 'KOSPI'),
    ('019', '운수창고', 'Transportation & Logistics', 'KOSPI'),
    ('020', '통신업', 'Telecommunications', 'KOSPI'),
    ('021', '금융업', 'Financials', 'KOSPI'),
    ('022', '은행', 'Banks', 'KOSPI'),
    ('023', '증권', 'Securities', 'KOSPI'),
    ('024', '보험', 'Insurance', 'KOSPI'),
    ('025', '서비스업', 'Services', 'KOSPI'),
    ('026', '제조업', 'Manufacturing', 'KOSPI')
ON CONFLICT (sector_code) DO NOTHING;

COMMENT ON TABLE sector_master IS 'Pillar 8: 섹터 마스터 데이터 (KRX 업종분류)';

-- ============================================================================
-- 6. 종목-섹터 매핑 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS symbol_sector_map (
    symbol TEXT NOT NULL,
    sector_code TEXT NOT NULL,
    weight DECIMAL(5,2) DEFAULT 100, -- 해당 섹터 내 비중 (%)
    is_primary BOOLEAN DEFAULT TRUE, -- 주요 섹터 여부
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT pk_symbol_sector PRIMARY KEY (symbol, sector_code),
    CONSTRAINT fk_sector FOREIGN KEY (sector_code) REFERENCES sector_master(sector_code)
);

CREATE INDEX IF NOT EXISTS idx_symbol_sector_symbol
ON symbol_sector_map (symbol);

CREATE INDEX IF NOT EXISTS idx_symbol_sector_sector
ON symbol_sector_map (sector_code);

COMMENT ON TABLE symbol_sector_map IS 'Pillar 8: 종목-섹터 매핑 테이블';

-- ============================================================================
-- Migration Complete
-- ============================================================================

-- 검증 쿼리
DO $$
BEGIN
    RAISE NOTICE 'Migration 007_pillar8_market_intelligence completed.';
    RAISE NOTICE 'Tables created: investor_trends, short_selling, program_trading, sector_rotation, sector_master, symbol_sector_map';
END $$;
