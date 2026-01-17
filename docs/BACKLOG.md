# Project Backlog: Backend Integration & Data Pipeline

> **Governance Notice**: 
> 본 백로그의 작업은 **Live Market Data Collection**에 영향을 주지 않도록, 장 마감 후 또는 별도의 Staging 환경에서 진행해야 합니다.
> (Reference: `API_GAP_REPORT.md` for specific technical gaps)

## Issues (Live)
- [x] **ISSUE-007**: Chart Zoom Glitch & Market Holiday Handling | P1 | [x] | [Branch: bug/ISSUE-001-chart-zoom-and-holiday]
- [x] **ISSUE-002**: Standardize Backlog Issue IDs | P1 | [x] | [Branch: refactor/ISSUE-002-standardize-backlog]

## Tier 1: Critical (Scalper / Day Trader)
*High Frequency Data Layer*

- [ ] **WebSocket Connection Manager (`src/backend/ws/manager.py`)** -> See **ISSUE-004**
    - [ ] **Single Socket Policy**: KIS API의 웹소켓 연결 제한(Key당 1개)을 준수하는 중앙 관리자 구현.
    - [ ] **Subscription Multiplexing**: 단일 소켓으로 여러 종목(005930, 000660 등)의 데이터를 수신하고 라우팅하는 로직.
    - [ ] **Recoverability**: 연결 끊김 시 60초 내 자동 재접속(Backoff) 전략.

- [ ] **OrderBook Streaming**
    - [ ] `stream_orderbook` 핸들러 구현.
    - [ ] 호가 잔량 변동분(Delta)만 전송하여 대역폭 절약.

- [ ] **Execution Streaming**
    - [ ] `stream_executions` 핸들러 구현.
    - [ ] "세력 체결" 감지 로직(서버 사이드) 및 알림 패킷 전송.

## Tier 2: Major (Swing / Trend Trader)
*Historical & Analytical Data Layer*

- [ ] **Candle Data Service (`src/backend/api/candles.py`)**
    - [ ] `GET /api/candles`: DB(PostgreSQL/TimescaleDB) 조회 로직.
    - [ ] **Data Filling**: 장중 빈 캔들(Gap)에 대한 Zero-Filling 또는 직전가 채우기 로직.

- [ ] **Market Sector Service**
    - [ ] 섹터별 등락률 집계 배치(Batch) 작업 (10초 주기).
    - [ ] `GET /api/market/sectors` 엔드포인트 구현.

## Tier 3: Quant Features (Analytical)
*Advanced Analytics*

- [ ] **Correlation Engine**
    - [ ] 관련주(`RelatedAssets`) 자동 산출 알고리즘 (Pearson Correlation).
    - [ ] 뉴스 키워드 기반 종목 연관성 분석.

- [ ] **Whale Alert System**
    - [ ] 대량 체결 발생 시 슬랙/디스코드 웹훅 연동.

---

## Tier 4: Internal Instance Execution (Backend Spec v1)
> **Ref**: `docs/requirements/backend_specs_v1.md`

### [ISSUE-003] DB View & Aggregation Restoration (Prev. TICKET-001)
**Priority**: Critical (P0)
- [ ] `market_candles` 데이터 보존 정책 확인
- [ ] `public.candles_1m` 뷰 재생성
- [ ] Continuous Aggregates (5m, 1h, 1d) 생성 및 Refresh Policy 등록
- [ ] `SELECT count(*)` 검증 (15m > 0)

### [ISSUE-004] WebSocket Connection Manager Implementation (Prev. TICKET-002)
**Priority**: High (P1)
- [ ] `ConnectionManager` 클래스 고도화 (`src/api/manager.py`)
- [ ] Redis Pub/Sub(`stock:ticks`) 기반 데이터 분배 구조 확립
- [ ] 브라우저 멀티 탭 진입 시 Socket 1개 유지 검증

### [ISSUE-005] Data Gap Detection & Filling Logic (Prev. TICKET-003)
**Priority**: Medium (P2)
- [ ] `get_candles` 내 누락 구간 감지 로직 추가
- [ ] Zero-Order Hold (직전가 채우기) 구현
- [ ] `is_filled` 메타데이터 응답 추가

### [ISSUE-006] API Error Handling & Logging (Prev. TICKET-004)
**Priority**: Medium (P2)
- [ ] 500 에러 스택 트레이스 로깅 강화
- [ ] 클라이언트용 명확한 에러 코드 정의 (`DB_CONNECTION_ERROR` 등)
