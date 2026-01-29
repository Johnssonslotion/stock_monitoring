# RFC-010: Market Intelligence & Rotation Analysis (Pillar 8)

**Status**: Draft
**Created**: 2026-01-29
**Author**: AI Architect
**Pillar**: 8
**Priority**: P1

---

## 1. Summary

Pillar 8은 **투자자별 수급, 공매도 현황, 프로그램 매매 데이터**를 수집하고 분석하여 **업종 간 순환매(Sector Rotation)**를 포착하는 시스템을 구축합니다.

---

## 2. Motivation

### 2.1 문제점

현재 시스템은 **가격 데이터(틱, 분봉)** 수집에 집중되어 있으며, 시장 참여자의 행동 패턴을 파악할 수 없습니다:

- 외국인/기관의 매수·매도 동향 파악 불가
- 공매도 과열 종목 사전 감지 불가
- 프로그램 매매(차익/비차익) 추적 불가
- 섹터 간 자금 이동(순환매) 탐지 불가

### 2.2 목표

1. **투자자 수급 데이터 수집**: 외국인, 기관, 개인별 순매수 현황
2. **공매도 모니터링**: 잔고, 일별 거래량, 과열 종목 플래깅
3. **프로그램 매매 추적**: 차익/비차익 거래 현황
4. **순환매 탐지**: 섹터별 자금 유입도 분석 및 알림

---

## 3. KIS API TR ID Mapping (Ground Truth)

### 3.1 투자자별 매매동향

| TR ID | 명칭 | URL Path | 용도 |
|-------|------|----------|------|
| `FHPTJ04400000` | 국내기관_외국인 매매종목가집계 | `/uapi/domestic-stock/v1/quotations/inquire-investor` | 투자자별 순매수 집계 |
| `FHKST01010900` | 종목별 외국계 순매수추이 | `/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice` | 외국인 순매수 추이 |
| `FHPTJ04400100` | 투자자별 매매동향(종합) | `/uapi/domestic-stock/v1/quotations/inquire-investor-trend` | 시장 전체 투자자 동향 |

### 3.2 공매도 현황

| TR ID | 명칭 | URL Path | 용도 |
|-------|------|----------|------|
| `FHPTJ04500000` | 국내주식 공매도 일별추이 | `/uapi/domestic-stock/v1/quotations/inquire-daily-shortselling` | 일별 공매도 거래량 |
| `FHPTJ04500100` | 공매도 종합 정보 | `/uapi/domestic-stock/v1/quotations/inquire-shortselling-balance` | 공매도 잔고 현황 |

### 3.3 프로그램 매매

| TR ID | 명칭 | URL Path | 용도 |
|-------|------|----------|------|
| `FHPTJ04300000` | 종목별 프로그램매매추이 | `/uapi/domestic-stock/v1/quotations/inquire-program-trade` | 차익/비차익 매매 현황 |
| `FHPTJ04300100` | 프로그램매매 종합현황 | `/uapi/domestic-stock/v1/quotations/inquire-program-trade-summary` | 시장 전체 프로그램 매매 |

> **Note**: 위 TR ID는 KIS Developers 포털 기준 추정치이며, 실제 구현 시 Schema Discovery를 통해 검증 필요.

---

## 4. Database Schema Extension

### 4.1 투자자별 매매동향 테이블

```sql
-- 투자자별 순매수 (일별)
CREATE TABLE IF NOT EXISTS investor_trends (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    foreign_buy BIGINT,          -- 외국인 매수량
    foreign_sell BIGINT,         -- 외국인 매도량
    foreign_net BIGINT,          -- 외국인 순매수
    institution_buy BIGINT,      -- 기관 매수량
    institution_sell BIGINT,     -- 기관 매도량
    institution_net BIGINT,      -- 기관 순매수
    retail_buy BIGINT,           -- 개인 매수량
    retail_sell BIGINT,          -- 개인 매도량
    retail_net BIGINT,           -- 개인 순매수
    source TEXT DEFAULT 'KIS',
    CONSTRAINT pk_investor_trends PRIMARY KEY (time, symbol)
);

SELECT create_hypertable('investor_trends', 'time', if_not_exists => TRUE);

-- 인덱스
CREATE INDEX idx_investor_trends_symbol_time
ON investor_trends (symbol, time DESC);
```

