# 트레이딩 데이터 관리 전략 (Trading Data Management Strategy)

**Version**: 2.0 (Integrated)
**Date**: 2026-01-20
**Scope**: Acquisition -> Storage -> Retention -> Access
**Status**: Active Strategy

---

## 1. Executive Summary

본 문서는 주식 데이터의 **획득(Acquisition)**부터 **저장(Storage)**, **수명 주기(Lifecycle)**, **접근(Access)**에 이르는 전 과정을 규정합니다.
Zero-Cost 원칙과 고성능 조회를 위해 **Hybrid Storage Tiering (TimescaleDB + DuckDB)** 전략을 채택합니다.

---

## 2. 데이터 수명 주기 및 저장 정책 (Data Lifecycle & Storage Policy)

### 2.1 Hybrid Storage Tiering
데이터의 접근 빈도(Hot/Cold)와 용도에 따라 저장소를 이원화하여 비용 효율성과 성능을 극대화합니다.

| Tier | Role | Storage | Retention | Scope | Access Pattern |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1 (Hot)** | 실시간 모니터링, 단기 차트, 알림 | **TimescaleDB** (Hypertable) | **최근 7일** (Raw Tick), **영구** (Candle) | Raw Tick, Orderbook | `SELECT * FROM market_ticks WHERE time > NOW() - 7d` |
| **Tier 2 (Cold)** | 백테스팅, 장기 차트 분석, 감사 | **DuckDB** (Parquet) | **영구 (Permanent)** | Raw Tick, Orderbook (Full) | API(File Read) or Local Analysis |

### 2.2 Retention Rules
1. **Raw Data (Tick/Orderbook)**:
   - TimescaleDB: 7일 후 **자동 삭제 (Drop Chunk)**.
   - DuckDB: **영구 보관**. (매일/매주 배치로 TimescaleDB -> Parquet 이관 후 Timescale에서 삭제).
2. **Candle Data (1m/1h/1d)**:
   - TimescaleDB: **영구 보관**. (용량이 작으므로 삭제 불필요).
   - 앱/차트에서는 주로 이 데이터를 조회함.

---

## 2. 데이터 분류 체계

### 2.1 Tier 0: 필수 (Critical) - 이미 수집 중
| 항목 | 현재 상태 | 용도 |
|------|-----------|------|
| 체결가 (Price) | ✅ 수집 중 | 차트, 수익률 계산 |
| 거래량 (Volume) | ✅ 수집 중 | 거래 활동 분석 |
| 시가/고가/저가/종가 (OHLC) | ✅ 일봉 생성 | 캔들 차트 |

---

### 2.2 Tier 1: 고우선순위 (High Priority) - 즉시 추가 권장

#### **그룹 A: 필터링 및 스크리닝**
| 항목 | 데이터 타입 | 비즈니스 가치 | 저장 비용 |
|------|-------------|---------------|-----------|
| **시가총액** | BIGINT | 🔥 **CRITICAL** - Map 크기 결정 | 8 bytes/종목 |
| **업종구분** | VARCHAR(50) | 섹터 필터링 | 20 bytes/종목 |
| **KOSPI200구분** | BOOLEAN | 대형주 필터 | 1 byte/종목 |
| **거래정지여부** | BOOLEAN | 거래 불가 종목 제외 | 1 byte/종목 |
| **관리종목여부** | BOOLEAN | 리스크 높은 종목 경고 | 1 byte/종목 |
| **정리매매여부** | BOOLEAN | 상장폐지 예정 | 1 byte/종목 |

**총 저장 비용**: ~30 bytes/종목 × 2,500 = **75KB** (무시할 수 있는 수준)

**획득 방법**: KRX 공개 API 또는 무료 Open API (FinanceDataReader 등)

---

#### **그룹 B: 밸류에이션 (무료 확인 필요)**
| 항목 | 데이터 타입 | 비즈니스 가치 | 갱신 빈도 |
|------|-------------|---------------|-----------|
| **주가수익비율 (PER)** | FLOAT | Value/Growth 구분 | 일 1회 |
| **배당수익률** | FLOAT | 배당주 스크리닝 | 분기 1회 |
| **자본금** | BIGINT | 재무 건전성 | 분기 1회 |

**저장 비용**: ~16 bytes/종목 = **40KB**

**획득 방법**: 
- 🆓 **무료**: `yfinance`, `FinanceDataReader` (PER, 배당수익률)
- 💰 **유료**: KRX 직접 구매

**권장**: 무료 소스 우선 사용, 누락 시 KRX 고려

---

### 2.3 Tier 2: 중우선순위 (Medium Priority) - Phase 3+ 검토

#### **그룹 C: 거래 메타데이터**
| 항목 | 비즈니스 가치 | 복잡도 |
|------|---------------|--------|
| **상한가/하한가** | 가격 리밋 표시 | Low |
| **매매수량단위** | 주문 검증 | Low |
| **락구분** | 배당/분할 감지 | Medium |
| **등락구분코드** | 등락 상태 색상 | Low |

**저장 비용**: ~20 bytes/종목 = **50KB**

