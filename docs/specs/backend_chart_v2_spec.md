# 🛠️ Backend Specification for Chart V2 (Server-Side)

**Scope**: Backend API & Database
**Goal**: Support Frontend Chart V2 features (VWAP, Bollinger, Reference Lines)
**Lead**: Backend Engineer

---

## 1. 개요 (Overview)
Frontend의 `CandleChart V2` 혁신(VWAP, Reference Lines)을 지원하기 위해, 백엔드는 단순 캔들 리스트 외에 **"메타 데이터(Reference Data)"**와 **"무결성 있는 시계열 데이터"**를 제공해야 합니다.

## 2. 신규/개선 요구사항 (Requirements)

### 2.1 ✅ Quote Snapshot Endpoint (신규)
-   **목적**: 차트의 `전일 종가(Prev Close)` 기준선을 그리기 위함. 1분봉 데이터만 조회해서는 전일 종가를 알 수 없음.
-   **Endpoint**: `GET /api/v1/quote/{symbol}` (또는 `/snapshot`)
-   **Payload**:
    ```json
    {
        "symbol": "005930",
        "price": 75000,
        "change_rate": 1.2,
        "volume": 5000000,
        "prev_close": 74100,  <-- 핵심 (Reference Line용)
        "open": 74500,
        "high": 75500,
        "low": 74200,
        "market_status": "OPEN" | "CLOSED"
    }
    ```

### 2.2 ⚡ Candle API 개선 (Optimization)
-   **목적**: VWAP(거래량 가중 평균) 계산을 위해 **"당일 시가부터 현재까지"** 누락 없는 데이터 필요.
-   **Endpoint**: `GET /api/v1/candles/{symbol}`
-   **Parameter 추가**:
    -   `mode=intraday` (옵션): 이 플래그가 있으면 `limit`을 무시하거나, 자동으로 **09:00:00 KST** 이후 데이터를 모두 반환.
-   **Gap Filling**:
    -   1분봉의 경우 거래가 없는 분(Minute)도 `volume=0, close=prev_close` 형태로 채워서 내려주는 옵션 고려 (`fill_gaps=true`). (현재 프론트에서 처리 중이나 백엔드 처리 권장)

### 2.3 🧱 Data Integrity (무결성)
-   **Tick Aggregation**: 1분봉 생성 시, Tick 데이터의 누락이 없어야 함.
-   **Latency**: 1일치(390 row) 조회 시 Latency < **50ms** 목표. (TimescaleDB Continuous Aggregate 활용)

---

## 3. Database Schema Impact
-   **No Schema Change Required**. 기존 `market_candles` 테이블 및 하이퍼테이블 활용.
-   **Query Strategy**:
    -   현재: `ORDER BY time DESC LIMIT N`
    -   개선: `WHERE time >= 'Today 09:00' ORDER BY time ASC` (Intraday Mode)

## 4. API Specification Matrix

| Feature | Method | Endpoint | Params | Response Focus |
| :--- | :--- | :--- | :--- | :--- |
| **Prev Close Line** | `GET` | `/api/v1/quote/{symbol}` | - | `prev_close` |
| **VWAP Data** | `GET` | `/api/v1/candles/{symbol}` | `interval=1m`, `from=09:00` | Full Intraday Series |
| **Market Status** | `GET` | `/api/v1/status` | - | `is_open`, `next_open_time` |

---

## 5. Implementation Roadmap
1.  **Phase 1**: `GET /quote/{symbol}` 구현 (Redis 캐시 기반).
2.  **Phase 2**: `get_candles` 쿼리 튜닝 (Date Range Query).
3.  **Phase 3**: Gap Filling 로직 (SQL 레벨 vs App 레벨 결정).