### 4.2 공매도 현황 테이블

```sql
-- 공매도 일별 현황
CREATE TABLE IF NOT EXISTS short_selling (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    short_volume BIGINT,         -- 공매도 거래량
    short_amount BIGINT,         -- 공매도 거래대금
    short_ratio DECIMAL(5,2),    -- 공매도 비율 (%)
    balance_volume BIGINT,       -- 공매도 잔고
    balance_ratio DECIMAL(5,2),  -- 잔고 비율 (%)
    source TEXT DEFAULT 'KIS',
    CONSTRAINT pk_short_selling PRIMARY KEY (time, symbol)
);

SELECT create_hypertable('short_selling', 'time', if_not_exists => TRUE);

-- 과열 종목 플래그
CREATE INDEX idx_short_selling_ratio
ON short_selling (short_ratio DESC)
WHERE short_ratio > 20;
```

### 4.3 프로그램 매매 테이블

```sql
-- 프로그램 매매 현황
CREATE TABLE IF NOT EXISTS program_trading (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    arb_buy BIGINT,              -- 차익 매수
    arb_sell BIGINT,             -- 차익 매도
    arb_net BIGINT,              -- 차익 순매수
    non_arb_buy BIGINT,          -- 비차익 매수
    non_arb_sell BIGINT,         -- 비차익 매도
    non_arb_net BIGINT,          -- 비차익 순매수
    total_net BIGINT,            -- 전체 순매수
    source TEXT DEFAULT 'KIS',
    CONSTRAINT pk_program_trading PRIMARY KEY (time, symbol)
);

SELECT create_hypertable('program_trading', 'time', if_not_exists => TRUE);
```

### 4.4 섹터 순환매 분석 테이블

```sql
-- 섹터별 자금 유입도 (일별 집계)
CREATE TABLE IF NOT EXISTS sector_rotation (
    time TIMESTAMPTZ NOT NULL,
    sector_code TEXT NOT NULL,
    sector_name TEXT,
    money_flow_index DECIMAL(8,2),  -- 자금 유입도 지수
    foreign_flow BIGINT,            -- 외국인 순매수 합계
    institution_flow BIGINT,        -- 기관 순매수 합계
    volume_change_pct DECIMAL(5,2), -- 거래량 증감률
    rotation_signal TEXT,           -- INFLOW / OUTFLOW / NEUTRAL
    CONSTRAINT pk_sector_rotation PRIMARY KEY (time, sector_code)
);

SELECT create_hypertable('sector_rotation', 'time', if_not_exists => TRUE);
```

---

## 5. Architecture Design

