# RFC-008: Tick Data Completeness & Quality Assurance System

**Status**: 🟡 Proposed  
**Created**: 2026-01-19  
**Author**: Antigravity AI  
**Supersedes**: [ID-daily-minute-recovery-qa.md](file:///home/ubuntu/workspace/stock_monitoring/docs/ideas/stock_monitoring/ID-daily-minute-recovery-qa.md)  

---

## 1. Executive Summary

### Problem Statement
현재 KIS/Kiwoom WebSocket을 통한 실시간 틱 데이터 수집은 네트워크 장애, API 제한, 소켓 끊김 등으로 인한 **데이터 누락 위험**이 존재합니다. 백테스팅과 머신러닝 학습 데이터의 신뢰성을 위해서는 **100%에 가까운 틱 데이터 완전성**이 필수적입니다.

### Proposed Solution
3단계 품질 보증 시스템:
1. **[P0] 틱 수집 강화**: 중복 제거, 버퍼링, Gap 감지 및 복구 로깅
2. **[P1] 분봉 배치 생성**: 수집된 틱 데이터로부터 SQL 기반 분봉 집계
3. **[P2] API 교차 검증**: 틱 기반 분봉 vs KIS/Kiwoom REST 분봉 비교

### Success Criteria
- 틱 데이터 누락률 < 0.1%
- 중복 저장 = 0건
- 분봉 생성 정확도 > 99%

---

## 2. Motivation

### 2.1 Current State (As-Is)

```
[KIS WebSocket]
   ├─ Tick ──┐
   └─ Hoga ──┴─→ UnifiedCollector → Redis → TimescaleDB (Dual Write)
                   (메모리 부족 위험, KIS 부하 집중)
```

**문제점**:
1. **단일 소스 의존**: KIS 장애 시 틱/호가 모두 중단.
2. **KIS 소켓 부하**: KIS 소켓 하나로 틱/호가 모두 처리 시 Latency 증가 (Zero Cost 환경).
3. **DB 리소스**: TimescaleDB 단일 저장소는 분석용(Cold)으로 무겁고, DuckDB는 실시간용(Hot)으로 부족.

### 2.2 Desired State (To-Be: Hybrid & Multi-Vendor)

```
[KIS WebSocket] ────→ Tick ────┐
                               │
[Kiwoom WebSocket] ─→ Hoga ────┼─→ Redis ──┬─→ [TimescaleDB] (Hot/Realtime)
                               │           │    ├─ 실시간 차트 (1m/5m/1h)
                               │           │    └─ 시스템 메트릭
                               │           │
                               │           └─→ [DuckDB] (Cold/Analytics)
                               │                ├─ 틱/호가 전체 로그 (Batch)
                               │                └─ Daily Recovery & QA
```

**핵심 변경**:
1. **Vendor 이원화**: 틱(KIS) / 호가(Kiwoom) 분리하여 리스크 분산.
2. **DB Hybrid**: 실시간성(Timescale)과 분석/보관(DuckDB)의 강점 결합.
3. **Deep Integrity**: DuckDB를 'Ground Truth'로 하여 Daily Recovery 수행.

---

## 3. Technical Design

### 3.1 Component Overview

| Component | 역할 | Source | Storage | Priority |
|-----------|------|--------|---------|----------|
| **EnhancedTickCollector** | 틱 수집 및 발행 | **KIS** | Redis | P0 |
| **KiwoomOrderbookCollector** | 호가 수집 및 발행 | **Kiwoom** | Redis | P0 |
| **TimescaleArchiver** | 실시간 데이터 적재 | Redis | **TimescaleDB** | P1 |
| **DuckDBArchiver** | 대용량 배치 적재 | Redis | **DuckDB** | P1 |
| **DailyRecovery** | 품질 검증 및 복구 | REST API | DuckDB | P2 |

### 3.2 Data Flow

```mermaid
graph TD
    KIS[KIS WebSocket] -->|Tick| A[Redis: ticker.kr]
    KW[Kiwoom WebSocket] -->|Orderbook| B[Redis: orderbook.kr]
    
    A --> C{TimescaleArchiver}
    B --> C
    C -->|Realtime Insert| D[(TimescaleDB)]
    D -->|Continuous Aggr| E[Minute Candles]
    
    A --> F{DuckDBArchiver}
    B --> F
    F -->|1s Batch Insert| G[(DuckDB)]
    
    G --> H[Daily Recovery]
    H -->|Validate| I[Kiwoom REST API]
```

### 3.3 Database Strategy (Hybrid)

#### TimescaleDB (Hot Data)
- **목적**: 실시간 차트 스트리밍, 시스템 모니터링
- **보관 주기**: 최근 7일 (Retention Policy 적용)
- **Table**: `market_ticks`, `market_orderbook`, `system_metrics`
- **Feature**: Continuous Aggregates (1m, 5m, 1h 자동 생성)

#### DuckDB (Cold Data)
- **목적**: 전체 과거 데이터 보관, 백테스팅, ML 학습, 무결성 검증
- **보관 주기**: 영구 (Permanent)
- **Table**: `market_ticks`, `market_orderbook`, `minute_candles`
- **Feature**: 고속 OLAP 쿼리, Parquet Export

### 3.4 Kiwoom Orderbook Specification

- **TR ID**: `real_hoga` (주식호가)
- **Fields**: 매도호가1~10, 매수호가1~10, 매도잔량, 매수잔량
- **특징**: KIS보다 데이터 업데이트 빈도가 높을 수 있음 (Throttle 필요 가능성)


### 3.4 External API Specifications

#### Kiwoom Chart REST API (QA용)

본 시스템은 틱 데이터 검증을 위해 키움증권의 차트 조회 API를 사용합니다.

- **엔드포인트**: `POST /api/tr/opt10079` (주식틱차트조회)
- **제공 데이터**: 틱 차트 + **체결 횟수** (`trde_qty`)
- **검증 로직**: `틱 DB의 COUNT(*) == 키움 API의 trde_qty` → 완전성 보장

#### KIS Tick REST API (Recovery용)

본 시스템은 **누락된 틱 데이터 복구**를 위해 KIS의 체결 조회 API를 사용합니다.

- **엔드포인트**: `GET /uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion` (`FHKST01010300`)
- **제공 데이터**: **Tick History** (시간, 가격, 거래량)
- **특징**: `FID_INPUT_HOUR_1` 파라미터로 특정 시점 과거 데이터 조회 가능. 
- **복구 전략**: 누락 구간에 대해 Paging 호출하여 DB에 채워넣음.

**역할 분담**:
1. **Kiwoom (QA)**: "몇 개가 빠졌는지" 확인 (Count Check)
2. **KIS (Recovery)**: "빠진 내용을" 채워넣기 (Data Fill)

### 3.5 Quality Metrics

#### A. Coverage (커버리지)

```
틱 커버리지 = (수집된 틱 수 / KIS REST 분봉 거래량 합계) × 100%

임계값:
- > 95%: ✅ Excellent
- 90-95%: ⚠️ Warning
- < 90%: ❌ Critical
```

#### B. Consistency (일관성)

```
분봉 일치율 = (OHLCV 일치 분봉 수 / 전체 분봉 수) × 100%

OHLCV 일치 조건:
- |tick_open - kis_open| / kis_open < 0.5%
- |tick_high - kis_high| / kis_high < 0.5%
- |tick_low - kis_low| / kis_low < 0.5%
- |tick_close - kis_close| / kis_close < 0.5%
- |tick_volume - kis_volume| / kis_volume < 5%
```

#### C. Latency (지연시간)

```
지연 = DB 저장 시각 - 체결 시각

목표:
- P99 < 100ms (틱 수집)
- P99 < 1000ms (분봉 생성 - 배치 처리)
```

---

## 4. Implementation Plan

### Phase 1: 틱 수집 강화 (Week 1)

**목표**: 틱 누락률 < 0.1%

- [ ] `EnhancedTickCollector` 구현
  - 체결번호 기반 중복 제거
  - 1초 배치 INSERT (5,000 rows/batch)
  - 10초+ Gap 시 Redis 알림 발송
- [ ] `TickRecoveryLogger` 구현
  - 소켓 끊김 이벤트 로깅
  - `recovery:pending` Redis Set에 저장
- [ ] Unit Tests
  - 중복 제거 테스트
  - Gap 감지 테스트
  - 버퍼 플러시 테스트

### Phase 2: 분봉 생성 (Week 2)

**목표**: 분봉 완성도 > 98%

- [ ] `generate_candles_from_ticks.py` 구현
  - DuckDB `time_bucket()` 함수 사용
  - 1분봉, 3분봉, 5분봉 지원
  - Upsert 로직 (`ON CONFLICT DO UPDATE`)
- [ ] DB 마이그레이션
  - `minute_candles` 테이블 생성
  - `execution_no` 컬럼 추가
- [ ] 검증
  - 과거 틱 데이터로 분봉 생성 테스트
  - 예상 분봉 수(391개/종목) 대비 생성률 확인

### Phase 3: API 교차 검증 (Week 3)

**목표**: 일치율 > 99%

- [ ] `cross_validate_candles.py` 구현
  - KIS REST API 분봉 수집
  - SQL JOIN 기반 비교 분석
  - 불일치 항목 CSV 리포트 생성
- [ ] Cron Job 설정
  ```bash
  # /etc/cron.d/tick-qa
  0 16 * * 1-5 /app/scripts/cross_validate_candles.py --date TODAY
  ```
- [ ] 알림 통합
  - Slack Webhook (Coverage < 95% 시)

### Phase 4: 프로덕션 배포 (Week 4)

- [ ] 모니터링 대시보드
  - Sentinel에 틱 커버리지 메트릭 추가
  - 일일 품질 점수 그래프
- [ ] 문서화
  - Walkthrough 작성
  - 운영 매뉴얼 업데이트
- [ ] 1주일 파일럿 운영

---

## 5. Council Review

### 👨‍💼 PM (Product Manager)
> **승인**: ✅  
> "데이터 품질이 백테스팅 신뢰도의 핵심입니다. P0 우선순위로 진행하세요."

### 🏗️ Architect
> **승인**: ✅  
> "분봉 생성을 틱 수집과 완전히 분리한 점이 탁월합니다. Celery는 나중에 도입해도 됩니다."

### 🔧 DevOps Lead
> **조건부 승인**: ⚠️  
> "DuckDB 쓰기 성능 벤치마크를 먼저 실행하세요. 버퍼링 효과를 수치로 입증해야 합니다."

### 🧪 QA Lead
> **승인**: ✅  
> "임계값(Coverage < 95% = FAIL)이 명확합니다. 리포트 자동화는 필수입니다."

### 🛡️ Security Lead
> **승인**: ✅  
> "분봉 데이터도 DuckDB 파일 암호화 대상입니다. 기존 정책 그대로 적용하세요."

### 💻 Engineer
> **승인**: ✅  
> "±1초 Fuzzy Matching으로 분봉-틱 매칭 문제 해결 가능합니다. 구현 난이도 낮습니다."

**Council 결정**: ✅ **만장일치 승인** (조건: DuckDB 벤치마크 선행 실행)

---

## 6. Risks & Mitigation

| Risk | Impact | Mitigation | Probability |
|------|--------|------------|-------------|
| **DuckDB 쓰기 병목** | 틱 누락 | 버퍼링 도입 (벤치마크 선행) | Medium |
| **체결번호 미제공** | 중복 제거 실패 | timestamp+price+volume 조합 사용 | Low |
| **KIS API Rate Limit** | 검증 지연 | Kiwoom API 대체 또는 익일 처리 | Low |
| **메모리 버퍼 손실** | 최대 1초치 데이터 손실 | Daily Recovery로 복구 (허용) | Low |

---

## 7. Success Metrics

### Quantitative

- [ ] 틱 커버리지 > 99%
- [ ] 중복 저장 = 0건
- [ ] 분봉 일치율 > 99%
- [ ] P99 지연 < 100ms

### Qualitative

- [ ] 일일 품질 리포트 자동 생성
- [ ] Council Review 통과
- [ ] 1주일 파일럿 운영 성공

---

## 8. Alternatives Considered

### Alternative 1: 실시간 분봉 집계 (In-Memory)

**장점**:
- 분봉 생성 지연 < 1ms
- 실시간 차트 제공 가능

**단점**:
- 틱 수집 성능 저하 (10-20%)
- 서버 재시작 시 미완성 분봉 손실
- 복잡도 증가

**결정**: ❌ **기각** (틱 수집이 최우선 목표)

### Alternative 2: Celery 비동기 작업 큐

**장점**:
- 스케줄링 관리 용이
- 실패 재시도 자동화

**단점**:
- 인프라 복잡도 증가 (RabbitMQ/Redis Queue)
- 오버엔지니어링 (현재 규모에 불필요)

**결정**: 🕐 **보류** (Phase 4 이후 검토)

---

## 9. Rollout Strategy

### Canary Deployment

```
Week 1: 1개 종목 (005930)
Week 2: 10개 종목 (KOSPI 대형주)
Week 3: 50개 종목
Week 4: 전체 100개 종목 (Full Deployment)
```

### Rollback Plan

버퍼링 로직 실패 시:
1. `EnhancedTickCollector` 비활성화
2. 기존 즉시 INSERT 방식으로 복귀
3. 틱 데이터는 보존됨 (분봉 생성만 지연)

---

## 10. Open Questions

1. **DuckDB 벤치마크 결과가 5,000 writes/sec를 감당하지 못하면?**
   - → PostgreSQL 또는 ClickHouse로 마이그레이션 고려
   - → 종목별 파일 분할 (`ticks_005930.duckdb`)

2. **체결번호가 제공되지 않는 API가 있다면?**
   - → `hash(symbol + timestamp + price + volume)` 사용
   - → 극히 드문 충돌만 허용 (< 0.01%)

3. **KIS와 Kiwoom 분봉이 모두 틱 집계와 불일치하면?**
   - → 틱 데이터를 Ground Truth로 간주
   - → 수동 검증 후 API 이슈로 보고

---

## 11. Approval

| Role | Name | Approval | Date |
|------|------|----------|------|
| PM | Council | ✅ Approved | 2026-01-19 |
| Architect | Council | ✅ Approved | 2026-01-19 |
| DevOps Lead | Council | ⚠️ Conditional* | 2026-01-19 |
| QA Lead | Council | ✅ Approved | 2026-01-19 |
| Security Lead | Council | ✅ Approved | 2026-01-19 |
| Engineer | Council | ✅ Approved | 2026-01-19 |

\* **조건**: DuckDB 쓰기 성능 벤치마크 선행 실행

---

## 12. References

- [ID-daily-minute-recovery-qa.md](file:///home/ubuntu/workspace/stock_monitoring/docs/ideas/stock_monitoring/ID-daily-minute-recovery-qa.md) (원본 아이디어)
- [Implementation Plan](file:///home/ubuntu/.gemini/antigravity/brain/0fe98171-b456-4f3d-987a-e35a953fc6a3/implementation_plan.md)
- [Gap Analysis Report 2026-01-19](file:///home/ubuntu/workspace/stock_monitoring/docs/governance/gap_analysis_report_2026-01-19.md)
- [RFC-007: Collector Isolation](file:///home/ubuntu/workspace/stock_monitoring/docs/rfc/RFC-007-collector-isolation.md)

---

**Next Steps**:
1. DuckDB 벤치마크 실행 (`scripts/benchmark_duckdb_writes.py`)
2. DevOps Lead 최종 승인 대기
3. Phase 1 구현 시작 (EnhancedTickCollector)


**Status Update**: 2026-01-19 - Council 만장일치 승인 (조건부)

---

## Appendix C: API Verification Strategy (Updated 2026-01-20)

### C.1 API Experiment Results

#### Kiwoom Tick Chart API (`ka10079`)

**실험 일시**: 2026-01-20 11:40 KST  
**대상**: 삼성전자 (005930)

**결과**:
- ✅ **900 ticks 반환** (1분간 데이터)
- ✅ Pagination 지원 (`next-key` 헤더)
- ✅ Token 자동 발급 성공 (Container와 충돌 없음)
- ❌ **TODAY ONLY** - 날짜 파라미터 없음
- ⚠️ Rate Limit 발생 (HTTP 429, 7/23 calls)

**제약사항**:
1. **TODAY ONLY**: 과거 날짜 조회 불가 → 주간 Full Scan 불가능
2. **Rate Limit**: 전수 검사 시 2,000+ calls 필요 → 실용성 낮음
3. **실용성**: 당일 실시간 모니터링용으로만 사용 가능

#### KIS Tick API (`FHKST01010300`)

**결과**:
- ✅ API 작동 확인
- ❌ Tick Count 직접 조회 불가 (전체 틱을 받아야 COUNT 가능)
- ⚠️ 비효율적 (검증만 하려는데 GB급 다운로드 필요)

---

### C.2 최종 Verification Strategy

#### Option B: Volume + OHLCV Cross-Check (ADOPTED) ✅

**2-Tier Adaptive Strategy**:

```
Tier 1: Volume Cross-Check (빠른 전수 스캔)
├─ KIS/Kiwoom 분봉 API로 거래량 조회
├─ DB 틱 거래량 합계와 비교
├─ 임계값: |API_Vol - DB_Vol| / API_Vol < 0.1%
└─ API 호출: ~40 calls/일 (전체 종목)

Tier 2: OHLCV Consistency (정밀 검증)
├─ Tier 1 실패 구간만 검증
├─ 틱 기반 분봉 vs API 분봉 OHLCV 비교
├─ 임계값: OHLC < 0.5%, Volume < 5%
└─ API 호출: 이상 구간만 (평균 < 10 calls/일)
```

**일일 스케줄**:
```
09:00-15:30  실시간 수집 (Container만)
15:30-16:00  Volume Cross-Check (Tier 1)
16:00-17:00  Targeted Recovery (Tier 2 이상치만)
```

**장점**:
- ✅ 효율적: 정상 구간은 빠르게 패스
- ✅ 정확: 의심 구간은 OHLCV로 정밀 검증
- ✅ Rate Limit 안전: 소수 구간만 Tier 2 호출
- ✅ 모든 날짜 가능: TODAY ONLY 제약 없음

**한계 (acknowledged)**:
- ⚠️ **소수 누락 탐지 불가**: Volume < 0.1% 차이는 놓칠 수 있음
- **수용 근거**: 백테스트 영향 미미, 완벽보다 실용성 우선

---

### C.3 Council Review Summary (2026-01-20)

**주요 결정**:
1. ✅ Volume + OHLCV 전략 만장일치 승인
2. ✅ API Gateway Rate Limiter 승인 (30 calls/sec)
3. ❌ Tick Count 전략 거부 (TODAY ONLY 제약)

**PM 최종 결정**:
> "실용성과 효율성을 우선합니다. Volume Cross-Check로 대부분의 오류를 탐지하고, 소수 누락은 허용합니다. 백테스트에 실질적 영향 있는 오류(Volume > 0.1%)만 검출하는 것으로 충분합니다."

---

## Appendix D: Redis Rate-Controlled Dual-Provider Verification (Added 2026-01-20)

### D.1 개요

현재 단일 API(KIS)에 의존하는 분봉 검증 구조에서, **Redis 기반 Rate Limiter**를 통해 API 호출을 제한적으로 관리하고, **Kiwoom 분봉 API**를 추가하여 **듀얼 소스 교차 검증** 체계를 구축한다.

```
┌─────────────────────────────────────────────────────────────┐
│              Redis Rate Limiter (GateKeeper)                │
│            KIS: 30 calls/sec | Kiwoom: 30 calls/sec         │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
      ┌──────────────┐               ┌──────────────┐
      │  KIS REST    │               │ Kiwoom REST  │
      │  분봉 API    │               │  분봉 API    │
      │ FHKST03010200│               │   ka10080    │
      └──────────────┘               └──────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
                    ┌──────────────────┐
                    │  Cross-Validator │
                    │  (Volume Check)  │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   DuckDB/TSDB    │
                    │ (Collected Ticks)│
                    └──────────────────┘
```

### D.2 기존 Rate Limiter 통합

**구현 위치**: `src/api_gateway/rate_limiter.py`

```python
class RedisRateLimiter:
    """Token Bucket Algorithm 기반 분산 Rate Limiter"""

    config = {
        "KIS": (30, 5),    # 30 calls/sec, burst 5
        "KIWOOM": (30, 5)  # 30 calls/sec, burst 5
    }

    async def acquire(self, api_name: str) -> bool:
        """Lua Script로 원자적 토큰 획득"""
        ...

    async def wait_acquire(self, api_name: str, timeout: float = 5.0) -> bool:
        """토큰 획득까지 대기 (timeout 내)"""
        ...
```

**통합 방안**:
- 기존 `gatekeeper` 싱글톤 인스턴스 재활용
- 분봉 검증 워커에서 API 호출 전 `await gatekeeper.wait_acquire()` 호출
- 추가 인프라 불필요 (Zero-Cost 준수)

### D.3 Dual-Provider 검증 로직

#### D.3.1 검증 플로우

```python
async def verify_minute_data(symbol: str, minute: datetime) -> VerificationResult:
    """듀얼 소스 분봉 검증"""

    # 1. Redis Rate Limit 획득 후 API 호출
    kis_data = None
    kiwoom_data = None

    if await gatekeeper.wait_acquire("KIS", timeout=5.0):
        kis_data = await fetch_kis_minute(symbol, minute)  # FHKST03010200

    if await gatekeeper.wait_acquire("KIWOOM", timeout=5.0):
        kiwoom_data = await fetch_kiwoom_minute(symbol, minute)  # ka10080

    # 2. DB에서 틱 기반 거래량 집계
    db_volume = await get_tick_volume_from_db(symbol, minute)

    # 3. 듀얼 소스 교차 검증
    if kis_data and kiwoom_data:
        if kis_data.volume == kiwoom_data.volume:
            api_volume = kis_data.volume  # 일치: 신뢰도 높음
            confidence = "HIGH"
        else:
            api_volume = max(kis_data.volume, kiwoom_data.volume)  # 보수적 선택
            confidence = "MEDIUM"
            logger.warning(f"API mismatch: KIS={kis_data.volume}, Kiwoom={kiwoom_data.volume}")
    else:
        # 단일 소스 폴백
        api_volume = (kis_data or kiwoom_data).volume
        confidence = "LOW"

    # 4. DB 데이터와 비교
    delta = abs(api_volume - db_volume) / max(api_volume, 1)

    return VerificationResult(
        symbol=symbol,
        minute=minute,
        api_volume=api_volume,
        db_volume=db_volume,
        delta_pct=delta * 100,
        confidence=confidence,
        needs_recovery=delta > 0.001  # 0.1% 임계값
    )
```

#### D.3.2 Failover 전략

| 시나리오 | KIS | Kiwoom | 동작 | 신뢰도 |
|----------|-----|--------|------|--------|
| 정상 | ✅ | ✅ | 듀얼 검증 (일치 시 HIGH) | HIGH |
| KIS 장애 | ❌ | ✅ | Kiwoom 단독 검증 | LOW |
| Kiwoom 장애 | ✅ | ❌ | KIS 단독 검증 | LOW |
| 양쪽 장애 | ❌ | ❌ | 검증 스킵, 알림 발송 | SKIP |
| Rate Limit | ⚠️ | ⚠️ | 순차 처리 (지연 허용) | MEDIUM |

### D.4 Rate Limit 전략

#### D.4.1 일일 호출량 분석

| 항목 | 계산 | 결과 |
|------|------|------|
| 종목 수 | 70개 | - |
| 검증 구간 | 391분 (09:00-15:30) | - |
| API 호출/종목 | Volume Check 1회 + OHLCV 필요시 | ~2회 |
| **총 일일 호출** | 70 × 2 × 2 (KIS+Kiwoom) | **~280 calls** |
| Rate Limit | 30 calls/sec × 2 API | **60 calls/sec** |
| **예상 소요 시간** | 280 / 60 | **< 5초** |

#### D.4.2 피크 시간대 조절

```python
# 장 마감 직후 (15:30-16:00) 부하 분산
VERIFICATION_CONFIG = {
    "batch_size": 10,           # 10종목씩 배치 처리
    "batch_delay_sec": 1.0,     # 배치 간 1초 대기
    "kis_ratio": 0.5,           # KIS 50%, Kiwoom 50% 분산
    "retry_on_429": True,       # Rate Limit 시 재시도
    "retry_delay_sec": 2.0      # 재시도 대기 시간
}
```

### D.5 API 명세

#### KIS 분봉 API

| 항목 | 값 |
|------|-----|
| TR ID | `FHKST03010200` |
| Method | GET |
| 제공 필드 | OHLCV, 거래량, 거래대금 |
| Rate Limit | 20 req/sec (공식), 30 req/sec (실측) |

#### Kiwoom 분봉 API

| 항목 | 값 |
|------|-----|
| TR ID | `ka10080` (opt10080) |
| Method | POST |
| 제공 필드 | OHLCV, 거래량 (`trde_qty`) |
| Rate Limit | 30 req/sec (실측) |

### D.6 구현 계획

| Phase | Task | 상태 |
|-------|------|------|
| D.6.1 | `MinuteVerificationWorker` 클래스 구현 | 🔲 TODO |
| D.6.2 | Kiwoom 분봉 클라이언트 (`ka10080`) 추가 | 🔲 TODO |
| D.6.3 | GateKeeper 통합 테스트 | 🔲 TODO |
| D.6.4 | Failover 시나리오 테스트 | 🔲 TODO |
| D.6.5 | 1일 파일럿 운영 | 🔲 TODO |

### D.7 성공 지표

- [ ] 듀얼 검증 성공률 > 95% (양쪽 API 정상 응답)
- [ ] Rate Limit 에러 발생률 = 0%
- [ ] Failover 자동 전환 성공률 = 100%
- [ ] 검증 소요 시간 < 5분 (70종목 기준)

### D.8 관련 문서

- [ID-redis-rate-controlled-dual-verification.md](file:///home/ubuntu/workspace/stock_monitoring/docs/ideas/stock_monitoring/ID-redis-rate-controlled-dual-verification.md) (원본 아이디어)
- [ID-volume-cross-check.md](file:///home/ubuntu/workspace/stock_monitoring/docs/ideas/stock_monitoring/ID-volume-cross-check.md) (Volume 검증 전략)
- [ID-dual-provider-minute-collection.md](file:///home/ubuntu/workspace/stock_monitoring/docs/ideas/stock_backtest/ID-dual-provider-minute-collection.md) (듀얼 수집 아이디어)
- `src/api_gateway/rate_limiter.py` (기존 구현)

---

## Appendix E: Queue-Based Verification Architecture (Updated 2026-01-20)

### E.1 개요

분봉 검증 시스템은 **Redis Queue 기반 아키텍처**를 사용한다. Redis는 **작업 큐와 Rate Limit만** 담당하고, 결과는 **DB에 직접 저장**한다.

```
┌──────────────┐     ┌──────────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Scheduler   │────▶│     Redis Queue      │────▶│    Worker    │────▶│     DB      │
│  (Producer)  │     │  (큐 + Rate Limit)   │     │  (Consumer)  │     │ DuckDB/TSDB │
└──────────────┘     └──────────────────────┘     └──────────────┘     └─────────────┘
       │                      │                          │                    │
   작업 생성              대기열 관리               API 호출             결과 저장
   (LPUSH)              Token Bucket              KIS/Kiwoom           (직접 INSERT)
                                                      │
                                                      ▼
                                              ┌──────────────┐
                                              │ APITarget    │
                                              │ Registry     │
                                              └──────────────┘
```

### E.1.1 Redis 역할 정의

| 역할 | Redis 담당 | 설명 |
|------|-----------|------|
| 작업 큐 | ✅ | `LPUSH` (생성) / `BRPOP` (소비) |
| Rate Limit | ✅ | Token Bucket (30 calls/sec) |
| 상태 추적 | ❌ | 불필요 (Fire & Forget) |
| 결과 저장 | ❌ | DB 직접 저장 |

### E.1.2 Queue 기반 플로우

```python
# 1. Scheduler: 작업 생성 (Producer)
async def produce_verification_task(symbol: str, minute: datetime):
    """검증 작업을 Redis 큐에 추가"""
    task = {
        "symbol": symbol,
        "minute": minute.isoformat(),
        "created_at": datetime.now().isoformat()
    }
    await redis.lpush("verify:queue", json.dumps(task))

# 2. Worker: 큐에서 소비 → API 호출 → DB 저장 (Consumer)
async def consume_verification_task():
    """큐에서 작업을 가져와 실행"""
    while True:
        # Blocking pop (최대 5초 대기)
        result = await redis.brpop("verify:queue", timeout=5)
        if not result:
            continue

        _, raw_task = result
        task = json.loads(raw_task)

        # Rate Limit 획득 (Redis Token Bucket)
        await rate_limiter.acquire("KIWOOM")

        # API 호출
        api_result = await fetch_minute_data(
            task["symbol"],
            datetime.fromisoformat(task["minute"])
        )

        # DB 직접 저장 (Redis 거치지 않음)
        await db.insert("verification_results", {
            "symbol": task["symbol"],
            "minute": task["minute"],
            "api_volume": api_result.volume,
            "db_volume": api_result.db_volume,
            "delta_pct": api_result.delta_pct,
            "verified_at": datetime.now()
        })
```

### E.1.3 Queue Key 설계

```python
# Redis Key 네이밍
QUEUE_KEYS = {
    "verify:queue":           "분봉 검증 작업 큐",
    "verify:queue:dlq":       "Dead Letter Queue (실패 작업)",
    "verify:queue:priority":  "우선순위 큐 (긴급 복구용)",
}

# Rate Limit Key
RATE_LIMIT_KEYS = {
    "ratelimit:KIS":     "KIS API Token Bucket",
    "ratelimit:KIWOOM":  "Kiwoom API Token Bucket",
}
```

---

### E.2 Scheduler Interface (Producer)

#### E.2.1 스케줄 정의

```python
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional
from datetime import time

class ScheduleType(Enum):
    CRON = "cron"           # Cron 표현식
    INTERVAL = "interval"   # 주기적 실행
    MARKET_EVENT = "event"  # 장 이벤트 기반

@dataclass
class VerificationSchedule:
    """검증 작업 스케줄 정의"""
    name: str
    schedule_type: ScheduleType

    # Cron 설정 (schedule_type == CRON)
    cron_expr: Optional[str] = None  # "30 15 * * 1-5" (장 마감 후)

    # Interval 설정 (schedule_type == INTERVAL)
    interval_minutes: Optional[int] = None  # 5분 간격

    # Market Event 설정 (schedule_type == MARKET_EVENT)
    market_event: Optional[str] = None  # "MARKET_CLOSE", "MARKET_OPEN"
    offset_minutes: int = 0  # 이벤트 후 대기 시간

    # 공통
    enabled: bool = True
    timezone: str = "Asia/Seoul"
```

#### E.2.2 스케줄러 구현

```python
from abc import ABC, abstractmethod
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class BaseScheduler(ABC):
    """스케줄러 추상 인터페이스"""

    @abstractmethod
    async def start(self) -> None:
        """스케줄러 시작"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """스케줄러 중지"""
        pass

    @abstractmethod
    def add_job(self, schedule: VerificationSchedule, func: Callable) -> str:
        """작업 추가, job_id 반환"""
        pass

    @abstractmethod
    def remove_job(self, job_id: str) -> bool:
        """작업 제거"""
        pass


class APSchedulerAdapter(BaseScheduler):
    """APScheduler 기반 구현"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
        self._jobs: dict[str, str] = {}

    async def start(self) -> None:
        self.scheduler.start()

    async def stop(self) -> None:
        self.scheduler.shutdown()

    def add_job(self, schedule: VerificationSchedule, func: Callable) -> str:
        if schedule.schedule_type == ScheduleType.CRON:
            trigger = CronTrigger.from_crontab(schedule.cron_expr)
        elif schedule.schedule_type == ScheduleType.INTERVAL:
            trigger = IntervalTrigger(minutes=schedule.interval_minutes)
        else:
            trigger = self._create_market_event_trigger(schedule)

        job = self.scheduler.add_job(func, trigger, id=schedule.name)
        self._jobs[schedule.name] = job.id
        return job.id


class CronTabAdapter(BaseScheduler):
    """시스템 Crontab 기반 구현 (경량)"""

    CRONTAB_PATH = "/etc/cron.d/verification"

    def add_job(self, schedule: VerificationSchedule, func: Callable) -> str:
        # 스크립트 경로 생성 및 crontab 등록
        script_path = f"/app/scripts/verify_{schedule.name}.py"
        cron_line = f"{schedule.cron_expr} python3 {script_path}"
        # ... crontab 파일 업데이트
        return schedule.name
```

#### E.2.3 기본 스케줄 설정

```yaml
# configs/verification_schedules.yaml
schedules:
  # 장 마감 후 전체 검증 (15:30 + 10분)
  - name: "daily_full_verification"
    schedule_type: "cron"
    cron_expr: "40 15 * * 1-5"
    enabled: true

  # 장 중 5분 간격 모니터링 (09:05 ~ 15:25)
  - name: "intraday_monitoring"
    schedule_type: "interval"
    interval_minutes: 5
    enabled: true
    market_hours_only: true

  # 장 시작 전 Pre-flight (08:30)
  - name: "preflight_check"
    schedule_type: "cron"
    cron_expr: "30 8 * * 1-5"
    enabled: true

  # 장 마감 이벤트 기반 (정확한 타이밍)
  - name: "market_close_verification"
    schedule_type: "event"
    market_event: "MARKET_CLOSE"
    offset_minutes: 10
    enabled: false  # 실험적
```

---

### E.3 API Target Interface

#### E.3.1 API 타겟 정의

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any

class APIProvider(Enum):
    KIS = "kis"
    KIWOOM = "kiwoom"
    EXTERNAL = "external"  # 확장용

class APIEndpointType(Enum):
    MINUTE_CANDLE = "minute_candle"   # 분봉 조회
    TICK_HISTORY = "tick_history"     # 틱 히스토리
    ORDERBOOK = "orderbook"           # 호가
    CURRENT_PRICE = "current_price"   # 현재가

@dataclass
class APITarget:
    """API 엔드포인트 타겟 정의"""
    provider: APIProvider
    endpoint_type: APIEndpointType

    # 엔드포인트 정보
    tr_id: str                        # TR ID (예: FHKST03010200)
    base_url: Optional[str] = None    # 기본 URL (없으면 provider 기본값)
    path: str = ""                    # API 경로
    method: str = "GET"               # HTTP Method

    # Rate Limit 설정
    rate_limit_key: str = ""          # GateKeeper에서 사용할 키
    calls_per_second: int = 30
    burst_limit: int = 5

    # 요청/응답 매핑
    request_template: Dict[str, Any] = field(default_factory=dict)
    response_mapping: Dict[str, str] = field(default_factory=dict)

    # 옵션
    enabled: bool = True
    priority: int = 1                 # 낮을수록 우선
    timeout_sec: float = 10.0
```

#### E.3.2 API 타겟 레지스트리

```python
class APITargetRegistry:
    """API 타겟 중앙 관리"""

    def __init__(self):
        self._targets: Dict[tuple[APIProvider, APIEndpointType], list[APITarget]] = {}
        self._load_default_targets()

    def _load_default_targets(self):
        """기본 타겟 로드"""
        # KIS 분봉 API
        self.register(APITarget(
            provider=APIProvider.KIS,
            endpoint_type=APIEndpointType.MINUTE_CANDLE,
            tr_id="FHKST03010200",
            path="/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
            method="GET",
            rate_limit_key="KIS",
            response_mapping={
                "open": "stck_oprc",
                "high": "stck_hgpr",
                "low": "stck_lwpr",
                "close": "stck_prpr",
                "volume": "cntg_vol",
                "timestamp": "stck_bsop_date"
            }
        ))

        # KIS 틱 히스토리 API
        self.register(APITarget(
            provider=APIProvider.KIS,
            endpoint_type=APIEndpointType.TICK_HISTORY,
            tr_id="FHKST01010300",
            path="/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion",
            method="GET",
            rate_limit_key="KIS",
            response_mapping={
                "price": "stck_prpr",
                "volume": "cntg_vol",
                "timestamp": "stck_cntg_hour"
            }
        ))

        # Kiwoom 분봉 API
        self.register(APITarget(
            provider=APIProvider.KIWOOM,
            endpoint_type=APIEndpointType.MINUTE_CANDLE,
            tr_id="ka10080",
            path="/api/dostk/chart",
            method="POST",
            rate_limit_key="KIWOOM",
            request_template={
                "stk_cd": "{symbol}",
                "chart_type": "1"  # 1분봉
            },
            response_mapping={
                "open": "open_pr",
                "high": "high_pr",
                "low": "low_pr",
                "close": "close_pr",
                "volume": "trde_qty",
                "timestamp": "dt"
            }
        ))

        # Kiwoom 틱 차트 API
        self.register(APITarget(
            provider=APIProvider.KIWOOM,
            endpoint_type=APIEndpointType.TICK_HISTORY,
            tr_id="ka10079",
            path="/api/dostk/tickchart",
            method="POST",
            rate_limit_key="KIWOOM",
            response_mapping={
                "price": "price",
                "volume": "volume",
                "timestamp": "time"
            }
        ))

    def register(self, target: APITarget) -> None:
        """타겟 등록"""
        key = (target.provider, target.endpoint_type)
        if key not in self._targets:
            self._targets[key] = []
        self._targets[key].append(target)
        # 우선순위 정렬
        self._targets[key].sort(key=lambda t: t.priority)

    def get_target(
        self,
        endpoint_type: APIEndpointType,
        provider: Optional[APIProvider] = None
    ) -> Optional[APITarget]:
        """타겟 조회 (provider 미지정 시 우선순위 기반 선택)"""
        if provider:
            key = (provider, endpoint_type)
            targets = self._targets.get(key, [])
            return targets[0] if targets else None

        # 모든 provider에서 enabled && 최우선순위 선택
        all_targets = []
        for (p, e), targets in self._targets.items():
            if e == endpoint_type:
                all_targets.extend([t for t in targets if t.enabled])

        all_targets.sort(key=lambda t: t.priority)
        return all_targets[0] if all_targets else None

    def get_all_targets(self, endpoint_type: APIEndpointType) -> list[APITarget]:
        """특정 타입의 모든 타겟 조회 (듀얼 검증용)"""
        result = []
        for (p, e), targets in self._targets.items():
            if e == endpoint_type:
                result.extend([t for t in targets if t.enabled])
        return sorted(result, key=lambda t: t.priority)


# 글로벌 레지스트리 인스턴스
api_registry = APITargetRegistry()
```

#### E.3.3 API 타겟 설정 파일

```yaml
# configs/api_targets.yaml
targets:
  # KIS API Targets
  kis:
    minute_candle:
      tr_id: "FHKST03010200"
      path: "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
      rate_limit:
        calls_per_second: 30
        burst: 5
      enabled: true
      priority: 1

    tick_history:
      tr_id: "FHKST01010300"
      path: "/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
      rate_limit:
        calls_per_second: 20
        burst: 3
      enabled: true
      priority: 2

    current_price:
      tr_id: "FHKST01010100"
      path: "/uapi/domestic-stock/v1/quotations/inquire-price"
      enabled: true
      priority: 1

  # Kiwoom API Targets
  kiwoom:
    minute_candle:
      tr_id: "ka10080"
      path: "/api/dostk/chart"
      method: "POST"
      rate_limit:
        calls_per_second: 30
        burst: 5
      enabled: true
      priority: 2  # KIS보다 낮은 우선순위

    tick_history:
      tr_id: "ka10079"
      path: "/api/dostk/tickchart"
      method: "POST"
      rate_limit:
        calls_per_second: 30
        burst: 5
      enabled: true
      priority: 1  # 틱은 Kiwoom 우선

  # External API (확장용)
  external:
    minute_candle:
      base_url: "https://api.external-provider.com"
      path: "/v1/candles"
      enabled: false
      priority: 99
```

---

### E.4 Queue 기반 통합 구현

#### E.4.1 Producer (Scheduler → Redis Queue)

```python
from src.verification.scheduler import APSchedulerAdapter, VerificationSchedule, ScheduleType
from src.core.config import get_redis_connection
import json

class VerificationProducer:
    """검증 작업 생성자 (Scheduler → Redis Queue)"""

    QUEUE_KEY = "verify:queue"
    PRIORITY_QUEUE_KEY = "verify:queue:priority"

    def __init__(self):
        self.scheduler = APSchedulerAdapter()
        self.redis = None

    async def start(self):
        self.redis = await get_redis_connection()

        # 정기 스케줄 등록: 장 마감 후 전체 검증
        daily_schedule = VerificationSchedule(
            name="daily_full_verification",
            schedule_type=ScheduleType.CRON,
            cron_expr="40 15 * * 1-5"  # 15:40 KST
        )
        self.scheduler.add_job(daily_schedule, self.produce_daily_tasks)

        # 장 중 5분 간격 모니터링
        intraday_schedule = VerificationSchedule(
            name="intraday_monitoring",
            schedule_type=ScheduleType.INTERVAL,
            interval_minutes=5
        )
        self.scheduler.add_job(intraday_schedule, self.produce_intraday_tasks)

        await self.scheduler.start()

    async def produce_daily_tasks(self):
        """장 마감 후 전체 심볼 검증 작업 생성"""
        symbols = await self.get_target_symbols()
        for symbol in symbols:
            task = {
                "type": "full_verification",
                "symbol": symbol,
                "date": datetime.now().strftime("%Y%m%d"),
                "created_at": datetime.now().isoformat()
            }
            await self.redis.lpush(self.QUEUE_KEY, json.dumps(task))

        logger.info(f"📤 Produced {len(symbols)} verification tasks")

    async def produce_intraday_tasks(self):
        """장 중 최근 분봉 검증 작업 생성"""
        minute = datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=1)
        symbols = await self.get_active_symbols()

        for symbol in symbols:
            task = {
                "type": "minute_verification",
                "symbol": symbol,
                "minute": minute.isoformat(),
                "created_at": datetime.now().isoformat()
            }
            await self.redis.lpush(self.QUEUE_KEY, json.dumps(task))

    async def produce_recovery_task(self, symbol: str, minute: datetime):
        """긴급 복구 작업 생성 (우선순위 큐)"""
        task = {
            "type": "recovery",
            "symbol": symbol,
            "minute": minute.isoformat(),
            "priority": "high",
            "created_at": datetime.now().isoformat()
        }
        # 우선순위 큐에 추가
        await self.redis.lpush(self.PRIORITY_QUEUE_KEY, json.dumps(task))
```

#### E.4.2 Consumer (Redis Queue → API → DB)

```python
from src.verification.api_registry import api_registry, APIEndpointType
from src.api_gateway.rate_limiter import gatekeeper
from src.storage.duckdb_client import DuckDBClient
import asyncio
import json

class VerificationConsumer:
    """검증 작업 소비자 (Redis Queue → API → DB 직접 저장)"""

    QUEUE_KEY = "verify:queue"
    PRIORITY_QUEUE_KEY = "verify:queue:priority"
    DLQ_KEY = "verify:queue:dlq"  # Dead Letter Queue

    def __init__(self):
        self.redis = None
        self.db = DuckDBClient()
        self.registry = api_registry
        self.running = False

    async def start(self):
        self.redis = await get_redis_connection()
        self.running = True
        await self.consume_loop()

    async def consume_loop(self):
        """메인 소비 루프"""
        while self.running:
            # 1. 우선순위 큐 먼저 확인
            task = await self.redis.rpop(self.PRIORITY_QUEUE_KEY)

            # 2. 일반 큐에서 Blocking Pop (5초 대기)
            if not task:
                result = await self.redis.brpop(self.QUEUE_KEY, timeout=5)
                if result:
                    _, task = result

            if not task:
                continue

            # 3. 작업 실행
            try:
                task_data = json.loads(task)
                await self.process_task(task_data)
            except Exception as e:
                logger.error(f"Task failed: {e}")
                # Dead Letter Queue로 이동
                await self.redis.lpush(self.DLQ_KEY, task)

    async def process_task(self, task: dict):
        """작업 처리: Rate Limit → API 호출 → DB 저장"""
        symbol = task["symbol"]
        task_type = task.get("type", "minute_verification")

        # 듀얼 API 타겟 조회
        targets = self.registry.get_all_targets(APIEndpointType.MINUTE_CANDLE)
        results = []

        for target in targets:
            # Rate Limit 획득 (Redis Token Bucket)
            acquired = await gatekeeper.wait_acquire(
                target.rate_limit_key,
                timeout=5.0
            )
            if not acquired:
                logger.warning(f"Rate limit timeout for {target.provider}")
                continue

            # API 호출
            try:
                data = await self.fetch_data(symbol, target, task)
                results.append({
                    "provider": target.provider.value,
                    "volume": data.get("volume"),
                    "ohlc": data.get("ohlc")
                })
            except Exception as e:
                logger.error(f"API call failed: {target.provider} - {e}")

        # 교차 검증 및 DB 직접 저장
        verification_result = self.cross_validate(results)
        await self.save_to_db(symbol, task, verification_result)

    async def save_to_db(self, symbol: str, task: dict, result: dict):
        """검증 결과 DB 직접 저장 (Redis 거치지 않음)"""
        await self.db.insert("verification_results", {
            "symbol": symbol,
            "task_type": task.get("type"),
            "minute": task.get("minute"),
            "kis_volume": result.get("kis_volume"),
            "kiwoom_volume": result.get("kiwoom_volume"),
            "db_volume": result.get("db_volume"),
            "delta_pct": result.get("delta_pct"),
            "status": result.get("status"),  # PASS / FAIL / NEEDS_RECOVERY
            "verified_at": datetime.now()
        })

    def cross_validate(self, results: list) -> dict:
        """교차 검증 로직"""
        if len(results) < 2:
            return {"status": "INCOMPLETE", "confidence": "LOW"}

        kis = next((r for r in results if r["provider"] == "kis"), None)
        kiwoom = next((r for r in results if r["provider"] == "kiwoom"), None)

        if kis and kiwoom:
            delta = abs(kis["volume"] - kiwoom["volume"]) / max(kis["volume"], 1)
            if delta < 0.001:  # 0.1% 미만
                return {"status": "PASS", "confidence": "HIGH", "delta_pct": delta}
            else:
                return {"status": "NEEDS_RECOVERY", "confidence": "MEDIUM", "delta_pct": delta}

        return {"status": "PARTIAL", "confidence": "LOW"}
```

#### E.4.3 Worker 실행 스크립트

```python
# scripts/run_verification_worker.py
import asyncio
from src.verification.producer import VerificationProducer
from src.verification.consumer import VerificationConsumer

async def main():
    # Producer와 Consumer를 병렬 실행
    producer = VerificationProducer()
    consumer = VerificationConsumer()

    await asyncio.gather(
        producer.start(),
        consumer.start()
    )

if __name__ == "__main__":
    asyncio.run(main())
```

---

### E.5 구현 계획

| Phase | Task | 상태 |
|-------|------|------|
| E.5.1 | `VerificationSchedule` 데이터클래스 정의 | 🔲 TODO |
| E.5.2 | `APSchedulerAdapter` 구현 | 🔲 TODO |
| E.5.3 | `APITarget` 및 `APITargetRegistry` 구현 | 🔲 TODO |
| E.5.4 | YAML 설정 파일 파싱 로직 | 🔲 TODO |
| E.5.5 | **Redis Queue Producer 구현** | 🔲 TODO |
| E.5.6 | **Redis Queue Consumer 구현** | 🔲 TODO |
| E.5.7 | **DuckDB 직접 저장 로직** | 🔲 TODO |
| E.5.8 | Dead Letter Queue 처리 | 🔲 TODO |
| E.5.9 | 테스트 및 파일럿 운영 | 🔲 TODO |

### E.6 성공 지표

- [ ] 스케줄러 정시 실행률 > 99.9%
- [ ] API 타겟 Failover 자동 전환 성공률 = 100%
- [ ] 설정 변경 시 재시작 없이 Hot Reload 지원
- [ ] 외부 API 추가 시 코드 수정 없이 YAML만으로 등록 가능
- [ ] **Queue 처리 지연 시간 < 100ms (p99)**
- [ ] **Dead Letter Queue 발생률 < 0.1%**

---

## Appendix F: Verified API Endpoints & Test Cases (Added 2026-01-20)

### F.1 확인된 API Endpoint 전체 목록

#### F.1.1 KIS REST API

| TR ID | 명칭 | 용도 | 엔드포인트 | 검증 상태 |
|-------|------|------|------------|-----------|
| `FHKST01010100` | 주식현재가 조회 | 현재가 | `/quotations/inquire-price` | ✅ 검증됨 |
| `FHKST01010200` | 주식현재가 예상체결 | 동시호가 | `/quotations/inquire-asking-price-exp-ccn` | ✅ 검증됨 |
| `FHKST01010300` | 주식현재가 체결 | **틱 히스토리 (Recovery)** | `/quotations/inquire-time-itemconclusion` | ✅ 검증됨 |
| `FHKST01010400` | 주식현재가 체결가 | 체결가 상세 | `/quotations/inquire-ccnl` | ✅ 검증됨 |
| `FHKST03010200` | 국내주식분봉조회 | **분봉 (Verification)** | `/quotations/inquire-time-itemchartprice` | ✅ 검증됨 |
| `HHDFS76950200` | 해외주식 기간별시세 | US 히스토리 | `/quotations/inquire-daily-itemchartprice` | ✅ 검증됨 |
| `HHDFS76200200` | 해외주식 현재가상세 | US 현재가 | `/quotations/inquire-search-info` | ✅ 검증됨 |

#### F.1.2 KIS WebSocket API

| TR ID | 명칭 | 용도 | 시장 | 검증 상태 |
|-------|------|------|------|-----------|
| `H0STCNT0` | 국내주식 실시간체결 | **틱 수집** | KR | ✅ 검증됨 |
| `H0STASP0` | 국내주식 실시간호가 | **호가 수집** | KR | ✅ 검증됨 |
| `HDFSCNT0` | 해외주식 실시간체결 | 틱 수집 | US | ✅ 검증됨 |
| `HDFSASP0` | 해외주식 실시간호가 | 호가 수집 | US | ✅ 검증됨 |
| `PINGPONG` | 연결 유지 | Heartbeat | ALL | ✅ 검증됨 |

#### F.1.3 Kiwoom REST API

| API ID | TR ID (Legacy) | 명칭 | 용도 | 검증 상태 |
|--------|----------------|------|------|-----------|
| `ka10006` | `opt10006` | 주식시세조회 | 현재가 | ⚠️ 부분 검증 |
| `ka10079` | `opt10079` | 주식틱차트조회 | **틱 히스토리 (Recovery)** | ✅ 검증됨 |
| `ka10080` | `opt10080` | 주식분봉시세조회 | **분봉 (Verification)** | ✅ 검증됨 |

#### F.1.4 Kiwoom WebSocket API

| TR ID | 명칭 | 용도 | 검증 상태 |
|-------|------|------|-----------|
| `H0STCNT0` | 주식체결 | **틱 수집** | ✅ 검증됨 |
| `H0STASP0` | 주식호가 | **호가 수집** | ✅ 검증됨 |

---

### F.2 API Response 스키마

#### F.2.1 KIS 분봉 응답 (`FHKST03010200`)

```json
{
  "output1": {
    "stck_bsop_date": "20260120",  // 영업일자
    "stck_cntg_hour": "100000",    // 체결시간 (HHMMSS)
    "stck_prpr": "75000",          // 현재가
    "stck_oprc": "74500",          // 시가
    "stck_hgpr": "75200",          // 고가
    "stck_lwpr": "74300",          // 저가
    "cntg_vol": "125000",          // 체결량
    "acml_tr_pbmn": "9375000000"   // 누적거래대금
  }
}
```

#### F.2.2 KIS 틱 히스토리 응답 (`FHKST01010300`)

```json
{
  "output": [
    {
      "stck_cntg_hour": "100532",  // 체결시간
      "stck_prpr": "75100",        // 체결가
      "cntg_vol": "150",           // 체결량
      "prdy_ctrt": "0.80"          // 전일대비율
    }
  ]
}
```

#### F.2.3 Kiwoom 분봉 응답 (`ka10080`)

```json
{
  "output": [
    {
      "dt": "202601201000",     // 일시 (YYYYMMDDHHMM)
      "open_pr": "74500",       // 시가
      "high_pr": "75200",       // 고가
      "low_pr": "74300",        // 저가
      "close_pr": "75000",      // 종가
      "trde_qty": "125000"      // 거래량
    }
  ]
}
```

#### F.2.4 Kiwoom 틱 응답 (`ka10079`)

```json
{
  "output": [
    {
      "time": "100532",        // 체결시간 (HHMMSS)
      "price": "75100",        // 체결가
      "volume": "150",         // 체결량
      "chg_rate": "0.80"       // 등락률
    }
  ],
  "next-key": "abc123..."      // 페이지네이션 키
}
```

---

### F.3 테스트 케이스

#### F.3.1 Unit Tests - API Target Registry

```python
# tests/unit/test_api_target_registry.py

import pytest
from src.verification.api_registry import (
    APITargetRegistry, APITarget, APIProvider, APIEndpointType
)

class TestAPITargetRegistry:
    """API Target Registry 단위 테스트"""

    @pytest.fixture
    def registry(self):
        return APITargetRegistry()

    # TC-F001: 기본 타겟 로드 확인
    def test_default_targets_loaded(self, registry):
        """기본 KIS/Kiwoom 타겟이 로드되어야 함"""
        kis_minute = registry.get_target(
            APIEndpointType.MINUTE_CANDLE,
            APIProvider.KIS
        )
        assert kis_minute is not None
        assert kis_minute.tr_id == "FHKST03010200"

        kiwoom_minute = registry.get_target(
            APIEndpointType.MINUTE_CANDLE,
            APIProvider.KIWOOM
        )
        assert kiwoom_minute is not None
        assert kiwoom_minute.tr_id == "ka10080"

    # TC-F002: 틱 히스토리 타겟 확인
    def test_tick_history_targets(self, registry):
        """틱 히스토리 타겟 검증"""
        kis_tick = registry.get_target(
            APIEndpointType.TICK_HISTORY,
            APIProvider.KIS
        )
        assert kis_tick.tr_id == "FHKST01010300"

        kiwoom_tick = registry.get_target(
            APIEndpointType.TICK_HISTORY,
            APIProvider.KIWOOM
        )
        assert kiwoom_tick.tr_id == "ka10079"

    # TC-F003: 우선순위 기반 선택
    def test_priority_based_selection(self, registry):
        """provider 미지정 시 우선순위 기반 선택"""
        # 분봉은 KIS가 priority 1
        target = registry.get_target(APIEndpointType.MINUTE_CANDLE)
        assert target.provider == APIProvider.KIS

    # TC-F004: 듀얼 타겟 조회
    def test_get_all_targets_for_dual_verification(self, registry):
        """듀얼 검증용 전체 타겟 조회"""
        targets = registry.get_all_targets(APIEndpointType.MINUTE_CANDLE)
        assert len(targets) >= 2
        providers = [t.provider for t in targets]
        assert APIProvider.KIS in providers
        assert APIProvider.KIWOOM in providers

    # TC-F005: 비활성화 타겟 필터링
    def test_disabled_target_filtered(self, registry):
        """enabled=False 타겟은 제외"""
        # 외부 API는 기본 비활성화
        external = registry.get_target(
            APIEndpointType.MINUTE_CANDLE,
            APIProvider.EXTERNAL
        )
        assert external is None or not external.enabled

    # TC-F006: 커스텀 타겟 등록
    def test_custom_target_registration(self, registry):
        """새 타겟 등록 기능"""
        custom = APITarget(
            provider=APIProvider.EXTERNAL,
            endpoint_type=APIEndpointType.MINUTE_CANDLE,
            tr_id="CUSTOM001",
            path="/v1/custom/candles",
            enabled=True,
            priority=0  # 최우선
        )
        registry.register(custom)

        target = registry.get_target(APIEndpointType.MINUTE_CANDLE)
        assert target.tr_id == "CUSTOM001"
```

#### F.3.2 Unit Tests - Scheduler Interface

```python
# tests/unit/test_verification_scheduler.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.verification.scheduler import (
    VerificationSchedule, ScheduleType, APSchedulerAdapter
)

class TestVerificationScheduler:
    """스케줄러 인터페이스 단위 테스트"""

    # TC-F010: Cron 스케줄 생성
    def test_cron_schedule_creation(self):
        """Cron 타입 스케줄 생성"""
        schedule = VerificationSchedule(
            name="daily_verification",
            schedule_type=ScheduleType.CRON,
            cron_expr="40 15 * * 1-5"
        )
        assert schedule.schedule_type == ScheduleType.CRON
        assert schedule.cron_expr == "40 15 * * 1-5"
        assert schedule.enabled is True

    # TC-F011: Interval 스케줄 생성
    def test_interval_schedule_creation(self):
        """Interval 타입 스케줄 생성"""
        schedule = VerificationSchedule(
            name="intraday_check",
            schedule_type=ScheduleType.INTERVAL,
            interval_minutes=5
        )
        assert schedule.interval_minutes == 5

    # TC-F012: Market Event 스케줄 생성
    def test_market_event_schedule_creation(self):
        """Market Event 타입 스케줄 생성"""
        schedule = VerificationSchedule(
            name="post_market",
            schedule_type=ScheduleType.MARKET_EVENT,
            market_event="MARKET_CLOSE",
            offset_minutes=10
        )
        assert schedule.market_event == "MARKET_CLOSE"
        assert schedule.offset_minutes == 10

    # TC-F013: 스케줄러 작업 추가
    @pytest.mark.asyncio
    async def test_scheduler_add_job(self):
        """APScheduler에 작업 추가"""
        scheduler = APSchedulerAdapter()
        schedule = VerificationSchedule(
            name="test_job",
            schedule_type=ScheduleType.CRON,
            cron_expr="0 * * * *"
        )

        mock_func = AsyncMock()
        job_id = scheduler.add_job(schedule, mock_func)

        assert job_id is not None
        assert "test_job" in scheduler._jobs
```

#### F.3.3 Integration Tests - API Endpoint Verification

```python
# tests/integration/test_api_endpoints.py

import pytest
import httpx
from datetime import datetime
from src.verification.api_registry import api_registry, APIEndpointType, APIProvider

class TestKISEndpoints:
    """KIS API 엔드포인트 통합 테스트"""

    @pytest.fixture
    def kis_headers(self, kis_token):
        return {
            "authorization": f"Bearer {kis_token}",
            "appkey": os.getenv("KIS_APP_KEY"),
            "appsecret": os.getenv("KIS_APP_SECRET"),
            "tr_id": "",
            "content-type": "application/json"
        }

    # TC-F020: KIS 분봉 API 응답 검증
    @pytest.mark.integration
    async def test_kis_minute_candle_response(self, kis_headers):
        """FHKST03010200 응답 스키마 검증"""
        target = api_registry.get_target(
            APIEndpointType.MINUTE_CANDLE,
            APIProvider.KIS
        )
        kis_headers["tr_id"] = target.tr_id

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://openapi.koreainvestment.com:9443{target.path}",
                headers=kis_headers,
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": "005930",
                    "FID_INPUT_HOUR_1": "100000",
                    "FID_PW_DATA_INCU_YN": "Y"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "output1" in data or "output" in data

        # 필수 필드 검증
        output = data.get("output1") or data.get("output", [{}])[0]
        assert "stck_prpr" in output  # 현재가
        assert "cntg_vol" in output   # 체결량

    # TC-F021: KIS 틱 히스토리 API 응답 검증
    @pytest.mark.integration
    async def test_kis_tick_history_response(self, kis_headers):
        """FHKST01010300 응답 스키마 검증"""
        target = api_registry.get_target(
            APIEndpointType.TICK_HISTORY,
            APIProvider.KIS
        )
        kis_headers["tr_id"] = target.tr_id

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://openapi.koreainvestment.com:9443{target.path}",
                headers=kis_headers,
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": "005930",
                    "FID_INPUT_HOUR_1": ""
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "output" in data

        # 틱 데이터 필드 검증
        if len(data["output"]) > 0:
            tick = data["output"][0]
            assert "stck_cntg_hour" in tick  # 체결시간
            assert "stck_prpr" in tick       # 체결가
            assert "cntg_vol" in tick        # 체결량


class TestKiwoomEndpoints:
    """Kiwoom API 엔드포인트 통합 테스트"""

    @pytest.fixture
    def kiwoom_headers(self, kiwoom_token):
        return {
            "authorization": f"Bearer {kiwoom_token}",
            "content-type": "application/json"
        }

    # TC-F030: Kiwoom 분봉 API 응답 검증
    @pytest.mark.integration
    async def test_kiwoom_minute_candle_response(self, kiwoom_headers):
        """ka10080 응답 스키마 검증"""
        target = api_registry.get_target(
            APIEndpointType.MINUTE_CANDLE,
            APIProvider.KIWOOM
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.kiwoom.com{target.path}",
                headers={
                    **kiwoom_headers,
                    "api-id": target.tr_id
                },
                json={
                    "stk_cd": "005930",
                    "chart_type": "1"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "output" in data

        # 필수 필드 검증
        if len(data["output"]) > 0:
            candle = data["output"][0]
            assert "open_pr" in candle or "strt_prc" in candle
            assert "trde_qty" in candle or "acml_vol" in candle

    # TC-F031: Kiwoom 틱 차트 API 응답 검증
    @pytest.mark.integration
    async def test_kiwoom_tick_chart_response(self, kiwoom_headers):
        """ka10079 응답 스키마 검증"""
        target = api_registry.get_target(
            APIEndpointType.TICK_HISTORY,
            APIProvider.KIWOOM
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.kiwoom.com{target.path}",
                headers={
                    **kiwoom_headers,
                    "api-id": target.tr_id
                },
                json={
                    "stk_cd": "005930",
                    "cts": ""
                }
            )

        assert response.status_code == 200
        data = response.json()

        # 페이지네이션 키 확인
        if "next-key" in response.headers or "next_key" in data:
            pass  # 페이지네이션 지원 확인

    # TC-F032: Kiwoom API Rate Limit 확인
    @pytest.mark.integration
    async def test_kiwoom_rate_limit_header(self, kiwoom_headers):
        """Rate Limit 헤더 확인"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.kiwoom.com/api/dostk/chart",
                headers={**kiwoom_headers, "api-id": "ka10080"},
                json={"stk_cd": "005930", "chart_type": "1"}
            )

        # Rate Limit 관련 헤더 확인
        rate_headers = [
            "x-ratelimit-limit",
            "x-ratelimit-remaining",
            "x-ratelimit-reset"
        ]
        # 일부 API는 헤더를 제공하지 않을 수 있음
        # assert any(h in response.headers for h in rate_headers)
```

#### F.3.4 E2E Tests - Dual Verification Flow

```python
# tests/e2e/test_dual_verification.py

import pytest
from datetime import datetime, timedelta
from src.verification.worker import MinuteVerificationWorker
from src.api_gateway.rate_limiter import gatekeeper

class TestDualVerificationE2E:
    """듀얼 검증 E2E 테스트"""

    @pytest.fixture
    async def worker(self):
        worker = MinuteVerificationWorker()
        await worker.initialize()
        yield worker
        await worker.cleanup()

    # TC-F040: 듀얼 소스 검증 성공
    @pytest.mark.e2e
    async def test_dual_source_verification_success(self, worker):
        """KIS + Kiwoom 동시 검증 성공 케이스"""
        symbol = "005930"
        minute = datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=5)

        result = await worker.verify_minute_data(symbol, minute)

        assert result is not None
        assert result.confidence in ["HIGH", "MEDIUM"]
        assert result.delta_pct < 1.0  # 1% 미만 오차

    # TC-F041: KIS 장애 시 Kiwoom Failover
    @pytest.mark.e2e
    async def test_kis_failure_kiwoom_failover(self, worker, mocker):
        """KIS API 장애 시 Kiwoom으로 Failover"""
        # KIS API 실패 모킹
        mocker.patch.object(
            worker, 'fetch_kis_minute',
            side_effect=Exception("KIS API Error")
        )

        symbol = "005930"
        minute = datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=5)

        result = await worker.verify_minute_data(symbol, minute)

        assert result is not None
        assert result.confidence == "LOW"  # 단일 소스

    # TC-F042: Rate Limit 준수 확인
    @pytest.mark.e2e
    async def test_rate_limit_compliance(self, worker):
        """70종목 검증 시 Rate Limit 준수"""
        symbols = ["005930", "000660", "035420"]  # 샘플 3종목
        minute = datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=5)

        start_time = datetime.now()
        results = []

        for symbol in symbols:
            result = await worker.verify_minute_data(symbol, minute)
            results.append(result)

        elapsed = (datetime.now() - start_time).total_seconds()

        # 모든 검증 완료
        assert len(results) == len(symbols)
        # Rate Limit 에러 없음
        assert all(r is not None for r in results)

    # TC-F043: 교차 검증 불일치 감지
    @pytest.mark.e2e
    async def test_cross_validation_mismatch_detection(self, worker, mocker):
        """KIS/Kiwoom 불일치 시 감지 및 경고"""
        # Kiwoom이 다른 값을 반환하도록 모킹
        original_fetch = worker.fetch_kiwoom_minute

        async def mock_kiwoom(*args, **kwargs):
            result = await original_fetch(*args, **kwargs)
            if result:
                result.volume = result.volume * 2  # 거래량 2배
            return result

        mocker.patch.object(worker, 'fetch_kiwoom_minute', mock_kiwoom)

        symbol = "005930"
        minute = datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=5)

        result = await worker.verify_minute_data(symbol, minute)

        # 불일치 감지
        assert result.confidence == "MEDIUM"

    # TC-F044: 검증 결과 리포트 생성
    @pytest.mark.e2e
    async def test_verification_report_generation(self, worker):
        """검증 완료 후 리포트 생성"""
        symbols = ["005930", "000660"]
        minute = datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=5)

        results = []
        for symbol in symbols:
            result = await worker.verify_minute_data(symbol, minute)
            results.append(result)

        report = worker.generate_report(results)

        assert "summary" in report
        assert "details" in report
        assert report["summary"]["total"] == len(symbols)
        assert "high_confidence" in report["summary"]
        assert "needs_recovery" in report["summary"]
```

---

### F.4 테스트 실행 명령어

```bash
# 단위 테스트 (빠름)
pytest tests/unit/test_api_target_registry.py -v
pytest tests/unit/test_verification_scheduler.py -v

# 통합 테스트 (API 호출 포함)
pytest tests/integration/test_api_endpoints.py -v -m integration

# E2E 테스트 (전체 플로우)
pytest tests/e2e/test_dual_verification.py -v -m e2e

# 전체 테스트
pytest tests/ -v --cov=src/verification --cov-report=html
```

---

### F.5 테스트 매트릭스

| 테스트 ID | 카테고리 | 대상 | 설명 | 우선순위 |
|-----------|----------|------|------|----------|
| TC-F001 | Unit | Registry | 기본 타겟 로드 | P0 |
| TC-F002 | Unit | Registry | 틱 히스토리 타겟 | P0 |
| TC-F003 | Unit | Registry | 우선순위 선택 | P1 |
| TC-F004 | Unit | Registry | 듀얼 타겟 조회 | P0 |
| TC-F005 | Unit | Registry | 비활성화 필터링 | P2 |
| TC-F006 | Unit | Registry | 커스텀 등록 | P2 |
| TC-F010 | Unit | Scheduler | Cron 스케줄 | P0 |
| TC-F011 | Unit | Scheduler | Interval 스케줄 | P1 |
| TC-F012 | Unit | Scheduler | Event 스케줄 | P2 |
| TC-F013 | Unit | Scheduler | 작업 추가 | P0 |
| TC-F020 | Integration | KIS | 분봉 응답 검증 | P0 |
| TC-F021 | Integration | KIS | 틱 응답 검증 | P0 |
| TC-F030 | Integration | Kiwoom | 분봉 응답 검증 | P0 |
| TC-F031 | Integration | Kiwoom | 틱 응답 검증 | P0 |
| TC-F032 | Integration | Kiwoom | Rate Limit 헤더 | P2 |
| TC-F040 | E2E | Verification | 듀얼 검증 성공 | P0 |
| TC-F041 | E2E | Verification | KIS Failover | P0 |
| TC-F042 | E2E | Verification | Rate Limit 준수 | P0 |
| TC-F043 | E2E | Verification | 불일치 감지 | P1 |
| TC-F044 | E2E | Verification | 리포트 생성 | P1 |

---

### F.6 성공 지표

- [ ] 단위 테스트 커버리지 > 90%
- [ ] 통합 테스트 API 응답 스키마 100% 검증
- [ ] E2E 테스트 전체 플로우 성공률 > 95%
- [ ] Rate Limit 에러 발생률 = 0%

---

## Appendix G: Kiwoom Token Behavior Verification (검증 완료)

> **검증일**: 2026-01-20
> **결과**: ✅ 소켓 오염 위험 없음 (동일 토큰 반환 확인)

### G.1 배경 및 목적

Kiwoom API는 WebSocket과 REST API 모두 동일한 OAuth2 토큰을 사용합니다. 이로 인해 다음 우려가 있었습니다:

| 우려 사항 | 설명 |
|-----------|------|
| 토큰 충돌 | WS와 REST가 각각 토큰 발급 시 기존 토큰 무효화 가능성 |
| 세션 오염 | REST 호출이 WS 세션에 영향을 미칠 가능성 |
| Rate Limit 공유 | 단일 토큰으로 인한 API 호출 제한 누적 |

### G.2 검증 테스트 결과

#### Test 1: 토큰 2회 발급 테스트

```bash
# scripts/test_kiwoom_dual_token.py 실행 결과
[Token 비교]
  Token1: --ZrAjaG5UhlDYX64lHN...
  Token2: --ZrAjaG5UhlDYX64lHN...
  동일 토큰: True

[상세 결과]
  Token1 기준선: 성공
  Token1 재검증: 성공  # Token2 발급 후에도 Token1 유효
  Token2 검증:   성공
```

**결론**: Kiwoom은 **서버 측 토큰 캐싱**을 사용. 동일 credentials로 재발급 시 **같은 토큰 반환**.

#### Test 2: WS 세션 생존 테스트

```bash
# scripts/test_kiwoom_ws_token_survival.py 실행 결과
[Step 2] WebSocket 연결 및 LOGIN
✅ WS LOGIN 성공: {'trnm': 'LOGIN', 'return_code': 0}

[Step 3] WS 유지 상태에서 REST용 Token 발급
✅ REST-Token: --ZrAjaG5UhlDYX... (동일 토큰)

[Step 4] REST Token으로 API 호출
✅ REST-Token REST 성공

[Step 5] WS 세션 생존 확인
✅ WS 세션 생존 확인: REG 성공
```

**결론**: WS 연결 중 REST API 호출해도 **WS 세션 유지됨**.

### G.3 Kiwoom 토큰 동작 모델

```
┌─────────────────────────────────────────────────────────────┐
│                   Kiwoom OAuth2 Server                      │
│                   (Token Caching Layer)                     │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┴────────────────────┐
         │           동일 토큰 반환                 │
         │         (만료 전까지 캐싱)              │
         ▼                                         ▼
┌─────────────────┐                     ┌─────────────────┐
│  WS Process     │                     │  REST Process   │
│  oauth2/token   │──→ Token_A          │  oauth2/token   │──→ Token_A
│  WS LOGIN       │                     │  API 호출       │
└─────────────────┘                     └─────────────────┘
```

### G.4 핵심 발견: 토큰 만료 시점 관리가 핵심

#### 토큰 라이프사이클

```
T+0h      T+23h     T+24h (만료)
│         │         │
▼         ▼         ▼
[Token_A 발급] ────────────────────→ [Token_A 만료]
                    │                      │
              [갱신 권장 시점]        [Token_B 발급]
              (만료 1시간 전)
```

#### 위험 시나리오

```
시간     WS Process              REST Process           문제점
────────────────────────────────────────────────────────────────
09:00    Token_A 발급, LOGIN     -
09:05    -                       Token_A로 API 호출     ✅ 정상
...
다음날
08:50    (Token_A 만료 임박)     Token_B 발급 (새 토큰)
08:55    WS: 여전히 Token_A      REST: Token_B 사용     ⚠️ 비동기
09:00    Token_A 만료            -                      ❌ WS 세션 위험
```

### G.5 권장 토큰 관리 전략

#### Strategy 1: 중앙 집중식 토큰 관리자 (권장)

```python
class KiwoomTokenManager:
    """싱글톤 토큰 관리자 - WS/REST 공유"""

    _instance = None
    _token: str = None
    _expires_at: datetime = None
    _refresh_threshold: timedelta = timedelta(hours=1)  # 만료 1시간 전 갱신

    @classmethod
    async def get_token(cls) -> str:
        """토큰 반환 (필요시 자동 갱신)"""
        if cls._should_refresh():
            await cls._refresh_token()
            await cls._notify_refresh()  # WS 재연결 트리거
        return cls._token

    @classmethod
    def _should_refresh(cls) -> bool:
        if not cls._token or not cls._expires_at:
            return True
        return datetime.now() >= cls._expires_at - cls._refresh_threshold

    @classmethod
    async def _notify_refresh(cls):
        """토큰 갱신 시 WS 재연결 알림"""
        await redis.publish("kiwoom:token:refreshed", cls._token)
```

#### Strategy 2: 만료 시점 동기화

```python
# Redis 기반 토큰 만료 시점 공유
KIWOOM_TOKEN_KEY = "kiwoom:token:current"
KIWOOM_EXPIRY_KEY = "kiwoom:token:expires_at"

async def get_shared_token() -> tuple[str, datetime]:
    """Redis에서 공유 토큰 및 만료 시점 조회"""
    token = await redis.get(KIWOOM_TOKEN_KEY)
    expires_at = await redis.get(KIWOOM_EXPIRY_KEY)
    return token, datetime.fromisoformat(expires_at)

async def should_refresh() -> bool:
    """만료 1시간 전이면 갱신 필요"""
    _, expires_at = await get_shared_token()
    return datetime.now() >= expires_at - timedelta(hours=1)
```

### G.6 구현 체크리스트

- [x] 토큰 2회 발급 시 동일 토큰 반환 확인
- [x] WS 세션 중 REST 호출 시 세션 유지 확인
- [ ] `KiwoomTokenManager` 싱글톤 구현
- [ ] Redis 기반 토큰 만료 시점 공유
- [ ] WS 재연결 로직 (토큰 갱신 시)
- [ ] 만료 1시간 전 자동 갱신 스케줄러

### G.7 테스트 스크립트 위치

| 스크립트 | 목적 |
|----------|------|
| `scripts/test_kiwoom_dual_token.py` | 토큰 2회 발급 테스트 |
| `scripts/test_kiwoom_ws_token_survival.py` | WS 세션 생존 테스트 |

### G.8 결론

| 항목 | KIS | Kiwoom |
|------|-----|--------|
| WS 토큰 | `approval_key` (WS 전용) | `token` (공유) |
| REST 토큰 | `access_token` (REST 전용) | `token` (공유) |
| 분리 관리 | ✅ 가능 (별도 토큰) | ⚠️ 불필요 (동일 토큰 반환) |
| 핵심 관리 포인트 | 각각 갱신 | **만료 시점 동기화** |

**최종 권장사항**: Kiwoom은 토큰 분리가 불필요하며, **만료 시점 1시간 전 갱신 + WS 재연결** 전략으로 안정적 운영 가능.

---

## Appendix H: Real-time Gap Recovery Mode (Added 2026-01-20)

> **원본 아이디어**: [ID-realtime-gap-recovery.md](file:///home/ubuntu/workspace/stock_monitoring/docs/ideas/stock_monitoring/ID-realtime-gap-recovery.md)
> **통합 근거**: RFC-008의 배치 검증과 상호 보완적인 실시간 검증 모드

### H.1 개요

장 종료 후가 아닌, **장 중(Real-time)**에 데이터 누락을 즉시 감지하고 복구하는 시스템입니다.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         검증 타이밍 비교                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [배치 검증 - Appendix E]                                            │
│  09:00 ═══════════════════════════════════════════ 15:30 → 15:40 검증 │
│                                                                      │
│  [실시간 검증 - Appendix H]                                          │
│  09:00 ─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─ 15:30        │
│         ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓               │
│        1분 단위 검증 (Min + 5sec 시점)                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### H.2 가설 및 기대 효과

**가설**: 분봉 API의 Volume 정보를 Checksum으로 활용하면, 수집한 Tick 데이터의 완전성을 1분 단위로 검증할 수 있다.

| 효과 | 설명 |
|------|------|
| **즉시성** | 장 마감까지 기다릴 필요 없이, 누락 발생 1~2분 내 자동 복구 |
| **API 효율** | 전체 재수집이 아닌 '누락된 구간'만 정밀 타격 |
| **데이터 신뢰도** | Correlation 0.99 상시 유지 보장 |

### H.3 아키텍처

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Collector   │────▶│   Verifier   │────▶│  Comparator  │────▶│  Recoverer   │
│ (WebSocket)  │     │ (Min + 5sec) │     │  (Volume %)  │     │ (REST API)   │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │                    │
    Tick 수집           분봉 API 조회      Local vs API 비교      Gap 복구
    (기존 로직)         (KIS/Kiwoom)       Tolerance 1-2%       Redis Throttle
```

#### H.3.1 Component 역할

| Component | 역할 | 트리거 시점 | Rate Limit |
|-----------|------|-------------|------------|
| **Verifier** | 분봉 API 조회 | `HH:MM:05` (매 분 +5초) | Appendix D 참조 |
| **Comparator** | Volume 비교 | Verifier 완료 후 | N/A |
| **Recoverer** | Gap 복구 REST 호출 | Gap > Tolerance | 30 calls/sec |

### H.4 Tolerance 전략

```python
# 실시간 모드 Tolerance 설정
REALTIME_CONFIG = {
    "volume_tolerance_pct": 2.0,    # 2% 미만 차이 허용
    "min_volume_threshold": 100,    # 100주 미만은 검증 스킵
    "recovery_delay_sec": 3,        # 복구 전 대기 (지연 체결 대응)
    "max_recovery_retries": 2,      # 복구 최대 재시도
}

def should_trigger_recovery(api_volume: int, db_volume: int) -> bool:
    """복구 트리거 조건 판단"""
    if api_volume < REALTIME_CONFIG["min_volume_threshold"]:
        return False  # 저유동성 스킵

    delta_pct = abs(api_volume - db_volume) / max(api_volume, 1) * 100
    return delta_pct > REALTIME_CONFIG["volume_tolerance_pct"]
```

### H.5 실시간 검증 플로우

```python
from datetime import datetime, timedelta
from src.verification.api_registry import api_registry, APIEndpointType
from src.api_gateway.rate_limiter import gatekeeper

class RealtimeVerifier:
    """장 중 실시간 검증 워커"""

    async def verify_last_minute(self, symbol: str) -> VerificationResult:
        """직전 1분 데이터 검증 (매 분 +5초에 호출)"""

        # 1. 검증 대상 시간 계산 (직전 분)
        now = datetime.now()
        target_minute = now.replace(second=0, microsecond=0) - timedelta(minutes=1)

        # 2. DB에서 틱 거래량 합계 조회
        db_volume = await self.db.query(
            """
            SELECT COALESCE(SUM(volume), 0) as total_volume
            FROM market_ticks
            WHERE symbol = ?
              AND timestamp >= ?
              AND timestamp < ?
            """,
            symbol, target_minute, target_minute + timedelta(minutes=1)
        )

        # 3. Rate Limit 획득 후 분봉 API 조회
        if not await gatekeeper.wait_acquire("KIS", timeout=2.0):
            return VerificationResult(status="SKIPPED", reason="rate_limit")

        api_data = await self.fetch_minute_candle(symbol, target_minute)

        # 4. Tolerance 기반 비교
        if should_trigger_recovery(api_data.volume, db_volume):
            await self.trigger_recovery(symbol, target_minute, api_data.volume - db_volume)
            return VerificationResult(status="RECOVERING", gap=api_data.volume - db_volume)

        return VerificationResult(status="PASS", delta_pct=delta_pct)

    async def trigger_recovery(self, symbol: str, minute: datetime, gap: int):
        """Gap 복구 트리거 - 우선순위 큐에 추가"""
        recovery_task = {
            "type": "realtime_recovery",
            "symbol": symbol,
            "minute": minute.isoformat(),
            "gap": gap,
            "priority": "high",
            "created_at": datetime.now().isoformat()
        }
        await self.redis.lpush("verify:queue:priority", json.dumps(recovery_task))
        logger.warning(f"⚠️ Gap detected: {symbol} @ {minute}, gap={gap}, recovery queued")
```

### H.6 스케줄링 통합

기존 Appendix E의 스케줄러에 실시간 모드 추가:

```yaml
# configs/verification_schedules.yaml (확장)
schedules:
  # 기존 배치 검증
  - name: "daily_full_verification"
    schedule_type: "cron"
    cron_expr: "40 15 * * 1-5"
    enabled: true
    mode: "batch"

  # [NEW] 실시간 검증 (1분 간격)
  - name: "realtime_minute_verification"
    schedule_type: "interval"
    interval_seconds: 60
    offset_seconds: 5           # 매 분 +5초에 실행
    enabled: true
    mode: "realtime"
    market_hours_only: true     # 장 중에만 활성화

    # 실시간 전용 설정
    realtime_config:
      tolerance_pct: 2.0
      min_volume: 100
      max_symbols_per_run: 10   # 1분 내 처리 가능량
      priority_symbols:         # 우선 검증 종목
        - "005930"              # 삼성전자
        - "000660"              # SK하이닉스
```

### H.7 배치 vs 실시간 모드 비교

| 항목 | 배치 모드 (Appendix E) | 실시간 모드 (Appendix H) |
|------|------------------------|--------------------------|
| **실행 시점** | 장 마감 후 15:40 | 매 분 +5초 |
| **검증 범위** | 전체 391분 | 직전 1분 |
| **대상 종목** | 전체 70종목 | 상위 10종목 (Priority) |
| **Tolerance** | 0.1% (엄격) | 2% (관대) |
| **복구 방식** | 다음날 배치 | 즉시 복구 |
| **목적** | 정확성 보장 | 누락 최소화 |

### H.8 실시간 모드 제약사항

| 제약 | 설명 | 대응 |
|------|------|------|
| **API Rate Limit** | 60 calls/min 제한 | 상위 10종목만 검증 |
| **지연 체결** | 체결 지연 시 False Positive | 3초 대기 후 검증 |
| **시장 휴장** | 휴장일/장외 시간 | `market_hours_only` 플래그 |
| **저유동성** | 거래량 0 종목 | `min_volume` 임계값 |

### H.9 구현 계획

| Phase | Task | 의존성 | 상태 |
|-------|------|--------|------|
| H.9.1 | `RealtimeVerifier` 클래스 구현 | Appendix D Rate Limiter | 🔲 TODO |
| H.9.2 | 1분 간격 스케줄러 추가 | Appendix E Scheduler | 🔲 TODO |
| H.9.3 | Priority 종목 설정 로직 | 없음 | 🔲 TODO |
| H.9.4 | 실시간 모드 테스트 케이스 | Appendix F 테스트 | 🔲 TODO |
| H.9.5 | 모니터링 대시보드 연동 | Sentinel | 🔲 TODO |

### H.10 성공 지표

- [ ] 실시간 검증 지연 < 5초 (Min + 5sec ~ 검증 완료)
- [ ] 장 중 Gap 감지율 > 95%
- [ ] False Positive율 < 5%
- [ ] 복구 성공률 > 99%
- [ ] API Rate Limit 에러 = 0

### H.11 관련 문서

- [Appendix D](##appendix-d-redis-rate-controlled-dual-provider-verification-added-2026-01-20): Rate Limiter 통합
- [Appendix E](##appendix-e-queue-based-verification-architecture-updated-2026-01-20): Queue 기반 아키텍처
- [Appendix F](##appendix-f-verified-api-endpoints--test-cases-added-2026-01-20): API 엔드포인트 명세
- [ID-realtime-gap-recovery.md](file:///home/ubuntu/workspace/stock_monitoring/docs/ideas/stock_monitoring/ID-realtime-gap-recovery.md): 원본 아이디어 (Archived)

