# Backend Requirements Specification & Execution Tickets
> **Target**: Internal Instance Development  
> **Date**: 2026-01-16  
> **Status**: Ready for Execution

## 1. Executive Summary
현재 프론트엔드(React)는 완성도 높은 UI/UX를 갖추었으나, 이를 뒷받침할 백엔드(Python/FastAPI)의 일부 기능이 미구현 상태이거나 로컬 개발 환경에서 비활성화되어 있습니다. 본 문서는 **안정적인 데이터 파이프라인**과 **실시간/과거 데이터 서빙**을 위한 필수 백엔드 요구사항을 정의하고, 이를 실행 가능한 작업 단위(Ticket)로 명세합니다.

---

## 2. Requirement Specifications

### RQ-01: Continuous Candle Aggregation (1M -> 5M/1H/1D)
- **Problem**: 현재 `public.candles_1m` 뷰가 비어있거나 소실됨. 상위 타임프레임(5분, 1시간, 1일) 데이터가 자동으로 생성되지 않음.
- **Requirement**: 1분봉(`market_candles` where interval='1m') 데이터를 기반으로 TimescaleDB의 **Continuous Aggregates** 기능을 활성화하여 5분, 1시간, 1일봉을 자동 생성 및 갱신해야 함.
- **Impact**: 차트 로딩 속도 향상, 데이터 무결성 보장.

### RQ-02: Single Socket WebSocket Manager
- **Problem**: KIS(한국투자증권) API는 계좌/Key당 1개의 웹소켓 연결만 허용함. 클라이언트(브라우저)별로 소켓을 열면 한도 초과로 차단됨.
- **Requirement**: 백엔드에서 **단일 웹소켓 연결(Single Socket)**을 유지하고, 수신된 데이터를 내부 브로드캐스팅(Redis Pub/Sub 또는 Memory)을 통해 연결된 모든 프론트엔드 클라이언트에게 분배(Multiplexing)해야 함.
- **Impact**: API 제한 준수, 다중 클라이언트 접속 지원.

### RQ-03: Historical Data Gap Filling
- **Problem**: 장중 데이터 수집이 일시 중단되거나 네트워크 이슈로 누락된 구간(Gap)이 발생할 경우, 차트에 구멍이 뚫림.
- **Requirement**: 조회 시점에 누락된 구간을 감지하여 `previous_close` 값으로 채우거나(Zero-Order Hold), 별도의 `is_filled: true` 플래그와 함께 보정된 데이터를 내려줘야 함.
- **Impact**: 차트 시각적 완결성, 기술적 지표 계산 오류 방지.

### RQ-04: Robust Docker Environment Policy
- **Problem**: 로컬 개발 시 무거운 수집기(Collector)들이 모두 실행되어 리소스를 점유하거나 데이터 정합성을 해침.
- **Requirement**: `docker-compose.local.yml` 프로파일을 명확히 분리하여, 로컬에서는 **Core(DB, Redis, API)**만 구동하고, 수집기는 **Production** 프로파일로 격리해야 함. (기 반영됨, 정책화 필요)

---

## 3. Execution Tickets (Task List)

### [TICKET-001] DB View & Aggregation Restoration
**Priority**: Critical (P0)  
**Assignee**: Backend Engineer  
**Description**:
1. `market_candles` 테이블의 데이터 보존 정책(Retention Policy) 확인.
2. `public.candles_1m` 뷰 재생성 (단순 쿼리 조회용).
3. `create_continuous_aggregates.sql` 스크립트를 실행하여 5m, 1h, 1d Materialized View 생성 및 Refresh Policy 등록.
**Acceptance Criteria**:
- [ ] `SELECT count(*) FROM market_candles_15m` 쿼리 결과가 0보다 커야 함.
- [ ] API `/candles/{symbol}?interval=5m` 호출 시 데이터 반환 성공.

### [TICKET-002] WebSocket Connection Manager Implementation
**Priority**: High (P1)  
**Assignee**: Backend Engineer  
**Description**:
1. `src/api/manager.py`에 `ConnectionManager` 클래스 고도화.
2. `src/data_ingestion/price/unified_collector.py`와 연동하여 KIS 소켓 데이터 수신.
3. Redis Pub/Sub 채널(`stock:ticks`)을 통해 API 서버로 데이터 전송 구조 확립.
**Acceptance Criteria**:
- [ ] 브라우저 3개 탭 동시 접속 시에도 KIS 소켓 연결은 1개만 유지.
- [ ] 모든 탭에서 실시간 호가/체결 데이터 수신 확인.

### [TICKET-003] Data Gap Detection & Filling Logic
**Priority**: Medium (P2)  
**Assignee**: Data Engineer  
**Description**:
1. `src/api/routes/candles.py` 내 `get_candles` 로직 수정.
2. 요청된 `from`/`to` 범위 내에서 예상되는 캔들 개수와 실제 개수 비교.
3. 누락 구간 발생 시 가상 캔들 생성 로직 추가.
**Acceptance Criteria**:
- [ ] 강제로 데이터 삭제 후 조회 시, 끊김 없이 직선(Flat)으로 연결된 차트 확인.

### [TICKET-004] API Error Handling & Logging
**Priority**: Medium (P2)  
**Description**:
1. 500 Internal Server Error 발생 시 스택 트레이스를 로그 파일에 상세 기록.
2. 클라이언트에게는 명확한 에러 코드(e.g., `DB_CONNECTION_ERROR`, `NO_DATA_FOUND`) 반환.

---
**Note**: 본 문서는 `docs/requirements/backend_specs_v1.md`로 관리됩니다.