### 5.1 시스템 구성도

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Pillar 8 Architecture                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐       │
│  │ KIS REST API  │    │ Kiwoom API    │    │ External Data │       │
│  │ (TR ID 기반)   │    │ (Optional)    │    │ (KRX, etc.)   │       │
│  └───────┬───────┘    └───────┬───────┘    └───────┬───────┘       │
│          │                    │                    │               │
│          ▼                    ▼                    ▼               │
│  ┌───────────────────────────────────────────────────────┐         │
│  │              Market Intelligence Collector             │         │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │         │
│  │  │ Investor    │ │ ShortSell   │ │ Program     │      │         │
│  │  │ Collector   │ │ Collector   │ │ Collector   │      │         │
│  │  └─────────────┘ └─────────────┘ └─────────────┘      │         │
│  └───────────────────────┬───────────────────────────────┘         │
│                          │                                         │
│                          ▼                                         │
│  ┌───────────────────────────────────────────────────────┐         │
│  │                   API Hub v2 Worker                    │         │
│  │           (Token Management, Rate Limiting)            │         │
│  └───────────────────────┬───────────────────────────────┘         │
│                          │                                         │
│                          ▼                                         │
│  ┌───────────────────────────────────────────────────────┐         │
│  │                    TimescaleDB                         │         │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │         │
│  │  │investor_trends│ │short_selling│ │program_trading│   │         │
│  │  └──────────────┘ └──────────────┘ └──────────────┘   │         │
│  │  ┌──────────────┐                                     │         │
│  │  │sector_rotation│ (Daily Aggregation)                │         │
│  │  └──────────────┘                                     │         │
│  └───────────────────────┬───────────────────────────────┘         │
│                          │                                         │
│                          ▼                                         │
│  ┌───────────────────────────────────────────────────────┐         │
│  │               Rotation Analysis Engine                 │         │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │         │
│  │  │ Money Flow  │ │ Sector      │ │ Alert       │      │         │
│  │  │ Calculator  │ │ Ranker      │ │ Generator   │      │         │
│  │  └─────────────┘ └─────────────┘ └─────────────┘      │         │
│  └───────────────────────┬───────────────────────────────┘         │
│                          │                                         │
│                          ▼                                         │
│  ┌───────────────────────────────────────────────────────┐         │
│  │                  Visualization Layer                   │         │
│  │  - 섹터 맵 수급 강도 오버레이                            │         │
│  │  - 공매도 과열 종목 대시보드                              │         │
│  │  - 순환매 시그널 알림                                    │         │
│  └───────────────────────────────────────────────────────┘         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 API Hub v2 Queue 통합

현재 시스템은 **API Hub v2 Worker**가 Redis Queue를 통해 모든 REST API 호출을 중앙 관리합니다.
Pillar 8 Collector들도 동일한 패턴을 따릅니다:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Intelligence    │     │  Redis Queue    │     │  API Hub v2     │
│ Collector       │────▶│  (Gatekeeper)   │────▶│  Worker         │
│ (요청 제출)      │     │  Rate Limiting  │     │  (실제 호출)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │  KIS REST API   │
                                                │  (20 req/s)     │
                                                └─────────────────┘
```

### 5.3 Collector 클래스 설계

```python
# src/data_ingestion/intelligence/base_intelligence_collector.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseIntelligenceCollector(ABC):
    """시장 인텔리전스 데이터 수집기 기본 클래스

    API Hub v2 Queue를 통해 Rate Limit 준수하며 데이터 수집
    """

    def __init__(self, redis_client, table_name: str, tr_id: str):
        self.redis = redis_client
        self.table_name = table_name
        self.tr_id = tr_id
        self.queue_name = "api_hub:request_queue"

    @abstractmethod
    def build_request(self, symbol: str, date: str) -> Dict[str, Any]:
        """API Hub Queue에 제출할 요청 생성"""
        pass

    @abstractmethod
    def transform(self, raw_data: Dict) -> List[Dict]:
        """응답 데이터를 DB 스키마로 변환"""
        pass

    async def submit_to_queue(self, symbol: str, date: str) -> str:
        """API Hub Queue에 요청 제출 (비동기)"""
        request = self.build_request(symbol, date)
        request_id = await self.redis.lpush(self.queue_name, json.dumps(request))
        return request_id

    async def collect_batch(self, symbols: List[str], date: str):
        """배치 수집 - Queue에 요청 제출 후 결과 대기"""
        for symbol in symbols:
            await self.submit_to_queue(symbol, date)
        # Worker가 처리한 결과는 별도 Consumer에서 수신