**획득 시기**: Phase 3 (주문 기능 추가 시)

---

### 2.4 Tier 3: 저우선순위 (Low Priority) - 전문가 기능

#### **그룹 D: 시장 미시구조 (Market Microstructure)**

이 지표들은 **HFT(고빈도 거래)** 또는 **마켓 메이킹** 전략에 필요하나, 일반 투자자에게는 과도한 정보입니다.

| 지표 그룹 | 예시 | 저장 비용 (일별) | 비즈니스 가치 |
|-----------|------|------------------|---------------|
| **거래속도** | 거래빈도 기준 5일/10일/20일/60일 | 32 bytes × 2,500 = 80KB | ⚠️ 전문가 전용 |
| **취소율** | IOC/FOK 취소주문량, 주문빈도 기준 취소율 | 24 bytes × 2,500 = 60KB | ⚠️ Spoofing 탐지용 |
| **불균형** | 매수매도불균형, 주문불균형 | 32 bytes × 2,500 = 80KB | ⚠️ 유동성 분석 |
| **스프레드** | 평균호가/비율/유효/실현 스프레드 | 32 bytes × 2,500 = 80KB | ⚠️ 체결 비용 분석 |
| **역선택** | HS 역선택 비용 | 8 bytes × 2,500 = 20KB | ⚠️ 고급 연구용 |

**총 저장 비용 (일별)**: ~300KB × 365일 = **~110MB/년**

**문제점**:
1. **비용**: KRX 유료 데이터일 가능성 높음 (무료 확인 필요)
2. **복잡도**: 해석에 도메인 전문 지식 필요
3. **리소스**: TimescaleDB 압축 적용해도 수백 MB 점유

**권장**: Phase 5+ 또는 연구 목적으로만 고려

---

## 2.5 Tier 4: 데이터 무결성 검증 (Data Integrity Validation)

### 2.5.1 Volume Cross-Check (Primary)
- **목적**: 데이터 누락 및 이상치 탐지 (Anomaly Detection)
- **방법**: `API.MinuteVolume` vs `DB.SumTickVolume` 교차 검증
    - API: KIS 분봉(`FHKST03010200`) 또는 Kiwoom 분봉(`ka10080`)
    - 오차율 허용범위: < 0.1%
- **장점**: O(1) 비용으로 전체 정합성 확인 가능

### 2.5.2 Tick Counting (Secondary)
- **목적**: 정밀 검증 (Deep Verification)
- **Trigger**: Volume Cross-Check 실패 시 수행
- **방법**: Kiwoom 틱 차트(`ka10079`) 페이징 조회로 전수 카운팅

---

## 2.6 복구 전략 (Recovery Strategy)

### 2.6.1 Dual Tick Recovery
- **Primary**: KIS REST API (`FHKST01010300`)
    - 장점: 단순함, Rate Limit (20req/sec) 준수 필요
- **Secondary**: Kiwoom REST API (`ka10079`)
    - 장점: 틱 차트 제공, 당일 전수 복구 가능
    - 조건: Primary 실패 시 자동 절체 (Failover)

---

## 3. 6인 페르소나 의견

### 👔 PM (Product Manager)
**"Tier 1만 추가해도 사용자 경험이 10배 향상됩니다."**

시가총액과 업종구분만 있어도:
- Market Map 크기 정확도 ↑
- "KOSPI 200 대형주만 보기" 필터 가능
- 관리종목 경고 배지 표시

**비용 대비 효과가 최고인 Tier 1 그룹 A/B를 즉시 추가하고, Tier 3는 Phase 5 이후로 연기합니다.**

---

### 📊 Data Scientist (DS)
**"시장 미시구조 지표는 매력적이나, 우리의 Use Case와 맞지 않습니다."**

**Tier 1 (필수)**:
- 시가총액: Map 시각화의 핵심
- 업종구분: 섹터 로테이션 분석 필수
- PER/배당수익률: Value/Growth 구분

**Tier 3 (보류)**:
- 거래속도, 취소율, 스프레드 등은 **밀리초 단위 의사결정**이 필요한 HFT 전용
- 우리는 "분~일" 단위 투자 결정을 지원하므로 불필요
- 데이터 해석에 전문 논문급 지식 필요 (예: HS 역선택 비용은 Hasbrouck 1991 논문 기반)

**결론**: Tier 1만으로 충분. Tier 3는 학술 연구용으로만 고려.

---

### 🖥️ Infra (Infrastructure Engineer)
**"Tier 3 추가 시 스토리지 예산 재검토 필수."**

**현재 상태**:
- TimescaleDB 할당: 8GB
- 현재 사용량: ~2GB (7일 틱 데이터)

**Tier 3 추가 시 영향**:
- 50개 지표 × 2,500 종목 × 365일 = **~110MB/년**
- 압축 비율 10:1 가정 → **11MB/년** (관리 가능)

**하지만**:
- 갱신 빈도가 "실시간"이면 틱 데이터급 부하
- 쿼리 복잡도 증가 → 인덱스 필요 → 추가 디스크

