# Target Portfolio Allocation (v3.0)

## 📊 Summary (Slot Management)
| Broker | Role | Capacity | Description |
|--------|------|----------|-------------|
| **KIS** | **Speed Core** | **40** | 초고속 트레이딩 대상 (틱/호가 필수) |
| **Kiwoom** | **Coverage** | **100** | 시장 상황 파악 및 섹터 로테이션 (틱/호가/VI) |
| **Kiwoom** | **Trend** | N/A (REST) | 시장 지수 (1분 주기 Polling) |

---

## 1. KIS Allocation (Speed Core: 40 Slots)
*Strategy: Absolute Speed & Liquidity*

### 1.1 Core ETFs (Market Leaders: 5 Slots)
시장 전체 변동성을 주도하거나 헷징에 필수적인 ETF.
KIS의 무제한(사실상 대용량) 처리 능력을 활용.

| Symbol | Name | Type | Key Reason |
|--------|------|------|------------|
| **069500** | KODEX 200 | Market | 현물 바스켓 표준 |
| **122630** | KODEX 레버리지 | Leverage | 단타/스캘핑 거래량 1위 |
| **252670** | KODEX 200선물인버스2X | Inverse 2X | 하락장 헷징 (곱버스) |
| **233740** | KODEX 코스닥150레버리지 | Leverage | 코스닥 변동성 추적 |
| **251340** | KODEX 코스닥150선물인버스 | Inverse | 코스닥 하락 헷징 |

### 1.2 Top Tier Stocks (Market Movers: 35 Slots)
KOSPI/KOSDAQ 시가총액 및 거래대금 최상위 종목.

| Symbol | Name | Sector | Priority |
|--------|------|--------|----------|
| **005930** | 삼성전자 | Tech | 1 (지수 영향력 20%+) |
| **000660** | SK하이닉스 | Tech | 2 |
| **373220** | LG에너지솔루션 | Battery | 3 |
| **207940** | 삼성바이오로직스 | Bio | 4 |
| **005380** | 현대차 | Auto | 5 |
| **000270** | 기아 | Auto | 6 |
| **005490** | POSCO홀딩스 | Materials | 7 |
| **035420** | NAVER | Internet | 8 |
| **035720** | 카카오 | Internet | 9 |
| **051910** | LG화학 | Chem | 10 |
| **006400** | 삼성SDI | Battery | 11 |
| ... | *(Dynamic Top 35)* | | |

---

## 2. Kiwoom Allocation (Coverage: 100 Slots)
*Strategy: Broad Context & Sector Rotation*

### 2.1 Sector/Theme ETFs (Key Themes: 20 Slots)
시장 주도 테마를 파악하기 위한 대표 ETF.

| Symbol | Name | Theme |
|--------|------|-------|
| 364980 | TIGER 2차전지테마 | Battery |
| 091160 | KODEX 반도체 | Semiconductor |
| 117680 | KODEX 철강 | Steel/Materials |
| 139260 | TIGER 200 IT | IT Hardware |
| 143860 | TIGER 헬스케어 | Bio/Healthcare |
| 261220 | KODEX WTI원유선물(H) | Energy |
| 132030 | KODEX 골드선물(H) | Precious Metal |
| ... | *(Selected 20)* | |

### 2.2 Mid-Cap & Growth (Growth Movers: 80 Slots)
시가총액 36위 ~ 115위, 또는 급등락 감시(Watchlist) 대상.

- **Examples**: 에코프로, 에코프로비엠, 셀트리온헬스케어, 두산로보틱스 등
- **Focus**: 변동성이 커지면 KIS(Core)로 승격될 후보군.

---

## 3. Kiwoom REST Allocation (Indices)
*Strategy: Macro Trend (Polling)*

### 3.1 Market Indices
| Symbol | Name | Description |
|--------|------|-------------|
| **001** | KOSPI | 코스피 종합 |
| **002** | KOSPI Large | 코스피 대형주 |
| **201** | KOSPI 200 | 코스피 200 |
| **101** | KOSDAQ | 코스닥 종합 |
| **150** | KOSDAQ 150 | 코스닥 150 |

---

## ⚠️ Operation Rules (운영 규칙)

1. **Rebalancing (리밸런싱)**:
   - 매주 금요일 장 마감 후 시가총액/거래대금 기준으로 List 업데이트.
   - `scripts/update_portfolio_lists.py` (To be implemented)

2. **Emergency Promotion (긴급 승격)**:
   - Kiwoom(Mid-Cap) 종목의 거래량이 폭증(전일 대비 500%+)하면 KIS(Core)의 하위 종목을 탈락시키고 즉시 승격. (Phase 2 feature)
