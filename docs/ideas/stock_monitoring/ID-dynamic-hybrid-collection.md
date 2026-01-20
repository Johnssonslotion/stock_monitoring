# IDEA: Dynamic Hybrid Data Collection Strategy

**Status**: 🌿 Sprouting (Drafting)
**Priority**: P1
**Source**: User / Brainstorming
**Date**: 2026-01-19

## 1. 개요 (Abstract)
기존의 정적 수집 전략(Core 20종목)을 확장하여, **KIS는 40종목 틱 수집**으로 확대하고 **Kiwoom은 호가 수집 및 순환매(Sector Rotation) 대상 동적 수집**을 담당하는 Hybrid 전략입니다. REST API의 Rate Limit을 준수하는 범위 내에서 주기적으로 수집 대상을 Refresh하는 **Dynamic Scanner**를 도입합니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)

### 가설
1.  **KIS WebSocket 확장**: KIS WS의 구독 제한(약 40~50개)을 최대한 활용하여 Mainstream 종목의 틱 데이터 커버리지를 2배로 늘릴 수 있다.
2.  **Kiwoom Dynamic Coverage**: Kiwoom의 조건검색(REST)과 WebSocket(호가+체결)을 결합하여, 실시간으로 거래량이 터지는 **순환매 종목**을 포착할 수 있다.
3.  **Data Specialization**: KIS는 빠른 Tick(체결)에, Kiwoom은 깊은 Orderbook(호가)에 집중함으로써 각 브로커 API의 강점을 극대화한다.

### 기대 효과
- **Market Coverage 증가**: 고정 20개 → 고정 40개 + 알파(동적 10~20개)
- **Alpha 포착**: 급등주/순환매 종목의 초기 진입 시점 포착 가능 (Scanner 연동)
- **시스템 효율성**: 호가 데이터(무거움)는 Kiwoom으로 분산하여 KIS 채널 부하 경감

## 3. 상세 전략 (Elaboration)

### 3.1. Symbol Allocation Strategy

| Role | Broker | Capacity | Data Type | Logic |
|------|--------|----------|-----------|-------|
| **Core Static** | **KIS** | 40 Symbols | **Tick Only** (0B) | 시총 상위 + 관심 종목 고정 (09:00~15:30) |
| **Rotation Dynamic** | **Kiwoom** | N Symbols | **Orderbook** (0D) + Tick | 조건검색/랭킹 기반 주기적 업데이트 |

### 3.2. Dynamic Scanner Logic
- **주기**: `REST API Limit` 고려 (예: 10분/30분/1시간 단위)
- **Process**:
    1.  **Scan**: Kiwoom 조건검색 API 호출 (또는 KIS 랭킹 API)
    2.  **Diff**: 현재 구독 목록 vs 신규 발굴 종목 비교
    3.  **Update**: Redis Pub/Sub으로 `Subscription Update` 이벤트 발행
    4.  **Action**: Collector가 동적으로 구독 추가/해제 (Kiwoom WS Screen No 관리 필수)

### 3.3. Technical Feasibility Check (Persona Opinions)

- **Tech Lead**:
    - KIS WebSocket은 계정당 40~50 종목 구독 가능하므로 40개 확장은 기술적으로 문제없음.
    - Kiwoom WebSocket은 Screen Number(화면번호) 하나당 100개 종목, 최대 50개 화면 가능하므로 동적 구독 용량 충분.
    - **Issue**: 동적 구독/해제 시 빈번한 `REG`/`REMOVE` 패킷 전송이 소켓 안정성에 미칠 영향 테스트 필요.

- **Data Scientist**:
    - 순환매 포착을 위해서는 **호가 데이터(Orderbook)**가 필수적임 (매수벽/매도벽 분석).
    - 스캔 주기가 너무 길면(1시간) 급등주 놓칠 위험. 1분~5분 주기가 이상적이나 API Quota 확인 필요.

- **DevOps**:
    - Redis를 통한 동적 Config 관리가 필요함. (`SET collection:targets:dynamic [...]`)
    - Scanner 서비스가 별도 컨테이너로 분리되어야 함 (`scanner-service`).

## 4. 로드맵 연동 시나리오
- **Phase 1**: KIS Target 40개로 증설 (Config 수정)
- **Phase 2**: Kiwoom Orderbook 수집 기능 구현 (현재 진행 중)
- **Phase 3**: `Scanner Service` 구현 및 동적 구독 파이프라인 구축 (Next Step)