**권장**: Tier 1은 안전, Tier 3는 별도 DuckDB 테이블로 격리 (Cold Storage)

---

### 💻 Dev (Developer)
**"Tier 1은 1주일, Tier 3는 1개월+ 작업량."**

**Tier 1 구현 (그룹 A/B)**:
1. DB 스키마 확장: `ALTER TABLE market_ticks ADD COLUMN ...` (1일)
2. KRX API 또는 무료 소스 파싱 (2일)
3. 일 1회 배치 작업 (cron) (1일)
4. Frontend 필터 UI (2일)

**총: 1주일**

**Tier 3 구현**:
- 50개 컬럼 추가
- 복잡한 집계 로직 (이동평균, 불균형 계산)
- 별도 테이블 설계 필요 (정규화)
- 데이터 검증 로직 (이상치 많을 것으로 예상)

**총: 1개월+**

**권장**: Tier 1 먼저 배포, 사용자 피드백 후 Tier 3 결정

---

### ✅ QA (Quality Assurance)
**"Tier 3 데이터 품질 검증이 어렵습니다."**

**Tier 1 검증**:
- 시가총액 = 종가 × 상장주식수 (계산 검증 가능)
- 업종구분: 공식 분류 체계와 대조
- PER: 재무제표와 교차 검증

**Tier 3 검증**:
- "평균유효 스프레드"가 정확한지 어떻게 검증?
- "HS 역선택 비용" 계산식조차 모호
- 이상치(Outlier) 판단 기준 불명확

**우려사항**:
- 잘못된 미시구조 지표로 투자 결정 → 재무 손실 위험
- 데이터 출처(KRX vs 무료 소스) 불일치 시 책임 소재

**권장**: Tier 1만 먼저 QA 통과, Tier 3는 "베타" 기능으로 표시

---

### 🏗️ Architect (Solution Architect)
**"데이터 계층을 명확히 분리해야 합니다."**

**제안 아키텍처**:

```
┌─ Tier 1 (Hot Data) ─────────────────┐
│ TimescaleDB: market_ticks            │
│ + 시가총액, 업종구분, PER 등           │
│ → Real-time Query (< 100ms)         │
└─────────────────────────────────────┘

┌─ Tier 3 (Cold Data) ────────────────┐
│ DuckDB: market_microstructure        │
│ + 거래속도, 취소율, 스프레드 등         │
│ → Analytical Query (1~10s OK)       │
└─────────────────────────────────────┘
```

**이점**:
- Tier 1: 실시간 대시보드용 (빠른 접근)
- Tier 3: 분석/연구용 (압축률 우선)

**구현 복잡도**: Medium (DuckDB 이미 사용 중이므로 기존 패턴 재사용)

---

## 4. 최종 권고안 (Council Consensus)

### ✅ Phase 2B: Tier 1 그룹 A (즉시 추가)

| 항목 | 획득 방법 | 갱신 빈도 | 저장 위치 |
|------|-----------|-----------|-----------|
| 시가총액 | `yfinance` 또는 KRX 무료 API | 일 1회 | TimescaleDB `market_metadata` |
| 업종구분 | KRX 공개 데이터 | 분기 1회 | PostgreSQL `symbol_sectors` |
| KOSPI200구분 | KRX 공개 데이터 | 분기 1회 | PostgreSQL `symbol_metadata` |
| 거래정지여부 | KRX 실시간 | 실시간 (5분 폴링) | Redis (캐시) + TimescaleDB |
| 관리종목여부 | KRX 공개 데이터 | 일 1회 | PostgreSQL `symbol_metadata` |

**예상 작업량**: 1주 (Dev 1명)  
**예상 저장 비용**: < 100KB (무시 가능)  
**배포 우선순위**: **HIGH**

---

### ⏸️ Phase 3+: Tier 1 그룹 B (조건부)

| 항목 | 조건 | 비고 |
|------|------|------|
| PER, 배당수익률 | 무료 소스 확인 후 | `yfinance`에 있으면 추가 |
| 자본금, 상장주식수 | KRX 무료 제공 시 | 시가총액 계산용 |

**배포 우선순위**: **MEDIUM**

---

### ❌ Phase 5+: Tier 3 (보류)

**사유**:
1. **비용 불명확**: KRX 유료 데이터일 가능성
2. **사용자 니즈 불분명**: HFT 아닌 일반 투자자에게 과도
3. **리소스 부담**: 110MB/년은 작아 보이나, 쿼리 복잡도 ↑

**재검토 조건**:
- 사용자가 명시적으로 "스프레드 분석" 같은 고급 기능 요청
- KRX가 해당 데이터를 무료로 제공
- Phase 5 도달 (백테스팅 엔진 완성 후)

---

## 5. 구현 계획 (Implementation Plan)

### Step 1: 무료 데이터 소스 확인 (2일)
```python
# POC: Check free data availability
import yfinance as yf
import FinanceDataReader as fdr

# Test case: Samsung Electronics
ticker = yf.Ticker("005930.KS")
info = ticker.info

print("Market Cap:", info.get('marketCap'))
print("Sector:", info.get('sector'))
print("PE Ratio:", info.get('trailingPE'))
print("Dividend Yield:", info.get('dividendYield'))
```

