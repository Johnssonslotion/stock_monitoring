# ISSUE-044: TimescaleDB Tick-to-Candle Automation & Recovery Sync

**Status**: Open
**Priority**: P1 (High)
**Type**: Feature (Automation + Architecture Refactoring)
**Created**: 2026-01-28
**Assignee**: Agent
**Reviewed**: 2026-01-28 (Council of Six)
**Architecture Decision**: 2026-01-28 (옵션 A 채택)

---

## 1. 개요 (Problem Description)

현재 `market_ticks` 테이블에 틱 데이터는 정상 수집되고 있으나, 이를 기반으로 하는 `market_candles` (분봉) 데이터는 자동 생성되지 않고 있음(1월 22일 이후 중단). 이를 해결하기 위해 DB 레벨의 **Continuous Aggregates**를 도입하여 자동화를 구현해야 함.

### 1.1 아키텍처 결정 (2026-01-28)

**옵션 A 채택**: `RealtimeVerifier` + `VerificationConsumer`로 복구 파이프라인 통합

| 항목 | 기존 (AS-IS) | 변경 후 (TO-BE) |
|------|-------------|----------------|
| 복구 경로 | BackfillManager → DuckDB → merge_worker | VerificationConsumer → TimescaleDB 직접 |
| 저장소 | DuckDB (중간) + TimescaleDB | TimescaleDB only (실시간) |
| DuckDB 역할 | 복구 중간 저장소 | Cold Storage (완결된 틱만 아카이빙) |
| Continuous Agg 연동 | 불가 | 자동 연동 |

**레거시 이동**:
- `src/data_ingestion/recovery/backfill_manager.py` → `legacy/`
- `src/data_ingestion/recovery/merge_worker.py` → `legacy/`
- `src/data_ingestion/recovery/recovery_orchestrator.py` → `legacy/`

---

## 2. 새로운 아키텍처 (TO-BE)

### 2.1 통합 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         통합 복구 파이프라인                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [실시간 수집]                                                              │
│  kis-service / kiwoom-service                                              │
│         │                                                                   │
│         ▼                                                                   │
│  TimescaleDB (market_ticks)                                                │
│         │                                                                   │
│         │◄──────────────────────────────────────┐                          │
│         │                                        │                          │
│         ▼                                        │                          │
│  ┌─────────────────────────────────┐            │                          │
│  │ RealtimeVerifier               │            │                          │
│  │ • 실시간 모드: 매 분 +5초 검증  │            │                          │
│  │ • 배치 모드: 장 마감 후 전체    │            │                          │
│  └─────────────────────────────────┘            │                          │
│         │ Gap 감지                               │                          │
│         ▼                                        │                          │
│  VerificationProducer.produce_recovery_task()   │                          │
│         │ Redis 우선순위 큐                      │                          │
│         ▼                                        │                          │
│  ┌─────────────────────────────────┐            │                          │
│  │ VerificationConsumer            │────────────┘                          │
│  │ ._handle_recovery_task()        │  KIS API → TimescaleDB 직접 저장      │
│  │ .refresh_continuous_aggregate() │  (NEW)                                │
│  └─────────────────────────────────┘                                       │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Continuous Aggregates (자동)                      │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  market_candles_1m_view  →  5m  →  1h  →  1d                        │   │
│  │  source_type = 'TICK_AGGREGATION_UNVERIFIED'                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ DuckDB/Parquet (Cold Storage)                                       │   │
│  │ • 일일 배치: 검증 완료된 틱만 아카이빙                               │   │
│  │ • 용도: 백테스팅, ML 학습, 장기 분석                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 DuckDB 역할 변경

**기존**: 복구 중간 저장소 + 분석용
**변경 후**: **완결된(Verified) 틱 데이터만 장기 보관** (Cold Storage)

```
TimescaleDB (Hot)  →  검증 완료  →  DuckDB/Parquet (Cold)
   (실시간)              ↓              (분석/백테스팅)
                   일일 배치 아카이빙
                   (장 마감 후 16:00)
```

**아카이빙 조건**:
- `source_type IN ('REST_API_KIS', 'REST_API_KIWOOM', 'TICK_AGGREGATION_VERIFIED')`
- 검증 완료 후 7일 경과 데이터

---

## 3. 상세 구현 계획 (Technical Details)

### 3.1 DB 스키마 (TimescaleDB)

**View 분리**: 기존 `market_candles`(API 원본)와 구분하기 위해 `market_candles_1m_view`(틱 집계)를 신규 생성.

**Continuous Aggregates**:
- `market_candles_1m_view`: Ticks → 1m Aggregation
- `market_candles_5m`: 1m View → 5m Aggregation (Cascade)
- `market_candles_1h`: 1m View → 1h Aggregation (Cascade)
- `market_candles_1d`: 1m View → 1d Aggregation (Cascade)