```

---

## 6. Implementation Phases

### Phase 1: Data Expansion (4-6 weeks)

**ISSUE 분리 계획**:

| ISSUE ID | 제목 | 우선순위 | 의존성 |
|----------|------|----------|--------|
| ISSUE-049 | KIS TR ID Discovery & Validation | P0 | - |
| ISSUE-050 | Investor Trends Collector | P1 | ISSUE-049 |
| ISSUE-051 | Short Selling Collector | P1 | ISSUE-049 |
| ISSUE-052 | Program Trading Collector | P1 | ISSUE-049 |
| ISSUE-053 | DB Migration (Pillar 8 Tables) | P0 | - |

### Phase 2: Rotation Engine (3-4 weeks)

| ISSUE ID | 제목 | 우선순위 | 의존성 |
|----------|------|----------|--------|
| ISSUE-054 | Money Flow Index Calculator | P1 | Phase 1 |
| ISSUE-055 | Sector Rotation Detector | P1 | ISSUE-054 |
| ISSUE-056 | Foreign/Institution Focus Alert | P2 | ISSUE-050 |

### Phase 3: Visualization (2-3 weeks)

| ISSUE ID | 제목 | 우선순위 | 의존성 |
|----------|------|----------|--------|
| ISSUE-057 | Sector Map Supply Overlay | P2 | Phase 2 |
| ISSUE-058 | Short Selling Dashboard | P2 | ISSUE-051 |
| ISSUE-059 | Rotation Signal Notification | P3 | ISSUE-055 |

---

## 7. Success Criteria

### 7.1 Phase 1 완료 조건

- [ ] 3개 이상 TR ID 실제 API 응답 스키마 확보
- [ ] 4개 신규 테이블 TimescaleDB 생성 완료
- [ ] 최소 50개 종목 투자자 동향 데이터 일일 수집
- [ ] Unit Test 커버리지 80% 이상

### 7.2 Phase 2 완료 조건

- [ ] Money Flow Index 계산 로직 구현 및 검증
- [ ] 섹터별 순환매 시그널 생성 (정확도 > 70%)
- [ ] 외국인/기관 집중 매수 알림 정상 동작

### 7.3 Phase 3 완료 조건

- [ ] 섹터 맵에 수급 강도 시각화 오버레이
- [ ] 공매도 과열 대시보드 E2E 테스트 통과
- [ ] Slack/Discord 알림 연동 완료

---

## 8. Risks & Mitigations

| 리스크 | 영향 | 완화 방안 |
|--------|------|----------|
| TR ID 추정 오류 | Phase 1 지연 | Schema Discovery 선행 작업 필수 |
| API Rate Limit | 데이터 수집 실패 | **기존 API Hub v2 Queue 활용** (이미 구현됨) |
| 데이터 지연 | 실시간성 저하 | 장중 1분 주기 수집 (비실시간 TR) |
| DB 용량 증가 | 스토리지 비용 | Retention Policy 30일 적용 |

> **Note**: 현재 시스템은 **API Hub v2 Queue**를 통해 전체 API 호출 제한을 중앙 관리하고 있습니다.
> Pillar 8 Collector들도 동일한 Queue에 요청을 제출하여 Rate Limit을 준수합니다.

---

## 9. Related Documents

- **Pillar 8 Roadmap**: `docs/strategy/master_roadmap.md#pillar-8`
- **KIS TR ID Reference**: `docs/specs/api_reference/kis_tr_id_reference.md`
- **Database Specification**: `docs/specs/database_specification.md`
- **API Hub v2 Overview**: `docs/specs/api_hub_v2_overview.md`

---

## 10. Approval

| Role | Name | Decision | Date |
|------|------|----------|------|
| Architect | AI | Proposed | 2026-01-29 |
| PM | - | Pending | - |
| QA | - | Pending | - |
| Developer | - | Pending | - |

---

**Next Steps**:
1. RFC 승인
2. ISSUE-049~053 (Phase 1) 생성
3. KIS API Schema Discovery 실행
4. DB 마이그레이션 스크립트 작성