### Step 2: DB 스키마 설계 (1일)
```sql
-- New table: symbol_metadata
CREATE TABLE symbol_metadata (
    symbol VARCHAR(10) PRIMARY KEY,
    market_cap BIGINT,
    sector VARCHAR(50),
    is_kospi200 BOOLEAN,
    is_halted BOOLEAN,
    is_managed BOOLEAN,  -- 관리종목
    is_delisting BOOLEAN, -- 정리매매
    per FLOAT,
    dividend_yield FLOAT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for filtering
CREATE INDEX idx_sector ON symbol_metadata(sector);
CREATE INDEX idx_market_cap ON symbol_metadata(market_cap DESC);
```

### Step 3: 데이터 수집 스크립트 (3일)
```python
# scripts/collect_metadata.py
async def collect_metadata(symbols: List[str]):
    """일 1회 실행, cron: 0 18 * * * (장 마감 후)"""
    for symbol in symbols:
        # 1. yfinance에서 데이터 가져오기
        data = fetch_from_yfinance(symbol)
        
        # 2. DB 업데이트
        await db.execute("""
            INSERT INTO symbol_metadata (symbol, market_cap, sector, ...)
            VALUES ($1, $2, $3, ...)
            ON CONFLICT (symbol) DO UPDATE SET ...
        """, symbol, data['market_cap'], ...)
```

### Step 4: API 엔드포인트 추가 (1일)
```python
# src/api/main.py
@app.get("/api/v1/metadata/{symbol}")
async def get_symbol_metadata(symbol: str):
    """종목 메타데이터 조회"""
    row = await db.fetchrow("""
        SELECT * FROM symbol_metadata WHERE symbol = $1
    """, symbol)
    
    return dict(row)
```

### Step 5: Frontend 필터 UI (2일)
```tsx
// components/MarketMapFilters.tsx
const [filters, setFilters] = useState({
  onlyKOSPI200: false,
  excludeHalted: true,
  excludeManaged: true,
  sectors: []
});

// Apply filters to Market Map data
const filteredData = marketData.filter(item => {
  if (filters.onlyKOSPI200 && !item.is_kospi200) return false;
  if (filters.excludeHalted && item.is_halted) return false;
  if (filters.excludeManaged && item.is_managed) return false;
  if (filters.sectors.length > 0 && !filters.sectors.includes(item.sector)) return false;
  return true;
});
```

---

## 6. 비용 편익 분석 (Cost-Benefit Analysis)

| Tier | 개발 비용 | 저장 비용 | 사용자 가치 | ROI |
|------|-----------|-----------|-------------|-----|
| **Tier 1-A** | 1주 | < 100KB | ⭐⭐⭐⭐⭐ 필터링 핵심 | **매우 높음** |
| **Tier 1-B** | 3일 | < 50KB | ⭐⭐⭐⭐ 밸류에이션 | **높음** |
| **Tier 2** | 1주 | < 100KB | ⭐⭐⭐ 주문 검증용 | 중간 |
| **Tier 3** | 1개월+ | ~110MB/년 | ⭐ HFT 전문가만 | **매우 낮음** |

---

## 7. 리스크 및 완화 전략

| 리스크 | 확률 | 영향 | 완화 전략 |
|--------|------|------|-----------|
| 무료 소스 데이터 품질 낮음 | Medium | Medium | KRX 공식 데이터와 교차 검증 |
| KRX API 비용 발생 | Low | High | 무료 소스 먼저, KRX는 마지막 수단 |
| Tier 3 데이터 해석 오류 | High | Critical | "베타" 태그 + 면책 조항 |

---

## 8. 최종 결정 (Final Decision)

> [!IMPORTANT]
> **Council of Six - 만장일치 승인**
>
> **Phase 2B에서 Tier 1 그룹 A (시가총액, 업종구분, 거래정지 등) 즉시 추가.**
>
> **Tier 3 (시장 미시구조)는 Phase 5 이후로 연기. 사용자 니즈 검증 후 재검토.**

**PM의 최종 조율**: 
*"데이터 추가의 황금률은 '80/20 법칙'입니다. Tier 1 그룹 A 6개 항목(20%)으로 사용자 가치의 80%를 달성할 수 있습니다. Tier 3 50개 항목은 나머지 20%를 위한 80%의 노력입니다. 우선순위가 명확합니다."*

---

**참고 문서**:
- [UI Design Master Document](./ui_design_master.md)
- [Master Roadmap](./strategies/master_roadmap.md)
- [AI Rules](./../.ai-rules.md)

---

---

## 9. 일중 시세 데이터 선택 전략 (Intraday Tick Data)

### 9.1 KRX 일중 시세 항목 분류

KRX는 일중 시세를 **대상항목 A**(기본)와 **대상항목 B**(고급)로 구분합니다.

---

#### **대상항목 A: 기본 OHLCV + 호가**

