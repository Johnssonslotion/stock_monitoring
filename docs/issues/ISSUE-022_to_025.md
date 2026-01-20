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
