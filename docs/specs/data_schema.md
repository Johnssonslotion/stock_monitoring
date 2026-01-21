# 데이터 스키마 정의서 (Data Schema Definitions)

## 1. 개요
본 문서는 `stock_monitoring` 시스템 내에서 흐르는 모든 데이터의 표준 형식을 정의한다. 모든 컴포넌트(Collector, Processor, Trader)는 이 스키마를 준수해야 한다.

## 2. 실시간 데이터 (Real-time Data)

### 2.1 틱 데이터 (TickData)
-   **용도**: 체결 내역의 최소 단위.
-   **Redis Channel**: `tick.{exchange}.{symbol}` (예: `tick.upbit.KRW-BTC`)
-   **JSON Structure**:
    ```json
    {
      "source": "upbit",            // 거래소명 (소문자)
      "symbol": "KRW-BTC",          // 통일된 심볼명
      "timestamp": 1704351600000,   // Unix Timestamp (Milliseconds)
      "price": 50000000.0,          // 체결가 (Float)
      "volume": 0.015,              // 체결량 (Float)
      "side": "ask",                // "ask"(매도) or "bid"(매수)
      "id": "TraceID-12345"         // (Optional) 추적용 Unique ID
    }
    ```

### 2.2 오더북 (OrderBook)
-   **용도**: 호가창 스냅샷.
-   **Redis Channel**: `book.{exchange}.{symbol}`
-   **JSON Structure**:
    ```json
    {
      "source": "upbit",
      "symbol": "KRW-BTC",
      "timestamp": 1704351600100,
      "bids": [
        {"price": 49999000, "qty": 0.5},
        {"price": 49998000, "qty": 1.2}
      ],
      "asks": [
        {"price": 50000000, "qty": 0.1},
        {"price": 50001000, "qty": 0.8}
      ]
    }
    ```

## 3. 분석 데이터 (Analytical Data)

### 3.1 캔들 (Candle/OHLCV)
-   **용도**: 기술적 분석용 집계 데이터.
-   **Storage**: DuckDB `candles` Table.
-   **Schema**:
    | Field | Type | Description |
    | :--- | :--- | :--- |
    | ts | TIMESTAMP | 캔들 시작 시간 |
    | symbol | VARCHAR | 심볼 |
    | open | DOUBLE | 시가 |
    | high | DOUBLE | 고가 |
    | low | DOUBLE | 저가 |
    | close | DOUBLE | 종가 |
    | volume | DOUBLE | 거래량 |
    | interval | VARCHAR | '1m', '5m', '1h' |

## 4. 저장소 규칙 (Storage Convention)
-   **DuckDB 파일**: `data/market_data.duckdb`
-   **Parquet 파티셔닝**: `data/archives/ticks/year=2024/month=01/day=04/ticks.parquet`
