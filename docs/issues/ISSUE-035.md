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
- [ ] `preflight_check.py`에 미러 테이블 (`*_test`) 자동 동기화 및 Schema Diff 로직 추가
- [ ] `tests/test_timescale_archiver.py`에 **코드-DB 스키마 정합성 유닛테스트** (Parity Test) 추가
- [ ] 운영-미러 테이블 간 스키마 변경 사항 리포팅 기능 구현 (Log/Alert)
- [ ] `TimescaleArchiver`의 적재 성공 메트릭(Redis Key: `last_db_success`) 추가
- [ ] `Sentinel`에 장 초반 지연 집중 감시 및 '무중단' 알림 로직 구현
- [ ] 08:58 KST DB 쓰기 테스트 시나리오 추가

## 4. 기대 효과 (Expected Impact)
- 장 개시 후 1분 이내 정착 성공률 99% 확보
- 장애 발생 시 인지 및 복구 시간을 5분 -> 15초 내외로 단축
- 백테스팅 데이터의 시작점(09:00) 신뢰성 보장
