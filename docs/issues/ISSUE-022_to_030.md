# ISSUE-022: [Bug] TickArchiver DuckDB 타입 변환 오류 수정

**Status**: Open  
**Priority**: P1  
**Type**: bug  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- Redis에서 전달되는 `int`/`float` 형태의 timestamp가 DuckDB의 `TIMESTAMP` 컬럼으로 저장될 때 `Conversion Error: Unimplemented type for cast (INTEGER -> TIMESTAMP)` 발생.
- 이로 인해 오늘 장중 DuckDB 적재가 전면 중단됨.

## Acceptance Criteria
- [ ] `TickArchiver` 내에서 모든 형태의 timestamp(int, float, str)를 ISO 8601 문자열 또는 `datetime` 객체로 정규화하여 저장.
- [ ] 장 종료 후 재시작 시 에러 없이 데이터 적재 확인.

---

# ISSUE-023: [Bug] TimescaleArchiver Kiwoom 채널 구독 누락 수정

**Status**: Open  
**Priority**: P1  
**Type**: bug  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- `KiwoomWSCollector`는 `tick:KR:*` 채널을 사용하나, `TimescaleArchiver`는 `ticker.*`만 구독하고 있어 Kiwoom 데이터가 TimescaleDB에 누락됨.

## Acceptance Criteria
- [ ] `TimescaleArchiver`의 구독 채널 리스트에 `tick:*` 및 `orderbook:*` 정규 표현식 추가.
- [ ] KIS/Kiwoom 데이터가 동시에 TimescaleDB에 저장되는지 확인.

---

# ISSUE-024: [Bug] Recovery Worker 의존성(httpx) 누락 수정

**Status**: Open  
**Priority**: P2  
**Type**: bug  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- `recovery-worker` 컨테이너 실행 시 `httpx` 모듈을 찾지 못해 무한 재시작됨.

## Acceptance Criteria
- [ ] `pyproject.toml` 또는 Dockerfile에 `httpx` 의존성 명시적 추가.
- [ ] 컨테이너가 정상적으로 `Up` 상태를 유지하는지 확인.

---

# ISSUE-025: [Feature] Raw Log (JSONL) 기반 DB 복구 스크립트 개발

**Status**: Open  
**Priority**: P1  
**Type**: feature  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- 오늘(2026-01-20) 장중 아카이버 장애로 인해 누락된 데이터를 `data/raw/`에 저장된 JSONL 파일로부터 추출하여 DB에 후행 적재해야 함.

## Acceptance Criteria
- [ ] KIS/Kiwoom 원본 로그 파싱 엔진 구현.
- [ ] 파싱된 데이터를 DuckDB 및 TimescaleDB에 중복 없이(On Conflict Do Nothing) 적재하는 기능.
- [ ] 복구 후 DB 건수와 로그 파일 라인 수 비교 검증.

---

# ISSUE-026: [Debt] Kiwoom Orderbook Pub/Sub 및 아카이빙 구현

**Status**: Open  
**Priority**: P2  
**Type**: refactor  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- `KiwoomWSCollector`가 실시간 호가(`0D`) 데이터를 수신하고 있으나, Redis로 발행하지 않아 TimescaleDB에 저장되지 않음.
- KIS는 이미 호가 수집 및 저장 로직이 존재하므로 Kiwoom도 동일 규격으로 구현 필요.

## Acceptance Criteria
- [ ] `KiwoomWSCollector`에서 `0D` 메시지 발생 시 Redis 채널로 발행.
- [ ] `TimescaleArchiver`에서 해당 데이터를 수신하여 `market_orderbook` 테이블에 적재.

---

# ISSUE-027: [SDLC] Smoke Test (test_smoke_modules.py) 구축

**Status**: Open  
**Priority**: P1  
**Type**: docs  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- 시스템 배포 또는 프리플라이트 체크 시 주요 모듈의 임포트 가능 여부 및 문법 오류를 자동으로 검증할 수 있는 스모크 테스트가 누락됨.
- 이로 인해 `recovery-worker`의 의존성 오류 등을 사전에 발견하지 못함.

## Acceptance Criteria
- [ ] `tests/test_smoke_modules.py` 작성: 모든 주요 Service(KIS, Kiwoom, Archiver) 및 유틸 모듈의 임포트 시도.
- [ ] 프리플라이트 체크(`scripts/preflight_check.py`)와 연동하여 장 시작 전 자동 실행.

---

# ISSUE-028: [Bug] Kiwoom Tick Subscription Failure (No `0B` data)

**Status**: Open  
**Priority**: P1  
**Type**: bug  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- RAW 로그 분석 결과, `KiwoomWSCollector`가 실시간 체결(`0B`) 데이터를 전혀 수신하지 못하고 있음 (`0D` 호가 잔량만 수신됨).
- 이는 `REG` 메시지 포맷 문제 또는 구독 요청 방식의 문제로 추정됨.

## Acceptance Criteria
- [ ] `KiwoomWSCollector` 구독 로직 수정 (체결/호가 구독 분리 등).
- [ ] RAW 로그에 `type: 0B` 메시지가 기록되는지 확인.

---

# ISSUE-029: [Debt] Container Configuration Sync (Mount `configs/`)

**Status**: Open  
**Priority**: P2  
**Type**: refactor  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- 현재 컬렉터 컨테이너들이 `configs/` 디렉토리를 볼륨 마운트하지 않아, 빌드 시점의 구버전 YAML 설정을 사용하고 있음 (현재 70종목이 아닌 22종목만 수집 중).

## Acceptance Criteria
- [ ] `docker-compose.yml` 수정하여 모든 서비스에 `../configs:/app/configs` 볼륨 마운트 추가.
- [ ] 컨테이너 재시작 시 최신 종목 리스트가 로그에 출력되는지 확인.

---

# ISSUE-030: [Bug] Pipeline Channel Name Inconsistency

**Status**: Open  
**Priority**: P1  
**Type**: bug  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- KIS 컬렉터는 `ticker.kr`, Kiwoom 컬렉터는 `tick:KR:{symbol}` 채널을 사용하고 있어 아카이버의 구독 패턴(`ticker.*`)과 일치하지 않음.
- 이로 인해 Kiwoom 데이터가 TimescaleDB에 저장되지 않는 현상 발생.

## Acceptance Criteria
- [ ] Redis 채널 명명 규칙 표준화 (예: `market:tick:{market}:{symbol}`).
- [ ] 아카이버 구독 영역 확장 및 모든 브로커 데이터 수용 확인.
