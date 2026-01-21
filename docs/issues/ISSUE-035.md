# ISSUE-035: [Feature] 상한선 없는 장 초반 수집 보장 (Zero-Tolerance Open Guard)

## 1. 문제 정의 (Problem Definition)
장 초반(09:00~09:10)에 소켓 통신(Collector)은 정상임에도 불구하고, **TimescaleDB 적재기(Archiver)의 내부 오류(스키마 불일치, DB 연결 끊김, 버퍼 오버플로 등)**로 인해 정작 DB에는 데이터가 남지 않는 현상이 발생할 수 있습니다. 현재 Sentinel은 주로 '데이터 발행(Redis)' 여부만 체크하여 '실제 저장(DB)' 실패를 탐지하는 속도가 느립니다.

## 2. 해결 방안 (Proposed Solution) - "Ingestion-Aware Passive Guard"
적재기(Archiver)의 문제를 해결하기 위해 강제 재시작과 같은 파괴적인 방식 대신, **정밀한 기록과 즉각적인 이상 탐지 및 알림**에 집중합니다. 소켓 통신(Collector)의 안정성을 최우선으로 보호합니다.

1.  **DB Ingestion Recording**: 
    *   `TimescaleArchiver`가 실제 DB `buffer_flush` 성공 시 기록하는 로그와 메트릭을 강화합니다.
    *   Sentinel은 Redis 발행(Redis) 시점과 DB 저장(DB) 시점 사이의 **지연(Lag)**을 장 초반에 1초 단위로 감시합니다.
2.  **Passive Gap Alerting (Non-disruptive)**:
    *   장 초반(09:00:00~09:10:00) 동안 15초 이상 DB 적재가 지연될 경우, **재시작 없이 즉시 `CRITICAL` 알림**만 발생시킵니다.
    *   이를 통해 운영자가 소켓 연결은 유지한 채로 적재기 상태만 별도로 점검할 수 있도록 합니다.
3.  **Pre-market Ingestion Proof & Mirror Sync (08:30-08:58)**:
    *   **Phase A (Pre-flight - 08:30)**: `preflight_check.py` 실행 시 운영 테이블과 동일한 스키마의 미러 테이블(`market_ticks_test`, `market_orderbook_test`)을 자동 생성하거나 최신 상태로 동기화(Sync)합니다.
    *   **Phase B (Schema Parity Check)**: 미러 테이블 동기화 과정에서 **운영 테이블과의 스키마 차이(Schema Drift)**를 감지합니다. 컬럼 추가, 타입 변경 등 변경 사항이 있을 경우 이를 즉시 리포트하여 '코드-DB 불일치' 가능성을 시각화합니다.
    *   **Phase C (Active Proof - 08:58)**: 동기화된 미러 테이블에 가짜 데이터를 써보며 **DDL 정합성, 인덱스 상태, 쓰기 권한**을 최종 검증합니다.

## 3. 상세 세부 작업 (Tasks)
- [x] `preflight_check.py`에 미러 테이블 (`*_test`) 자동 동기화 및 Schema Diff 로직 추가
- [x] 운영-미러 테이블 간 스키마 변경 사항 리포팅 기능 구현 (Log/Alert)
- [x] `TimescaleArchiver`의 적재 성공 메트릭(Redis Key: `archiver:last_db_success`) 추가
- [x] `Sentinel`에 장 초반 지연 집중 감시 및 '무중단' 알림 로직 구현
- [x] 08:58 KST DB 쓰기 테스트 시나리오 추가
- [ ] `tests/test_timescale_archiver.py`에 **코드-DB 스키마 정합성 유닛테스트** (Parity Test) 추가 (Optional)

## 4. 기대 효과 (Expected Impact)
- 장 개시 후 1분 이내 정착 성공률 99% 확보
- 장애 발생 시 인지 및 복구 시간을 5분 -> 15초 내외로 단축
- 백테스팅 데이터의 시작점(09:00) 신뢰성 보장

## 5. 구현 완료 (Implementation Completed - 2026-01-21)

### 5.1 구현 내용
1. **preflight_check.py 개선**
   - `sync_mirror_tables()`: market_ticks_test, market_orderbook_test 자동 생성
   - `check_schema_parity()`: 운영-테스트 테이블 스키마 차이 감지
   - `db_write_test()`: 실제 DB 쓰기 권한 및 DDL 검증

2. **TimescaleArchiver 메트릭 추가**
   - `_record_db_success()`: 적재 성공 시 Redis 메트릭 기록
   - Redis Keys: `archiver:last_db_success`, `archiver:last_flush_count`, `archiver:last_flush_time`

3. **Sentinel 장 초반 모니터링**
   - `monitor_ingestion_lag()`: 09:00-09:10 KST 동안 1초 단위 감시
   - Redis publish time vs DB ingestion time 비교
   - 15초 이상 지연 시 CRITICAL 알림 (재시작 없음)

4. **환경 변수 표준화**
   - `.env.schema.yaml`: 전체 변수 정의 (30+ variables)
   - `.env.template`: 마스터 템플릿
   - `.env.local.example`: Mac 로컬 개발용
   - `.env.prod.example`: Oracle Cloud 프로덕션용

### 5.2 테스트 결과
```
✅ Smoke Test: PASSED
✅ Redis: Connected
✅ TimescaleDB: Connected
✅ Mirror Tables: Created/Synced
✅ Schema Parity: MATCH (Production ↔ Test)
✅ DB Write Test: PASSED (1 test record)
```

### 5.3 변경된 파일
- `scripts/preflight_check.py`: 미러 테이블, 스키마 검증, DB 쓰기 테스트 추가
- `src/data_ingestion/archiver/timescale_archiver.py`: DB 적재 성공 메트릭 추가
- `src/monitoring/sentinel.py`: 장 초반 지연 감시 로직 추가
- `.env.schema.yaml`, `.env.template`, `.env.local.example`, `.env.prod.example`: 통일
- `README.md`: 환경 설정 가이드 업데이트
