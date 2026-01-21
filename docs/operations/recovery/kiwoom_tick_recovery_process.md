# Kiwoom Tick Recovery Process (Mismatch Minutes)

## 1. Objective
Kiwoom 분봉(REST)과 Tick Aggregation 간의 불일치(Mismatch) 및 누락 구간을 식별하고, **Kiwoom Tick API (`ka10079`)를 통해 정밀한 Tick 데이터를 복구**합니다.

## 2. Workflow Overview
1.  **Outlier Detection**: DB에서 Kiwoom 분봉 vs Log Tick Aggregation 비교하여 불일치 구간 식별.
2.  **Target Grouping**: 종목별 복구 대상 분(Minute) 리스트 생성.
3.  **API Recovery**: `ka10079` (주식틱차트조회) API 호출 (Reverse Pagination).
4.  **Ingestion**: 복구된 Tick 데이터를 `market_ticks_imputed` 테이블에 저장 (`imputed_from='KIWOOM_API'`).

## 3. Implementation Details

### 3.1. Implementation Script
-   **File**: `src/verification/recover_outlier_ticks_kiwoom.py`
-   **Key Logic**:
    -   **Pagination**: `next-key` 헤더를 이용해 과거 시점(Target Minute)까지 역순 탐색.
    -   **Filtering**: `cntr_tm` (체결시간) 파싱하여 Target Minute(HHMM)에 해당하는 틱만 추출.
    -   **Rate Limit**: `gatekeeper` (Redis) 연동 및 429/503 에러 발생 시 Exponential Backoff 적용.

### 3.2. Execution Command
```bash
export REDIS_URL=redis://localhost:6379/1
export PYTHONPATH=$PYTHONPATH:$(pwd)
poetry run python src/verification/recover_outlier_ticks_kiwoom.py --date 2026-01-20
```

## 4. Current Status (2026-01-20)
-   **Process Implemented**: 전체 로직 구현 완료.
-   **Limitation**: 현재 실행 환경에서 Kiwoom API **429 (Rate Limit Exceeded)** 에러가 지속 발생하여 실제 데이터 적재 속도는 매우 느림. (API Quota 이슈)
-   **Next Step**: API 호출 제한 해제 또는 분산 처리 환경(Worker Scaling) 도입 필요.
