# 데이터 스키마 정의서 (Data Schema Definitions)

## 1. 개요
본 문서는 `stock_monitoring` 시스템 내에서 흐르는 모든 데이터의 표준 형식을 정의한다. 모든 컴포넌트(Collector, Processor, Trader)는 이 스키마를 준수해야 한다.

## 2. 실시간 데이터 (Real-time Data)

### 2.1 틱 데이터 (TickData)
-   **용도**: 체결 내역의 최소 단위 및 TimescaleDB 적재.
-   **Metadata (Common)**:
    - `broker`: 데이터 소스 거래소 (예: "KIS", "KIWOOM")
    - `broker_time`: 거래소가 제공한 원본 시간 (TIMESTAMPTZ)
    - `received_time`: 우리 시스템 수신 시간 (TIMESTAMPTZ / Pinning Target)
    - `sequence_number`: 데이터 고유 순번 (Deduplication Key)
    - `source`: 상위 시스템 구분 (KIS/KIWOOM)
-   **JSON Structure**:
    ```json
    {
      "symbol": "005930",
      "price": 72000.0,
      "volume": 150.0,
      "change": 0.5,
      "timestamp": "2026-01-21T15:00:00+09:00",
      "broker": "KIWOOM",
      "broker_time": "2026-01-21T14:59:59+09:00",
      "received_time": "2026-01-21T15:00:00.123456+09:00",
      "sequence_number": 1234567,
      "source": "KIWOOM"
    }
    ```

### 2.2 오더북 (OrderBook)
-   **용도**: 실시간 호가 잔량 정보.
-   **Schema (Flat 43-Column Structure)**:
    - `time`, `symbol`, `source`, `broker`, `broker_time`, `received_time`, `sequence_number`
    - `ask_price1` ~ `ask_price10` (매도 호가 1~10단)
    - `ask_vol1` ~ `ask_vol10` (매도 잔량 1~10단)
    - `bid_price1` ~ `bid_price10` (매수 호가 1~10단)
    - `bid_vol1` ~ `bid_vol10` (매수 잔량 1~10단)

## 3. 저장소 및 분석 데이터 (Storage & Analytics)

### 3.1 TimescaleDB (Main Storage)
- **Table**: `market_ticks`, `market_orderbook`
- **SSoT**: `migrations/*.sql` 파일을 따름.

### 3.2 캔들 (Candle/OHLCV)
-   **용도**: 기술적 분석용 집계 데이터.
-   **Storage**: TimescaleDB `market_candles` Table.
-   **Schema**:
    | Field | Type | Description |
    | :--- | :--- | :--- |
    | time | TIMESTAMPTZ | 캔들 시작 시간 |
    | symbol | TEXT | 심볼 |
    | interval | TEXT | '1m', '5m', '1h' |
    | open/high/low/close | DOUBLE | 시가/고가/저가/종가 |
    | volume | DOUBLE | 거래량 |