### 3.2 source_type 컬럼 처리 (Ground Truth Policy 준수)

[Ground Truth Policy](../governance/ground_truth_policy.md) 섹션 2.1에 따라 데이터 소스 타입을 명확히 구분한다.

| View/Table | source_type 값 | 설명 |
|------------|---------------|------|
| `market_candles` | `REST_API_KIS`, `REST_API_KIWOOM` | API 원본 (Ground Truth, 1순위) |
| `market_candles_1m_view` | `TICK_AGGREGATION_UNVERIFIED` | 틱 집계 (검증 전, 3순위) |
| `market_candles_1m_view` | `TICK_AGGREGATION_VERIFIED` | 틱 집계 (Volume Check 통과, 2순위) |

**View 정의 시 source_type 매핑**:
```sql
CREATE MATERIALIZED VIEW market_candles_1m_view
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS time,
    symbol,
    '1m' AS interval,
    first(price, time) AS open,
    max(price) AS high,
    min(price) AS low,
    last(price, time) AS close,
    sum(volume) AS volume,
    'TICK_AGGREGATION_UNVERIFIED' AS source_type  -- 기본값: 미검증
FROM market_ticks
GROUP BY time_bucket('1 minute', time), symbol;
```

**검증 승격 로직** (realtime-verifier 연동):
- Volume Check 통과 시 `verification_status` 테이블에 기록
- 서빙 시 JOIN하여 검증 상태 반영

### 3.3 Cascade 의존성 및 자동 Refresh 정책

**Refresh 계층 구조**:
```
market_ticks (원본)
    ↓ [자동: 1분 주기]
market_candles_1m_view
    ↓ [자동: 5분 주기]
market_candles_5m
    ↓ [자동: 1시간 주기]
market_candles_1h
    ↓ [자동: 1일 1회, 장 마감 후]
market_candles_1d
```

**Refresh Policy 설정**:
```sql
-- 1분봉: 장 운영 시간 내 1분 주기 갱신
SELECT add_continuous_aggregate_policy('market_candles_1m_view',
    start_offset => INTERVAL '10 minutes',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute');

-- 5분봉: 5분 주기 갱신
SELECT add_continuous_aggregate_policy('market_candles_5m',
    start_offset => INTERVAL '30 minutes',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes');

-- 1시간봉: 1시간 주기 갱신
SELECT add_continuous_aggregate_policy('market_candles_1h',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

-- 1일봉: 매일 16:00 (장 마감 후) 갱신
SELECT add_continuous_aggregate_policy('market_candles_1d',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day');
```

**모니터링 메트릭** (Architect 권고):
- `cagg_last_refresh_time`: 각 View별 마지막 refresh 시간
- `cagg_refresh_lag_seconds`: 현재 시간 - 마지막 refresh 시간
- Alert 조건: `refresh_lag > 2 * schedule_interval`

### 3.4 VerificationConsumer 수정 (핵심)

**기존 BackfillManager 대체**: `VerificationConsumer._handle_recovery_task()` 확장

**수정 사항**:
1. 복구 데이터 TimescaleDB 직접 저장 (기존 유지)
2. 저장 후 `refresh_continuous_aggregate()` 호출 (NEW)
3. `source_type='REST_API_KIS'` 사용 (Policy 준수)

**구현 코드** (`src/verification/worker.py`):
```python
async def _handle_recovery_task(self, task: VerificationTask) -> VerificationResult:
    """
    긴급 복구 작업 처리 + Continuous Aggregates Refresh

    ISSUE-044: BackfillManager 대체
    """
    symbol = task.symbol
    dt_min = datetime.fromisoformat(task.minute)

    # Phase 1: KIS API 호출 및 TimescaleDB 저장 (기존 로직)
    recovered_count = await self._fetch_and_save_ticks(symbol, dt_min)

    if recovered_count > 0:
        # Phase 2: Continuous Aggregates Refresh (NEW)
        await self._refresh_continuous_aggregates(dt_min, dt_min + timedelta(minutes=1))

    return VerificationResult(...)

async def _refresh_continuous_aggregates(self, start: datetime, end: datetime):
    """
    ISSUE-044: Backfill 후 Continuous Aggregates Refresh
    """
    views = [
        'market_candles_1m_view',
        'market_candles_5m',
        'market_candles_1h',
        'market_candles_1d'
    ]

    for view in views:
        for attempt in range(3):  # 최대 3회 재시도
            try:
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        "CALL refresh_continuous_aggregate($1, $2, $3)",
                        view, start, end
                    )
                logger.info(f"✅ Refreshed {view} for {start} ~ {end}")
                break
            except Exception as e:
                if attempt == 2:
                    logger.error(f"❌ Failed to refresh {view}: {e}")
                    await self._queue_pending_refresh(view, start, end)
                await asyncio.sleep(1)
```

