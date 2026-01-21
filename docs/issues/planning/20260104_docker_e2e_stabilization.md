# Phase 1-2 Docker E2E Stabilization Plan

## Goal Description
Docker 환경에서 TickCollector와 TickArchiver가 정상적으로 통신하고 데이터를 저장하도록 수정하여 E2E 테스트를 통과시킨다.

## User Review Required
> [!IMPORTANT]
> 이 변경사항은 `master` 브랜치에 병합되어 Phase 1-2를 완료 처리하는 기반이 됩니다.

## Proposed Changes

### Docker Environment & Infrastructure
#### [MODIFY] `src/core/config.py`
- **문제**: `configs/base.yaml`의 `redis://localhost`가 Docker 컨테이너에서 통신 불가.
- **해결**: `REDIS_URL` 환경변수가 존재할 경우 설정 파일 값보다 우선하도록 수정.

#### [MODIFY] `deploy/docker-compose.yml`
- Redis 서비스 및 Python App 컨테이너 설정 최적화.
- 환경변수 `REDIS_URL=redis://stock-redis:6379/0` 명시.

### Data Concurrency
#### [MODIFY] `src/data_ingestion/ticks/archiver.py` & `src/data_ingestion/news/collector.py`
- **문제**: 여러 컨테이너가 단일 DuckDB 파일(`market_data.duckdb`)에 동시 쓰기 시도 시 `PID Lock` 오류 발생.
- **해결**: 컴포넌트별로 DB 파일 분리.
  - TickArchiver: `data/ticks.duckdb`
  - NewsCollector: `data/news.duckdb`

### Bug Fixes & Improvements
#### [MODIFY] `src/data_ingestion/ticks/archiver.py`
- **문제**: `subscribe("tick.*")`는 패턴 매칭이 안 되어 메시지 수신 불가.
- **해결**: `psubscribe("tick.*")`로 변경.

#### [MODIFY] `src/data_ingestion/ticks/collector.py`
- 디버깅 용이성을 위해 `DEBUG` 레벨 로깅 추가.

#### [NEW] Debugging Tools in `Makefile`
- `make debug-redis`: 실시간 Redis 트래픽 모니터링 (`MONITOR`)
- `make debug-pubsub`: 활성 구독자 수 확인 (`PUBSUB NUMSUB`)

## Verification Plan

### Automated Verification
1. **Docker Compose Up**: `make up`
2. **Data Collection Check**:
   - `docker logs tick-collector`: "Published tick" 로그 확인
   - `docker logs tick-archiver`: "Flushed X ticks" 로그 확인
3. **Data Integrity Check**:
   - `make verify` (별도 스크립트로 DuckDB 쿼리 실행)

### Success Metrics
- [x] Redis Pub/Sub 메시지 도달율 100%
- [x] DuckDB 파일 잠금 오류 0건
- [x] 1분당 100개 이상의 Tick 데이터 저장 (Upbit 기준)
