# Data Usage & Recovery Policy

**Effective Date**: 2026-01-15  
**Context**: Service Continuity vs Data Granularity

---

## 1. Core Principle
**"Chart Continuity First"**
- 사용자는 빈 차트보다 완벽하지 않은 차트를 선호합니다.
- 실시간 틱 수집이 실패하더라도, 외부 API(KIS)를 통해 완성된 분봉(Candle)을 가져와 서비스를 유지합니다.

## 2. Data Source Strategy (Dual-Source)

| Type | Primary Source (Real-time) | Secondary Source (Fallback/Recovery) |
| :--- | :--- | :--- |
| **Source** | **WebSocket Ticks** (Stream) | **KIS REST API** (Request) |
| **Storage** | `market_ticks` table | `market_candles` table (Raw) |
| **Granularity**| Tick-level (Aggregated to 1m) | 1-minute Candle |
| **Usage** | Live Chart, Order Flow Analysis | Historical Chart, Gap Filling |

## 3. Validation Logic
시스템은 주기적으로(매 10분) 틱 데이터의 품질을 검사합니다.

**Thresholds**:
- **Missing Bucket**: 1분 단위 Bucket이 하나라도 비어있으면 **FAIL**.
- **Low Volume**: Tick Count가 평소 대비 10% 미만이면 **WARN** (Alert only).

## 4. Recovery Process
Validation **FAIL** 시 다음 절차를 자동으로 수행합니다:

1.  **Identify Gaps**: 비어있는 시간 구간(`start_time`, `end_time`) 식별.
2.  **Fetch Candles**: KIS API(`inquire-daily-itemchartprice`)를 호출하여 해당 구간의 1분봉 조회.
3.  **Store**: `market_candles` 테이블에 Upsert.
    - *Note: `candles_1m` (View)에는 Insert 불가하므로 별도 테이블 사용.*

## 5. Serving Strategy (API)
Backend API는 사용자가 데이터 출처를 신경 쓰지 않도록 **Union**하여 제공합니다.

```sql
SELECT bucket as time, open, high, low, close, volume FROM candles_1m (Tick-based View)
UNION ALL
SELECT time, open, high, low, close, volume FROM market_candles (API-based Table)
-- 중복 시 우선순위 로직 적용 (View 우선)
```

## 6. Rate Limit Management
KIS API 호출은 무료 티어 제한을 준수합니다.
- **Limit**: 초당 20건 / 일일 해당없음(시세조회)
- **Policy**: 복구 시 종목당 1회 호출 (한 번에 100건 조회 가능하므로 효율적).