### 3.5 RealtimeVerifier View 활용 (선택)

**기존**: `market_ticks`에서 직접 OHLCV 집계
**권장**: `market_candles_1m_view` 조회로 변경

```python
# 기존 (AS-IS)
async def _get_local_candle_from_db(self, symbol: str, minute: datetime):
    row = await conn.fetchrow("""
        SELECT first(price, time) as open, max(price) as high, ...
        FROM market_ticks  -- 직접 집계
        WHERE symbol = $1 AND time >= $2 AND time < $3
    """, ...)

# 변경 후 (TO-BE) - Optional
async def _get_local_candle_from_db(self, symbol: str, minute: datetime):
    row = await conn.fetchrow("""
        SELECT open, high, low, close, volume
        FROM market_candles_1m_view  -- View 활용
        WHERE symbol = $1 AND time = $2
    """, symbol, minute)
```

### 3.6 에러 핸들링 (Recovery + Refresh)

**시나리오별 처리 방안**:

| 시나리오 | 처리 방안 | 복구 전략 |
|----------|----------|----------|
| 데이터 삽입 성공 + Refresh 성공 | 정상 완료 | - |
| 데이터 삽입 성공 + Refresh 실패 | 재시도 (최대 3회) | 실패 시 `pending_refresh` 큐에 등록 |
| 데이터 삽입 실패 | 트랜잭션 롤백 | Refresh 시도 안 함 |
| Cascade 중간 실패 | 실패 지점부터 재시도 | 하위 View만 stale 상태로 표시 |

**pending_refresh 재처리**:
- Cron Job: 매 10분마다 `pending_refresh` 큐 처리
- 최대 재시도: 10회 (이후 Manual Review 대기열 이동)

---

## 4. 완료 조건 (Acceptance Criteria)

### 4.1 기능 요구사항
- [ ] `market_candles_1m_view`가 생성되고 실시간으로 데이터가 쌓여야 함.
- [ ] `market_candles_5m`, `1h`, `1d` 뷰가 정상적으로 생성되고 조회되어야 함.
- [ ] 과거 데이터 복구 시 `market_candles_1m_view`에도 해당 데이터가 반영되어야 함.
- [ ] 기존 `market_candles` 테이블(API 원본)은 영향을 받지 않아야 함.
- [ ] **BackfillManager, merge_worker가 레거시로 이동되어야 함.** (완료)
- [ ] **VerificationConsumer에 `refresh_continuous_aggregate()` 호출이 추가되어야 함.**

### 4.2 QA 테스트 케이스 (검증 방법)

#### TC-044-01: 실시간 데이터 반영 검증
```sql
-- 1. 테스트 틱 데이터 삽입
INSERT INTO market_ticks (time, symbol, price, volume)
VALUES (NOW(), 'TEST001', 50000, 100);

-- 2. 1분 대기 후 View 반영 확인
SELECT * FROM market_candles_1m_view
WHERE symbol = 'TEST001'
  AND time >= date_trunc('minute', NOW() - INTERVAL '2 minutes');

-- 기대값: 1개 이상의 row 반환, volume >= 100
```

#### TC-044-02: Recovery 후 View 동기화 검증
```sql
-- 1. Recovery 전 row count 기록
SELECT COUNT(*) AS before_count FROM market_candles_1m_view
WHERE time BETWEEN '2026-01-22' AND '2026-01-23';

-- 2. VerificationConsumer recovery task 실행

-- 3. Recovery 후 row count 확인
SELECT COUNT(*) AS after_count FROM market_candles_1m_view
WHERE time BETWEEN '2026-01-22' AND '2026-01-23';

-- 기대값: after_count > before_count (데이터 증가)
```

#### TC-044-03: 기존 테이블 무결성 검증
```sql
-- 1. 작업 전 market_candles 스냅샷
CREATE TEMP TABLE candles_snapshot AS
SELECT COUNT(*) AS cnt, MAX(time) AS max_time
FROM market_candles
WHERE source_type IN ('REST_API_KIS', 'REST_API_KIWOOM');

-- 2. ISSUE-044 작업 수행

-- 3. 작업 후 비교
SELECT
    s.cnt = c.cnt AS count_preserved,
    s.max_time = c.max_time AS max_time_preserved
FROM candles_snapshot s,
     (SELECT COUNT(*) AS cnt, MAX(time) AS max_time
      FROM market_candles
      WHERE source_type IN ('REST_API_KIS', 'REST_API_KIWOOM')) c;

-- 기대값: count_preserved = true, max_time_preserved = true
```