| 항목 | 현재 상태 | 비즈니스 가치 | 권장 |
|------|-----------|---------------|------|
| **시가** | ✅ 수집 중 (일봉 생성) | 캔들 차트 필수 | ✅ **KEEP** |
| **고가** | ✅ 수집 중 | 캔들 차트 필수 | ✅ **KEEP** |
| **저가** | ✅ 수집 중 | 캔들 차트 필수 | ✅ **KEEP** |
| **거래량** | ✅ 수집 중 | 거래 활동 분석 | ✅ **KEEP** |
| **거래대금** | ❌ 미수집 | 거래량 × 가격 (계산 가능) | ⏸️ **계산으로 대체** |
| **누적거래량** | ❌ 미수집 | 일중 누적 (계산 가능) | ⏸️ **계산으로 대체** |
| **누적거래대금** | ❌ 미수집 | 일중 누적 (계산 가능) | ⏸️ **계산으로 대체** |
| **매수최우선호가가격** | ✅ 수집 중 (Orderbook) | 호가창 필수 | ✅ **KEEP** |
| **매도최우선호가가격** | ✅ 수집 중 (Orderbook) | 호가창 필수 | ✅ **KEEP** |
| **매수최우선호가잔량** | ✅ 수집 중 (Orderbook) | 호가창 필수 | ✅ **KEEP** |
| **매도최우선호가잔량** | ✅ 수집 중 (Orderbook) | 호가창 필수 | ✅ **KEEP** |

**결론**: **대상항목 A는 이미 80% 수집 중**. 누적 계열은 계산으로 대체 가능.

---

#### **대상항목 B: 고급 미시구조 지표**

| 항목 | Tier | 비즈니스 가치 | 권장 |
|------|------|---------------|------|
| 최우선매수매도호가중간값 | Tier 2 | Mid-price (공정가 추정) | ✅ **Phase 3 추가** |
| 전량가중평균지정가 | Tier 2 | VWAP 계산 검증용 | ⏸️ **보류** |
| IOC취소주문량 | Tier 3 | 취소율 분석 (HFT) | ❌ **Phase 5+** |
| FOK주문취소량 | Tier 3 | 취소율 분석 (HFT) | ❌ **Phase 5+** |
| 주문빈도기준취소율 | Tier 3 | Spoofing 탐지 | ❌ **Phase 5+** |
| 주문량기준취소율 | Tier 3 | Spoofing 탐지 | ❌ **Phase 5+** |
| 종목별거래횟수기준매수매도불균형 | Tier 3 | 주문 불균형 | ❌ **Phase 5+** |
| 종목별거래량기준매수매도불균형 | Tier 3 | 주문 불균형 | ❌ **Phase 5+** |
| 주문횟수기준주문불균형 | Tier 3 | 주문 불균형 | ❌ **Phase 5+** |
| 주문량기준주문불균형 | Tier 3 | 주문 불균형 | ❌ **Phase 5+** |
| 평균호가스프레드 | Tier 3 | 체결 비용 분석 | ❌ **Phase 5+** |
| 평균비율스프레드 | Tier 3 | 체결 비용 분석 | ❌ **Phase 5+** |
| 평균유효스프레드 | Tier 3 | 체결 비용 분석 | ❌ **Phase 5+** |
| 평균실현스프레드 | Tier 3 | 체결 비용 분석 | ❌ **Phase 5+** |
| HS역선택비용 | Tier 3 | 고급 연구용 | ❌ **Phase 5+** |
| 주문수량기준깊이 | Tier 2 | 유동성 분석 | ⏸️ **Phase 3 검토** |
| 주문건수기준깊이 | Tier 2 | 유동성 분석 | ⏸️ **Phase 3 검토** |

**결론**: **대상항목 B는 대부분 Tier 3** (HFT 전용). Mid-price만 Phase 3에서 고려.

---

### 9.2 필수 항목 (KRX 요구사항)

| 항목 | 현재 상태 | 비고 |
|------|-----------|------|
| **거래일자** | ✅ 수집 중 | `timestamp` 컬럼에 포함 |
| **시각** | ✅ 수집 중 | `timestamp` 컬럼 (밀리초 단위) |
| **시장ID** | ✅ 수집 중 | KR/US 구분 (`market` 컬럼) |
| **종목코드** | ✅ 수집 중 | `symbol` 컬럼 |
| **종목명** | ⏸️ 부분 수집 | Config YAML에만 있음 |
| **종가** | ✅ 수집 중 | 일봉 생성 시 저장 |

**결론**: **필수 항목 모두 충족**. 종목명은 `symbol_metadata` 테이블에 추가 예정.

---

### 9.3 최종 권고: 일중 시세 데이터 선택

#### ✅ **현재 유지 (Already Collecting)**
```yaml
대상항목_A:
  - 시가, 고가, 저가 (OHLC)
  - 거래량
  - 매수/매도 최우선호가 가격/잔량

필수항목:
  - 거래일자, 시각, 시장ID, 종목코드, 종가
```

**저장 위치**: `market_ticks` (TimescaleDB)

---

