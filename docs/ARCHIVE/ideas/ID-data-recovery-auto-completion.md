# IDEA: 데이터 누락 자동 보완 및 무결성 복구 (Data Gap Auto-Completion)
**Status**: 💡 Seed (Idea)
**Priority**: P1
**Related**: [ID-isolation-and-recovery](./ID-isolation-and-recovery.md)

## 1. 개요 (Abstract)
시스템 장애, 네트워크 지연, 또는 API 오류로 인해 발생한 수집 데이터의 **누락(Gap)**을 자동으로 감지하고, 가용한 대체 소스(Kiwoom TR 등)를 통해 **사후 보완(Filling)**하는 메커니즘을 정의합니다. 수집기 격리(Isolation)가 '예방'이라면, 이 아이디어는 '복구'에 초점을 맞춥니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설 1 (Sequence Tracking)**: 틱 데이터의 시퀀스나 타임스탬프를 분석하면 유의미한 누락(예: 1분 이상 데이터 공백)을 100% 감지할 수 있다.
- **가설 2 (Auto-Filling)**: 장 중에는 실시간 복구가 어렵더라도, **장 마감 후(Post-Market)** 또는 **유휴 시간(Idle Time)**에 키움 `opt10079`(주식틱차트조회) 등을 활용하여 누락분을 메꿀 수 있다.
- **기대 효과**: 백테스팅 데이터의 신뢰도 확보 (Zero-Gap 추구).

## 3. 구체화 세션 (Elaboration)
- **Data Scientist (Integrity First)**: 
    - "단 1분의 데이터 누락도 백테스팅 결과에 치명적일 수 있습니다. `DuckDB`에 저장된 데이터의 무결성을 주기적으로 검증하는 `check_duckdb_integrity.py`와 같은 도구가 필수적입니다."
- **Backend Developer (Implementation)**: 
    - **Detection**: `Doomsday Check`는 실시간 0건을 감지하지만, 미세한 누락(Sequence Skip)은 감지하지 못함. 별도의 `Integrity Checker` 필요.
    - **Recovery Logic**:
        1. **Identify**: 누락된 종목과 시간대(`start_time`, `end_time`) 특정.
        2. **Fetch**: 키움 TR 요청 (API Limit 고려하여 스케줄링).
        3. **Merge**: 기존 DuckDB 테이블에 중복 없이 Insert.
- **Infra (Resource Constraint)**:
    - "오라클 프리티어(4 vCPU) 내에서 대량의 복구 쿼리가 돌면 실시간 수집에 영향을 줄 수 있습니다. 복구 작업은 장 마감 후(`15:30~`) 또는 주말에 수행하는 것이 안전합니다."

## 4. 로드맵 연동 시나리오
- **Pillar**: Pillar 2 (Data Ingestion & Integrity)
- **Backlog Item**: [Failure Mode 자동 복구](../../../BACKLOG.md#L21) (`P2`)
- **Key Components**: 
    - `src/monitoring/integrity_checker.py` (New)
    - `src/recovery/recovery_worker.py` (New)
