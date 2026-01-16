# 데이터 수집 통합 및 최대 구독 전략

## 1. 하이브리드 수집 아키텍처 (Hybrid Collection Architecture)

본 프로젝트는 **KIS(한국투자증권)**를 메인(Core)으로, **Kiwoom(키움증권)**을 특수 목적(Satellite) 및 백업으로 사용하는 하이브리드 전략을 채택합니다.

### 1.1 역할 분담 (Role Allocation)

| Broker | 역할 (Role) | 수집 데이터 (Data Types) | 비고 |
|--------|-------------|--------------------------|------|
| **KIS** | **Primary (주력)** | - 전 종목 실시간 체결 (Tick)<br>- 전 종목 실시간 호가 (Orderbook) | - 제한 없는 구독 가능<br>- Dual Socket 지원 (안정적) |
| **Kiwoom**| **Satellite (보조)** | - **업종지수 (0J)**<br>- **VI 발동/해제 (1h)**<br>- 예상체결 (0H, 장전)<br>- *Backup Ticks* | - 시장 전체 데이터(지수)에 강점<br>- 이벤트 데이터(VI) 수집 가능 |

---

## 2. 최대 구독 한도 (Capacity Planning)

### 2.1 Kiwoom WebSocket 제약 사항 (검증 완료)
- **구독 한도**: **최대 100개 "종목" (Symbol)**
  - *검증 결과*: 종목당 여러 TR(체결+호가)을 등록해도 1개로 카운트됨.
  - 예: A종목(체결+호가) + B종목(체결+호가) = 2개 사용.
- **연결 한도**: 계정당 **1개 WebSocket** 권장.

### 2.2 구독 전략 (Maximizing Stocks Coverage)
**제약 사항(100개)**을 고려하여, **업종지수는 REST Polling으로 전환**하고 WebSocket은 주식 종목에 집중합니다.

1. **지수 (Indices)**: **REST API Polling** (1분 주기)
   - **이유**: 지수 추세는 틱 단위 초고속 데이터가 불필요하며, WebSocket 슬롯(20개)을 절약하여 주식 종목을 더 확보하는 것이 유리함.
   - **대상**: KOSPI, KOSDAQ, KOSPI200, 주요 섹터 지수.

2. **Core Group (Top 40)**: KIS WebSocket
   - **대상**: 시가총액 최상위 40종목 (삼성전자, 선물 등).
   - **데이터**: 틱 + 호가.

3. **Mid-Cap Group (Next 100)**: Kiwoom WebSocket
   - **대상**: 시가총액 41위 ~ 140위.
   - **데이터**: 
     - **주식체결 (0B)** + **주식호가잔량 (0D)** (기본)
     - **VI 발동 (1h)** (종목 등록 시 **무료**로 포함: Type 리스트에 `1h` 추가해도 슬롯 차감 없음)
   
**총 커버리지**: **140개 종목 (KIS 40 + Kiwoom 100)**
- *기존 전략(120개) 대비 +20개 확장 효과.*


---

## 3. 데이터 통합 및 정규화 (Normalization)

서로 다른 브로커의 데이터를 통일된 내부 포맷으로 변환하여 시스템(Redis/DB)에 공급합니다.

### 3.1 Tick Data (체결) 표준 포맷
Redis Channel: `stock:tick:kr:{symbol}`

```json
{
  "source": "kis" | "kiwoom",
  "symbol": "005930",
  "timestamp": 1705300000.123,
  "price": 70500,
  "volume": 10,
  "ask_price": 70600,  # 최우선 매도호가
  "bid_price": 70500,  # 최우선 매수호가
  "aggressor_side": "buy" | "sell" | "unknown"
}
```

- **Kiwoom 전처리**: 
  - `10`(현재가), `27`(매도), `28`(매수) 필드 매핑.
  - 타임스탬프가 없는 경우 수신 시점(System Time) 사용.

### 3.2 Orderbook (호가) 표준 포맷
Redis Channel: `stock:orderbook:kr:{symbol}`

```json
{
  "source": "kis" | "kiwoom",
  "symbol": "005930",
  "timestamp": 1705300000.123,
  "bids": [{"price": 70500, "qty": 1000}, ...],  # 1~10호가
  "asks": [{"price": 70600, "qty": 1200}, ...]   # 1~10호가
}
```

### 3.3 Index/Event 표준 포맷 (Kiwoom Exclusive)

**업종지수**: `market:index:kr:{symbol}`
```json
{
  "source": "kiwoom",
  "symbol": "001",  # KOSPI
  "price": 2500.50,
  "change": 10.5,
  "timestamp": ...
}
```

**VI 발동**: `market:event:vi`
```json
{
  "symbol": "005930",
  "type": "VI_STATIC" | "VI_DYNAMIC",
  "status": "ACTIVE" | "RELEASED",
  "time": "10:00:00"
}
```

---

## 4. 장애 대응 (Failover Plan)

1. **KIS 장애 감지**:
   - 10초간 Heartbeat 누락 또는 `ConnectionClosed`.
   
2. **Kiwoom 전환 (Fallback)**:
   - 즉시 `KiwoomWSCollector`에 **Core Watchlist (KOSPI200 Top 50)**에 대한 `REG`(주식체결 0B) 요청 전송.
   - *주의*: 기존 Upstream(지수 등)은 유지(`refresh=1`).
   
3. **복구 (Recovery)**:
   - KIS 재연결 성공 시, Kiwoom의 종목 구독 해제(`REMOVE`) 후 KIS로 복귀.

## 5. 결론 및 승인 요청
- **데이터 통합**: 표준 포맷 정의 완료.
- **최대 구독**: Kiwoom은 **보조(Satellite)** 역할로 한정하며, 대량 데이터 수집은 KIS에 집중.
- **승인 요청**: 위 전략에 따라 `KiwoomWSCollector` 및 `unified_collector.py` 구현을 진행하겠습니다.