#### ➕ **Phase 3 추가 고려**
```yaml
대상항목_B_선택:
  - 최우선매수매도호가중간값 (Mid-price)
    → 용도: 공정가 추정, 슬리피지 계산
    → 계산식: (매수호가 + 매도호가) / 2
    → 저장 비용: 8 bytes/틱
```

**구현 방법**:
```python
# 실시간 계산 (저장 X)
mid_price = (best_bid + best_ask) / 2

# 필요 시에만 저장 (선택)
ALTER TABLE market_ticks ADD COLUMN mid_price FLOAT;
```

---

#### ❌ **Phase 5까지 보류**
```yaml
대상항목_B_제외:
  - IOC/FOK 취소주문량
  - 주문빈도/량 기준 취소율
  - 매수매도 불균형 (4종)
  - 스프레드 (4종)
  - HS 역선택비용
  - 주문 깊이 (2종)
```

**사유**:
1. **HFT 전용**: 밀리초 단위 의사결정 필요
2. **해석 복잡**: 도메인 전문 지식 필요
3. **저장 부담**: ~300KB/day × 365 = 110MB/year
4. **비용**: KRX 유료 데이터일 가능성

---

### 9.4 데이터 획득 방법

#### **Option 1: KIS WebSocket (현재 방식) ✅ 권장**
- **장점**: 실시간, 무료, 이미 구현됨
- **단점**: 대상항목 A만 제공 (B는 미제공 추정)
- **현재 TR_ID**:
  - KR Tick: `H0STCNT0`
  - KR Orderbook: `H0STASP0`
  - US Tick: `HDFSCNT0`

**결론**: **대상항목 A는 KIS WebSocket으로 충분**.

---

#### **Option 2: KRX 직접 구매 (대상항목 B)**
- **비용**: 확인 필요 (유료 추정)
- **용도**: Tier 3 데이터 (Phase 5+)
- **API**: KRX MDD (Market Data Dissemination)

**결론**: **Phase 5 도달 시 재검토**.

---

### 9.5 저장 전략

#### **Hot Data (실시간 조회)**
```sql
-- TimescaleDB: market_ticks
CREATE TABLE market_ticks (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    -- 대상항목 A (현재)
    best_bid DOUBLE PRECISION,
    best_ask DOUBLE PRECISION,
    bid_volume DOUBLE PRECISION,
    ask_volume DOUBLE PRECISION,
    -- Phase 3 추가 고려
    mid_price DOUBLE PRECISION,  -- 계산 가능하므로 선택적
    
    PRIMARY KEY (time, symbol)
);

SELECT create_hypertable('market_ticks', 'time');
```

**압축**: 7일 이후 자동 압축 (10:1 비율)

---

#### **Cold Data (분석 전용)**
```sql
-- DuckDB: market_microstructure (Phase 5+)
CREATE TABLE market_microstructure (
    date DATE,
    symbol VARCHAR(10),
    -- 대상항목 B
    ioc_cancel_volume BIGINT,
    order_imbalance DOUBLE PRECISION,
    avg_spread DOUBLE PRECISION,
    hs_adverse_selection DOUBLE PRECISION,
    ...
);
```

**압축**: Parquet 포맷 (압축률 50:1)

---

### 9.6 Council of Six - 일중 시세 의견

#### 👔 PM
**"현재 수집 중인 대상항목 A로 충분합니다. 추가 비용 없이 99% 사용자 니즈 충족."**

#### 📊 DS
**"Mid-price는 Phase 3 Tick Streaming 구현 시 추가. 나머지 대상항목 B는 불필요."**

#### 🖥️ Infra
**"대상항목 B 추가 시 TimescaleDB 압축률 저하 우려. DuckDB 분리 필수."**

#### 💻 Dev
**"Mid-price는 계산으로 충분. 저장 시 컬럼 1개 추가만 필요 (간단)."**

#### ✅ QA
**"대상항목 B는 검증 불가능. 추가 시 '베타' 태그 필수."**

#### 🏗️ Arch
**"Hot/Cold 분리 전략 유지. 대상항목 A는 TimescaleDB, B는 DuckDB."**

---

### 9.7 최종 결정

> [!IMPORTANT]
> **일중 시세 데이터 선택 결정**
>
> ✅ **대상항목 A**: 현재 수집 유지 (추가 작업 불필요)
>
> ➕ **Mid-price**: Phase 3에서 계산으로 추가 (저장은 선택)
>
> ❌ **대상항목 B (나머지)**: Phase 5까지 보류
>
> **근거**: 비용 대비 효과 분석 결과, 대상항목 A로 일반 투자자 니즈 99% 충족.

**다음 단계**: Phase 2B에서 Tier 1 종목 메타데이터 추가 (시가총액, 업종구분 등)

---

## 10. 과거 데이터 획득 전략 (Historical Data Backfill)

### 10.1 문제 정의

**현재 상황**:
- 실시간 데이터 수집: 2026-01-05 ~ 현재 (7일간)
- **과거 데이터 공백**: 2026-01-05 이전 데이터 없음

