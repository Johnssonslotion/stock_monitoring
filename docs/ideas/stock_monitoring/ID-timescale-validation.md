# IDEA: TimescaleDB-based Minute Validation System
**Status**: 💡 Seed (Idea)
**Priority**: [P1]

## 1. 개요 (Abstract)
- **문제**: 현재 DuckDB는 파일 기반 잠금(File-level Lock)으로 인해 데이터 복구와 실시간 수집이 동시에 발생할 때 `Conflicting lock` 에러가 빈번하게 발생함.
- **기회**: 이미 인프라에 포함된 **TimescaleDB(PostgreSQL)**를 검증 테이블(`market_ticks_validation`)의 저장소로 활용하여 동시성을 확보하고, 실시간 집계 데이터와 API 데이터를 안정적으로 비교함.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: "검증 데이터를 MVCC를 지원하는 TimescaleDB에 저장하면, 데이터 수집 파이프라인에 영향을 주지 않고 병렬적으로 품질 검증(Cross-check)을 수행할 수 있을 것이다."
- **기대 효과**:
    - 데이터 수집/복구 시 DB Lock으로 인한 프로세스 중단 방지.
    - PostgreSQL의 강력한 쿼리 기능을 활용하여 복잡한 오차 분석(Delta Analysis) 수행 가능.
    - 향후 대시보드에서 검증 결과를 실시간으로 조회하기에 용이함.

## 3. 구체화 세션 (Elaboration)
- **Antigravity (Data First)**: "데이터가 없으면 전략도 없다. DuckDB의 잠금 문제는 데이터 파이프라인의 가장 큰 병목이다. TimescaleDB로의 전환은 필수적이다."
- **Architect (Scalability)**: "1분봉 데이터는 틱 데이터에 비해 훨씬 용량이 작다. TimescaleDB에 저장하더라도 스토리지 부담은 적으면서 동시성 이점은 극대화될 것."

## 4. 로드맵 연동 시나리오
- **Pillar**: Infrastructure & Data Quality
- **Section**: [RFC-008] Tick Completeness & QA System
- **Next Step**: `implementation_plan.md`의 저장소 설정을 DuckDB에서 TimescaleDB로 변경.

## 5. 저장 구조 제안 (Schema Draft)
```sql
CREATE TABLE IF NOT EXISTS market_ticks_validation (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    agg_close DOUBLE PRECISION,   -- DB 집계 종가
    api_close DOUBLE PRECISION,   -- API 응답 종가
    agg_volume DOUBLE PRECISION,  -- DB 집계 거래량
    api_volume DOUBLE PRECISION,  -- API 응답 거래량
    delta_price DOUBLE PRECISION, -- 가격 차이
    delta_volume DOUBLE PRECISION, -- 거래량 차이
    status TEXT,                  -- 'MATCH', 'MISMATCH', 'GAP'
    source TEXT                   -- 'KIS', 'KIWOOM'
);
SELECT create_hypertable('market_ticks_validation', 'time', if_not_exists => TRUE);
```
