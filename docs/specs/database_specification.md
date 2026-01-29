# Database Specification (v1.1)

## 1. 개요 (Overview)
본 문서는 `Stock Monitoring System`의 영구 저장소인 **TimescaleDB**의 스키마와 데이터 수명 주기(Retention)를 정의합니다.
모든 DB 마이그레이션 스크립트와 ORM/DAO 코드는 이 명세를 준수해야 합니다.

## 2. 접속 정보 (Connection Info)
- **Env Params**: `DB_HOST`, `DB_PORT` (5432), `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- **Driver**: `asyncpg` (Async PostgreSQL Driver)

## 3. 스키마 명세 (Schema Specification)

### 3.1 틱 데이터 (Market Ticks)
- **Table Name**: `market_ticks`
- **Type**: Hypertable (Partition by `time`)
- **Retention**: 7 Days (Hot), DuckDB Export after (Cold) - See `docs/data_management_strategy.md`

| Column | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| **time** | `TIMESTAMPTZ` | **No** | 거래 발생 시간 (UTC) |
| **symbol** | `TEXT` | **No** | 종목 코드 (예: 005930, AAPL) |
| **source** | `TEXT` | **No** | 출처 (KIS, KIWOOM) |
| **price** | `DOUBLE` | **No** | 체결가 |
| **volume** | `DOUBLE` | No | 체결량 (순간 거래량) |
| **change** | `DOUBLE` | Yes | 전일 대비 등락 |

### 3.2 호가 데이터 (Market Orderbook)
- **Table Name**: `market_orderbook`
- **Type**: Hypertable
- **Depth**: 10 Levels (Ask 10 + Bid 10)

| Column | Type | Description |
| :--- | :--- | :--- |
| **time** | `TIMESTAMPTZ` | 수신 시간 |
| **symbol** | `TEXT` | 종목 코드 |
| **source** | `TEXT` | 출처 |
| **ask_price[1-10]** | `DOUBLE` | 매도 호가 1~10단계 |
| **ask_vol[1-10]** | `DOUBLE` | 매도 잔량 1~10단계 |
| **bid_price[1-10]** | `DOUBLE` | 매수 호가 1~10단계 |
| **bid_vol[1-10]** | `DOUBLE` | 매수 잔량 1~10단계 |

*(Note: 총 43개 컬럼. `ask_price1` ... `bid_vol10`)*

### 3.3 분봉 데이터 (Market Candles) [ISSUE-044]
#### 3.3.1 Continuous Aggregate Views (Auto-Generated)
- **Source**: `market_ticks`
- **Type**: Materialized View (TimescaleDB Continuous Aggregate)
- **Strategy**: Flat (Todos directly from Ticks)

| View Name | Interval | Refresh Policy | Source Type |
| :--- | :--- | :--- | :--- |
| `market_candles_1m_view` | 1 Minute | Every 1 min (Lag: 1min) | Derived from Ticks |
| `market_candles_5m_view` | 5 Minutes | Every 5 min | Derived from Ticks |
| `market_candles_1h_view` | 1 Hour | Every 1 hour | Derived from Ticks |
| `market_candles_1d_view` | 1 Day | Daily (16:00) | Derived from Ticks |

#### 3.3.2 Serving Views (Unified)
- **Strategy**: Ground Truth Policy (REST API 우선, 없으면 Tick Aggregation 사용)

| View Name | Description |
| :--- | :--- |
| `market_candles_1m_serving` | 1분봉 통합 서빙 (Priority Logic Applied) |
| `market_candles_5m_serving` | 5분봉 통합 서빙 |
| `market_candles_1h_serving` | 1시간봉 통합 서빙 |
| `market_candles_1d_serving` | 일봉 통합 서빙 |

### 3.4 시스템 메트릭 (System Metrics)
- **Table Name**: `system_metrics`
- **Type**: Hypertable

| Column | Type | Description |
| :--- | :--- | :--- |
| **time** | `TIMESTAMPTZ` | 측정 시간 |
| **type** | `TEXT` | 메트릭 유형 (cpu, memory, disk, network) |
| **value** | `DOUBLE` | 측정값 |
| **meta** | `JSONB` | 추가 메타데이터 (예: `{"host": "prod-1"}`) |

### 3.5. Data Validation (ISSUE-029)
**Table**: `market_ticks_validation`
**Type**: Hypertable (Partition by `bucket_time`)

| Column | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `bucket_time` | TIMESTAMPTZ | NO | Minute bucket timestamp (PK) |
| `symbol` | TEXT | NO | Stock symbol (PK) |
| `tick_count_collected` | INTEGER | YES | Number of ticks collected in this minute |
| `volume_sum` | DOUBLE PRECISION | YES | Sum of validation volume |
| `price_open` | DOUBLE PRECISION | YES | Open price of the minute |
| `price_high` | DOUBLE PRECISION | YES | High price of the minute |
| `price_low` | DOUBLE PRECISION | YES | Low price of the minute |
| `price_close` | DOUBLE PRECISION | YES | Close price of the minute |
| `updated_at` | TIMESTAMPTZ | YES | Last update timestamp (Default: NOW()) |
| `validation_status` | TEXT | YES | Validation result status |

### 3.6 투자자별 매매동향 (Investor Trends) [Pillar 8]
- **Table Name**: `market_investor_trends`
- **Type**: Hypertable (Partition by `time`)

| Column | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| **time** | `TIMESTAMPTZ` | **No** | 수집 기준 시간 (Daily/Min) |
| **symbol** | `TEXT` | **No** | 종목 코드 |
| **fore_ntby_qty** | `BIGINT` | Yes | 외국인 순매수 수량 |
| **orgn_ntby_qty** | `BIGINT` | Yes | 기관 순매수 수량 |
| **pstn_ntby_qty** | `BIGINT` | Yes | 개인 순매수 수량 |
| **fore_pstn_rate** | `DOUBLE` | Yes | 외국인 보유 지분율 |

### 3.7 공매도 현황 (Short Selling Status) [Pillar 8]
- **Table Name**: `market_short_selling`
- **Type**: Hypertable (Partition by `time`)

| Column | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| **time** | `TIMESTAMPTZ` | **No** | 수취 일자/시간 |
| **symbol** | `TEXT` | **No** | 종목 코드 |
| **short_vol** | `BIGINT` | Yes | 공매도 거래량 |
| **short_amt** | `BIGINT` | Yes | 공매도 거래 대금 |
| **short_balance** | `BIGINT` | Yes | 공매도 잔고 수량 |
| **short_bal_amt** | `BIGINT` | Yes | 공매도 잔고 금액 |

**Indexes**:
- `market_ticks_validation_bucket_time_idx` (Derived from Hypertable)
- Unique Constraint: `(bucket_time, symbol)`

**Retention Policy**:
- 30 days (Validation data is for short-term audit)

## 4. 인덱스 전략 (Indexing Strategy)
- `market_ticks_symbol_time_idx`: `(symbol, time DESC)` - 종목별 최신 조회 최적화.
- `market_orderbook_symbol_time_idx`: `(symbol, time DESC)`

## 5. 알려진 이슈 (Known Issues)
> [!WARNING]
> 현재 `timescale_archiver.py` 코드 상 `market_orderbook` 테이블 생성 로직이 누락되어 있음. (Manual Creation 필요 상태) -> **Migration Script 작성 필요**.
