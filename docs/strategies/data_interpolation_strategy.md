# Data Interpolation & Recovery Strategy (2026-01-20 Analysis)

## 1. 진단 결과 요약 (Outlier Report 기반)
1월 20일 데이터에 대한 전수 조사 결과, 데이터 퀄리티는 크게 세 가지 그룹으로 나뉩니다.

| 그룹 | 상태 | 종목 예시 | 비중 | 특징 |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1 (High)** | Coverage > 80% | 삼성전자, SK하이닉스 등 (약 10종목) | ~14% | 복구된 Log 데이터가 API와 거의 일치함. 미세한 가격 오차(1틱) 존재. |
| **Tier 2 (Partial)** | Coverage 10~80% | (없음 - 모 아니면 도 패턴) | 0% | - |
| **Tier 3 (Missing)** | Coverage < 10% | 나머지 대부분 종목 (약 60종목) | ~86% | Log 파일에 데이터가 거의 없거나 아예 없음 (수집 대상 제외 추정). |

## 2. 보간(Interpolation) 전략 원칙

### 원칙 1: Honest Tick (틱 데이터 위조 금지)
- **틱(Tick)** 데이터는 체결의 '사실'을 기록해야 하므로, **분봉 데이터를 기반으로 가상의 틱을 생성(Synthetic Ticks)하지 않습니다.**
- 따라서 Tier 3(완전 소실) 구간의 `market_ticks` 테이블은 **결측(Gap) 상태로 남겨둡니다.**

### 원칙 2: Candle Backfill (분봉 데이터 완전성)
- 차트 분석 및 지표 계산을 위해 **분봉(Candle)** 데이터는 끊김이 없어야 합니다.
- Tier 3 구간은 **KIS REST API (`market_verification_raw`) 데이터를 사용하여 `market_candles` 테이블을 채웁니다.**

### 원칙 3: Primary Source Selection
- **Tier 1 (Log 존재)**: `market_ticks_recovery` (Log) → 집계 → `market_candles` (Volume 정확도 높음)
- **Tier 3 (Log 소실)**: `market_verification_raw` (API) → 복사 → `market_candles`

## 3. 실행 계획 (Action Plan)

### Step 1: Outlier Detection (완료)
- `detect_outliers.py`를 통해 종목별 Tier 분류 완료.

### Step 2: Candle Merging (보간 실행)
- **SQL 기반 병합 쿼리** 실행:
    ```sql
    -- 1. Log 기반 분봉 생성 (Tier 1 우선)
    INSERT INTO market_candles (time, symbol, open, high, low, close, volume)
    SELECT 
        time_bucket('1 minute', time), symbol, 
        first(price, time), max(price), min(price), last(price, time), sum(volume)
    FROM market_ticks_recovery
    GROUP BY 1, 2;
    
    -- 2. API 기반 결측 보완 (Tier 3 Backfill)
    INSERT INTO market_candles (time, symbol, open, high, low, close, volume)
    SELECT time, symbol, open, high, low, close, volume
    FROM market_verification_raw v
    WHERE NOT EXISTS (
        SELECT 1 FROM market_candles c 
        WHERE c.time = v.time AND c.symbol = v.symbol
    );
    ```

### Step 3: Tick Gap Visualization
- UI 상에서 틱 데이터가 없는 구간은 "Tick Data Unavailable (Source: API Candle)"로 표시하여 사용자에게 데이터 출처를 명확히 고지.
