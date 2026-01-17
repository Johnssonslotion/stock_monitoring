# Database Specification (v1.0)

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
- **Retention**: 30 Days (Hot), S3 Export after (Cold)

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

### 3.3 시스템 메트릭 (System Metrics)
- **Table Name**: `system_metrics`
- **Type**: Hypertable

| Column | Type | Description |
| :--- | :--- | :--- |
| **time** | `TIMESTAMPTZ` | 측정 시간 |
| **type** | `TEXT` | 메트릭 유형 (cpu, memory, disk, network) |
| **value** | `DOUBLE` | 측정값 |
| **meta** | `JSONB` | 추가 메타데이터 (예: `{"host": "prod-1"}`) |

## 4. 인덱스 전략 (Indexing Strategy)
- `market_ticks_symbol_time_idx`: `(symbol, time DESC)` - 종목별 최신 조회 최적화.
- `market_orderbook_symbol_time_idx`: `(symbol, time DESC)`

## 5. 알려진 이슈 (Known Issues)
> [!WARNING]
> 현재 `timescale_archiver.py` 코드 상 `market_orderbook` 테이블 생성 로직이 누락되어 있음. (Manual Creation 필요 상태) -> **Migration Script 작성 필요**.
