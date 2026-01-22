# External API Verification Status (2026-01-20)

## 1. Executive Summary
본 문서는 2026-01-20 데이터 누락 사고 대응 중 수행된 **외부 벤더(Kiwoom, KIS) API의 동작 검증 결과**를 통합 기술합니다.

| Vendor | API Type | Endpoint / TR ID | Status | Verdict | Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Kiwoom** | **Minute (분봉)** | `ka10080` | ✅ 200 OK | **Production Ready** | 파싱 버그 수정 완료 (`stk_min_pole_chart_qry`) |
| **Kiwoom** | **Tick (틱)** | `ka10079` | ✅ 200 OK | **Verified (Throttled)** | 구성 정상이나 Rate Limit(429)으로 대량 수집 제한 |
| **KIS** | **Tick (틱)** | `FHKST01010400` | ✅ 200 OK | **Unavailable** | VTS 환경에서 과거 데이터 조회 시 Empty List 반환 |

---

## 2. Detailed Verification Results

### 2.1. Kiwoom Minute API (`ka10080`)
- **검증 목적**: 데이터 공백 구간(09:00~15:30)에 대한 분봉 데이터 확보.
- **테스트 결과**:
    -   기존 수집기(`collector_kiwoom.py`)의 필드명 오류(`pols` -> `pole`) 수정 후 재실행.
    -   삼성전자(`005930`), SK하이닉스(`000660`) 등 주요 종목에 대해 **381건(전일)** 데이터 수집 성공.
- **결론**: **Main Data Source**로 채택하여 보간(Imputation) 작업 수행.

### 2.2. Kiwoom Tick API (`ka10079`)
- **검증 목적**: Outlier 분(Minute)에 대한 정밀 Tick 레벨 복구.
- **테스트 결과**:
    -   **구성**: API ID `ka10079`, `tic_scope=1`.
    -   **연결**: `test_kiwoom_tick_simple.py` 수행 결과 **200 OK 및 데이터 수신 확인**.
    -   **한계**: 연속 호출 시 `Rate Limit Exceeded (429)` 빈번 발생.
- **결론**: 구성은 유효하나, 현재 API Quota로는 대량 복구가 불가능하여 **프로세스만 수립(Ready)** 상태 유지.

### 2.3. KIS Tick API (`FHKST01010400`)
- **검증 목적**: Kiwoom 대안으로 Tick 데이터 복구 시도.
- **테스트 결과 (2026-01-20 12:00 UTC)**:
    -   **구성**: `inquire-time-itemconclusion` + `FHKST01010400`.
    -   **응답**: HTTP 200 OK 반환되나, `output1`(데이터 리스트)이 비어있음(`[]`).
    -   **Target Time**: 2026-01-20 09:00~09:13 (KST).
- **긴급 복구 실패 분석 (09:30 KST)**:
    -   당시 스크립트(`recover_morning_ticks.py`)에서 `FHKST01010300`(Snapshot TR)을 잘못 사용하여 실패(0 Byte)한 것으로 확인됨.
    -   그러나 올바른 TR(0400)로 재시도한 현재도 데이터가 없는 것으로 보아, **Mock/VTS 환경의 데이터 보존 정책 한계**로 추정됨.
- **결론**: 현재 환경에서 **복구 불가** 판정.

---

## 3. Action Items
1.  **Kiwoom Minute 활용**: `market_candles` 테이블의 최종 보간 데이터로 확정 사용.
2.  **Kiwoom Tick 프로세스 보존**: `recover_outlier_ticks_kiwoom.py`는 향후 API 용량 증설 시 즉시 투입 가능하도록 보존.
3.  **KIS API 용도 제한**: 현재 환경에서는 실시간 수집(Websocket) 외의 과거 데이터 조회 용도로는 신뢰할 수 없음.