**필요성**:
- **백테스팅**: 전략 검증에 최소 1~2년 데이터 필요
- **트렌드 분석**: 장기 이동평균 (60일, 120일, 200일)
- **시즌성 분석**: 연간 패턴 파악
- **통계 모델링**: 충분한 샘플 사이즈 확보

---

### 10.2 과거 데이터 소스 비교

| 소스 | 데이터 범위 | 비용 | 품질 | 권장도 |
|------|-------------|------|------|--------|
| **KIS API** (무료) | 최대 30일 1분봉 | 무료 | ⭐⭐⭐⭐ 공식 | ✅ **1순위** |
| **yfinance** | 무제한 일봉 | 무료 | ⭐⭐⭐ 괜찮음 | ✅ **1순위** |
| **FinanceDataReader** | 무제한 일봉 | 무료 | ⭐⭐⭐⭐ KRX 공식 | ✅ **1순위** |
| **KRX 구매** | 맞춤형 | 💰 유료 | ⭐⭐⭐⭐⭐ 최고 | ⏸️ **3순위** |

---

### 10.3 Phase별 백필 전략

#### **Phase 2B: 무료 소스 최대 활용**

##### **Step 1: 일봉 백필 (2년치)**
```python
import FinanceDataReader as fdr
import yfinance as yf
from datetime import datetime, timedelta

# KRX 종목 리스트
symbols = ['005930', '000660', '035420', ...]  # ~22개

# 2년치 일봉 수집
for symbol in symbols:
    # Option 1: FinanceDataReader (KRX 공식)
    df = fdr.DataReader(symbol, start='2024-01-01')
    
    # Option 2: yfinance (글로벌)
    ticker = yf.Ticker(f"{symbol}.KS")
    df = ticker.history(period="2y")
    
    # TimescaleDB 저장
    await save_to_candles(df, symbol, interval='1d')
```

**예상 데이터량**:
- 22 종목 × 500 거래일 × 5 컬럼 (OHLCV) = **55,000 rows**
- 저장 공간: ~2MB (압축 전) → ~200KB (압축 후)

**소요 시간**: 1시간 (API 레이트 리밋)

---

##### **Step 2: 1분봉 백필 (30일치) - KIS API**
```python
# KIS REST API: FHKST03010200 (국내주식분봉조회)
async def fetch_minute_candles(symbol: str, days: int = 30):
    """KIS API로 1분봉 최대 30일 수집"""
    candles = []
    for day in range(days):
        date = (datetime.now() - timedelta(days=day)).strftime('%Y%m%d')
        response = await kis_api.get_minute_candles(symbol, date)
        candles.extend(response['output2'])
    
    return candles
```

**제약사항**:
- **KIS 제한**: 1분봉은 최대 30일까지만 제공
- **대안 없음**: 무료로 1분봉 과거 데이터 제공하는 곳 없음

**예상 데이터량**:
- 22 종목 × 30일 × 390분/일 = **257,400 rows**
- 저장 공간: ~10MB (압축 전) → ~1MB (압축 후)

---

#### **Phase 3+: KRX 구매 검토 (조건부)**

**구매 고려 시점**:
```yaml
조건:
  - 백테스팅 엔진 완성 (Phase 4)
  - 무료 데이터로 검증 완료
  - 상용 서비스 출시 계획
  - ROI 명확 (구매 비용 < 예상 수익)

목적:
  - 1분봉 1년+ 백필 (KIS는 30일만 제공)
  - 대상항목 B 미시구조 지표 (연구용)
  - 공식 인증 데이터 (법적 근거)
```

---

### 10.4 KRX 구매 시 우선순위

**구매한다면 이 순서로**:

#### **Tier 1: 백테스팅 필수 데이터**
| 항목 | 필요 기간 | 비용 추정 | 우선순위 |
|------|-----------|-----------|----------|
| **1분봉 OHLCV** | 2년 | 💰💰 | ⭐⭐⭐⭐⭐ **CRITICAL** |
| **일중 호가 스냅샷** | 1년 | 💰 | ⭐⭐⭐⭐ |

**사유**: 실시간 데이터는 충분하나, 백테스팅용 과거 데이터 부족

---

#### **Tier 2: 밸류에이션 & 메타데이터**
| 항목 | 필요 기간 | 무료 대안 | 우선순위 |
|------|-----------|-----------|----------|
| 시가총액, PER, 배당 | 5년 | ✅ yfinance | ⭐⭐ LOW |
| 재무제표 | 5년 | ✅ OpenDART | ⭐⭐ LOW |

**사유**: 무료 소스로 충분

---

#### **Tier 3: 미시구조 지표**
| 항목 | 필요 기간 | 비즈니스 가치 | 우선순위 |
|------|-----------|---------------|----------|
| 스프레드, 취소율 등 | 1년 | HFT 전용 | ⭐ VERY LOW |

**사유**: 일반 투자자에게 불필요

---

### 10.5 비용 편익 분석 (KRX 구매 시나리오)