#### TC-044-04: Cascade Refresh 검증
```sql
-- 1분봉 Refresh 후 상위 View 반영 확인
SELECT
    (SELECT MAX(time) FROM market_candles_1m_view) AS t_1m,
    (SELECT MAX(time) FROM market_candles_5m) AS t_5m,
    (SELECT MAX(time) FROM market_candles_1h) AS t_1h;

-- 기대값: t_1m >= t_5m >= t_1h (계층적 갱신)
```

#### TC-044-05: 레거시 모듈 격리 검증
```bash
# 레거시 모듈이 메인 파이프라인에서 import되지 않아야 함
grep -r "from src.data_ingestion.recovery.backfill_manager" src/ --include="*.py" | grep -v legacy
grep -r "from src.data_ingestion.recovery.merge_worker" src/ --include="*.py" | grep -v legacy

# 기대값: 결과 없음 (import 없음)
```

---

## 5. Council of Six 검토 기록

**검토일**: 2026-01-28

### 👔 PM (Project Manager)
> "ISSUE-044는 P1 우선순위로 올바르게 설정되었다. 분봉 데이터 생성이 6일간 중단된 것은 비즈니스 크리티컬 이슈다. 백테스팅과 ML 학습 모두 분봉 데이터에 의존하므로, 이 자동화는 시스템 가용성에 직결된다. **옵션 A(통합)로 아키텍처를 단순화하는 것에 동의한다. DuckDB는 Cold Storage 역할로 전환하여 운영 복잡도를 줄인다.**"

### 🏛️ Architect (설계자)
> "View 분리 전략은 적절하다. **BackfillManager와 merge_worker를 레거시로 이동하고 VerificationConsumer로 통합하면 단일 데이터 경로가 확보된다.** Cascade 집계 방식에서 1m_view → 5m/1h/1d로 이어지는 의존성 체인이 장애 전파 지점이 될 수 있으므로, 각 계층별 마지막 refresh 시간을 모니터링하는 메트릭이 필요하다."

### 🔬 Data Scientist (데이터 사이언티스트)
> "source_type 컬럼 처리 방식이 명확해야 한다. Ground Truth Policy에 따르면 틱 집계 분봉은 `TICK_AGGREGATION_UNVERIFIED`로 시작하고, Volume Check 통과 시 `TICK_AGGREGATION_VERIFIED`로 승격되어야 한다. **DuckDB를 Cold Storage로 전환하여 검증 완료된 데이터만 아카이빙하는 것은 데이터 품질 관점에서 바람직하다.**"

### 🔧 Infra (인프라 엔지니어)
> "refresh policy 설정 시 `start_offset`과 `end_offset` 값이 중요하다. 장 운영 시간(09:00-15:30)에 맞춰 갱신 주기를 최적화해야 한다. **BackfillManager + merge_worker 제거로 컨테이너 복잡도가 감소한다. DuckDB 아카이빙은 일일 배치로 충분하다.**"

### 👨‍💻 Developer (개발자)
> "에러 핸들링과 트랜잭션 경계가 명시되어야 한다. **VerificationConsumer에 `_refresh_continuous_aggregates()` 메서드를 추가하는 것으로 구현 범위가 명확해졌다.** Cascade Refresh 순서도 명확히 해야 한다."

### 🧪 QA Engineer (테스트/품질 엔지니어)
> "구체적인 검증 방법이 필요하다. 실시간 반영 확인, Recovery 후 동기화 확인, 기존 테이블 무결성 검증을 위한 테스트 케이스가 명시되어야 한다. **TC-044-05로 레거시 모듈 격리 검증을 추가한다.**"

**결정**: 옵션 A 채택, 레거시 이동 완료, 구현 진행 승인

---

## 6. 변경 이력

| 날짜 | 변경 내용 | 담당 |
|------|----------|------|
| 2026-01-28 | 초안 작성 | Agent |
| 2026-01-28 | Council of Six 검토 반영 (source_type, 에러 핸들링, QA 테스트) | Agent |
| 2026-01-28 | **옵션 A 채택: RealtimeVerifier + Consumer 통합** | Agent |
| 2026-01-28 | **레거시 이동: BackfillManager, merge_worker, RecoveryOrchestrator** | Agent |

---

## 7. Related
- [ISSUE-043](ISSUE-043.md) (Realtime Verification)
- [RFC-009](../governance/rfc/RFC-009-ground-truth-api-control.md)
- [Ground Truth Policy](../governance/ground_truth_policy.md)
- [Legacy README](../../src/data_ingestion/recovery/legacy/README.md)