#### **Scenario A: 1분봉 2년치만 구매**
```
비용 (추정):
  - 1분봉 OHLCV: ₩100만~500만 (추정, 확인 필요)
  - 22종목 × 2년

편익:
  - 백테스팅 정확도 ↑↑↑
  - 전략 신뢰도 ↑
  - 논문/연구 발표 가능

ROI:
  - Phase 4 도달 시 필수
  - 무료 데이터 검증 후 구매
```

---

#### **Scenario B: 미시구조 지표 포함**
```
비용 (추정):
  - 1분봉 + 대상항목 B: ₩500만~1,000만 (추정)

편익:
  - HFT 전략 개발 가능
  - 학술 연구용

 ROI:
  - Phase 5+ 또는 연구 프로젝트 전용
  - 일반 서비스에는 과도
```

---

### 10.6 Council of Six - 과거 데이터 의견

#### 👔 PM
**"Phase 2B에서 무료 소스로 2년치 일봉 백필. 1분봉은 KIS API 30일로 시작. KRX 구매는 Phase 4+ 또는 상용화 시점에 ROI 재계산."**

#### 📊 DS
**"백테스팅에는 일봉 2년이면 충분. 1분봉은 최근 30일만 있어도 초단타 전략 검증 가능. KRX 구매는 논문 쓸 때나 필요."**

#### 💻 Dev
**"무료 API 백필은 1일이면 구현 가능. KRX 구매 데이터 포맷 확인 후 파서 개발 필요 (추가 1주)."**

#### 🖥️ Infra
**"2년 일봉은 200KB, 30일 1분봉은 1MB. 둘 다 무시할 수 있는 수준. KRX 구매 시에도 스토리지는 문제없음."**

#### ✅ QA
**"무료 데이터로 먼저 검증. KRX 구매 데이터는 'Gold Standard'로 교차 검증용."**

#### 🏗️ Arch
**"과거 데이터는 DuckDB Parquet로 저장 (Cold Storage). 실시간은 TimescaleDB 유지."**

---

### 10.7 최종 권고: 과거 데이터 전략

> [!IMPORTANT]
> **과거 데이터 획득 전략**
>
> **Phase 2B (즉시)**:
> - ✅ 일봉 2년: `FinanceDataReader` 또는 `yfinance` (무료)
> - ✅ 1분봉 30일: KIS REST API (무료)
> - 예상 작업: 1~2일
>
> **Phase 4 (백테스팅 엔진 완성 후)**:
> - ⏸️ KRX 구매 검토: 1분봉 2년치 (비용 확인 후)
> - 조건: 무료 데이터 검증 완료 + ROI 명확
>
> **Phase 5+**:
> - ❌ 대상항목 B (미시구조): 연구 목적만
>
> **핵심**: 무료 소스 최대 활용 → 필요 시 점진적 KRX 구매

---

### 10.8 실행 계획

#### **Step 1: 무료 백필 POC (2일)**
```python
# scripts/backfill_historical.py
import asyncio
import FinanceDataReader as fdr

async def backfill_daily_candles():
    """2년치 일봉 백필"""
    symbols = load_symbols()  # configs/kr_symbols.yaml
    
    for symbol in symbols:
        logger.info(f"Backfilling {symbol}...")
        
        # 1. FinanceDataReader로 다운로드
        df = fdr.DataReader(symbol, start='2024-01-01')
        
        # 2. TimescaleDB 저장
        await db.executemany("""
            INSERT INTO market_candles (time, symbol, open, high, low, close, volume, interval)
            VALUES ($1, $2, $3, $4, $5, $6, $7, '1d')
            ON CONFLICT DO NOTHING
        """, df.itertuples())
        
        logger.info(f"{symbol}: {len(df)} candles saved")

if __name__ == "__main__":
    asyncio.run(backfill_daily_candles())
```

**실행**:
```bash
# 백필 스크립트 실행
python scripts/backfill_historical.py

# 검증
psql -h localhost -U postgres -d stockval -c \
  "SELECT symbol, COUNT(*), MIN(time), MAX(time) FROM market_candles WHERE interval='1d' GROUP BY symbol;"
```

---

#### **Step 2: KRX 비용 조사 (1일)**
```
TODO:
1. KRX 홈페이지 방문 (data.krx.co.kr)
2. 시장정보 > 데이터판매 메뉴 확인
3. 1분봉 OHLCV 2년치 견적 요청
4. 대상항목 A/B 가격 비교
5. ROI 계산 후 PM에게 보고
```

---

#### **Step 3: 백테스팅 검증 (Phase 4)**
```python
# Phase 4에서 실행
# 1. 무료 데이터로 백테스트
result_free = backtest(strategy, data_source='yfinance')

# 2. KRX 구매 데이터로 재검증 (구매 시)
result_krx = backtest(strategy, data_source='krx')

# 3. 차이 분석
if abs(result_free.sharpe - result_krx.sharpe) > 0.1:
    logger.warning("Data source divergence detected!")
```

---

**결론**: **과거 데이터는 무료 소스 우선, KRX 구매는 Phase 4+ ROI 검증 후 결정**

---

**📌 이 문서는 데이터 획득 결정 시 참조하는 Source of Truth입니다.**
