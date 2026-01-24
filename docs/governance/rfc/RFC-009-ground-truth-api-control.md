# RFC-009: Data Ground Truth Policy & Centralized API Control

**Status**: 🟢 Approved  
**Created**: 2026-01-22  
**Author**: Council of Six  
**Supersedes**: Partial policies from RFC-007, RFC-008  
**Related**: RFC-007 (Collector Isolation), RFC-008 (Tick Completeness QA), ISSUE-031 (Hybrid Recovery)

---

## 1. Executive Summary

본 RFC는 시스템의 **데이터 참값(Ground Truth) 정책**과 **REST API 중앙 집중식 통제 전략**을 확립합니다. 백테스팅 및 머신러닝 학습 데이터의 신뢰도를 보장하고, 외부 API 호출량 제한으로 인한 시스템 마비를 방지하기 위해 명확한 규칙을 정의합니다.

### 핵심 결정사항
1. **REST API 분봉 = 유일한 참값(Ground Truth)**
2. **모든 REST API 호출은 RedisRateLimiter 경유 필수**
3. ~~GatewayWorker 배포를 P0 우선순위로 상향~~ → **API Hub v2로 대체 완료** ✅

---

## 2. Motivation

### 2.1 문제점 (Current Issues)

#### A. 참값 정책의 모호함
- RFC-008에서 "틱 데이터를 Ground Truth로 간주"하는 조항과 "REST API Volume Check" 전략이 혼재
- `impute_final_candles.py`에서 "Volume이 큰 쪽 선택" 방식 사용 → 일관성 없음
- 백테스팅 시 어떤 데이터를 신뢰해야 할지 불명확

#### B. API 통제의 불완전성
- `BackfillManager`: 개별 `sleep(0.06)` 사용 (전역 제어 없음)
- `RecoveryOrchestrator`: Rate Limiter 미적용
- 일부 검증 워커만 `gatekeeper` 사용 → 멀티 워커 환경에서 429 에러 위험

### 2.2 비즈니스 영향

| 이슈 | 영향 | 심각도 |
|------|------|--------|
| 참값 불명확 | 백테스팅 결과 신뢰도 하락, 법적 리스크 | **HIGH** |
| API 통제 실패 | 프로덕션 키 소진, 서비스 중단 | **CRITICAL** |
| 데이터 일관성 부족 | 전략 개발 효율성 저하 | **MEDIUM** |

---

## 3. Ground Truth Policy

### 3.1 참값 우선순위 (Priority Hierarchy)

```
┌────────────────────────────────────────────────────┐
│ 1️⃣ REST API 분봉 (참값)                            │
│    - KIS: FHKST03010200 (국내 분봉)                │
│    - Kiwoom: ka10080 (국내 분봉)                   │
│    - 거래소 공식 데이터, 법적 효력 있음              │
└────────────────────────────────────────────────────┘
              ↓ (누락 시)
┌────────────────────────────────────────────────────┐
│ 2️⃣ 검증된 틱 집계 분봉                             │
│    - Volume Check 통과 (오차 < 0.1%)               │
│    - 실시간성 중요 시 사용 가능                      │
│    - 일일 검증 필수                                 │
└────────────────────────────────────────────────────┘
              ↓ (검증 실패 시)
┌────────────────────────────────────────────────────┐
│ 3️⃣ Manual Review & 복구                           │
│    - 데이터 누락/불일치 구간                        │
│    - 수동 검증 후 사용                              │
└────────────────────────────────────────────────────┘
```

### 3.2 사용 시나리오별 정책

| 용도 | 사용 데이터 | 근거 |
|------|------------|------|
| **백테스팅** | REST API 분봉 (1순위) | 재현 가능성, 법적 효력 |
| **ML 학습** | REST API 분봉 (1순위) | 모집단 데이터, 완전성 |
| **실시간 알고리즘** | 검증된 틱 집계 (2순위) | 속도 우선, 검증 필수 |
| **품질 리포팅** | REST API 분봉 (1순위) | 감사 대응, 재현 가능 |

### 3.3 Database Schema

#### `market_candles` 테이블 확장
```sql
ALTER TABLE market_candles 
ADD COLUMN source_type VARCHAR(50) DEFAULT 'TICK_AGGREGATION_UNVERIFIED';

-- Enum Values:
-- 'REST_API_KIS'               : KIS REST API 분봉 (참값)
-- 'REST_API_KIWOOM'            : Kiwoom REST API 분봉 (참값)
-- 'TICK_AGGREGATION_VERIFIED'  : Volume Check 통과 (준참값)
-- 'TICK_AGGREGATION_UNVERIFIED': 미검증 틱 집계 (임시)
```

#### 쿼리 예시
```sql
-- 백테스팅용 참값만 조회
SELECT * FROM market_candles 
WHERE source_type IN ('REST_API_KIS', 'REST_API_KIWOOM')
  AND symbol = '005930'
  AND time BETWEEN '2026-01-20 09:00' AND '2026-01-20 15:30';

-- 실시간 알고리즘용 (검증된 데이터만)
SELECT * FROM market_candles 
WHERE source_type IN ('REST_API_KIS', 'TICK_AGGREGATION_VERIFIED')
  AND symbol = '005930'
ORDER BY time DESC LIMIT 100;
```

---

## 4. Centralized API Control

### 4.1 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│          All REST API Requests (KIS/Kiwoom)             │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
        ┌──────────────────────────┐
        │   RedisRateLimiter       │
        │    (gatekeeper)          │
        │  ┌────────────────────┐  │
        │  │ KIS:    20 req/s   │  │
        │  │ KIWOOM: 10 req/s   │  │
        │  └────────────────────┘  │
        └──────────┬───────────────┘
                   │ Token Bucket (Lua Script)
                   ▼
        ┌──────────────────────────┐
        │    External API          │
        │  ┌────────┐  ┌────────┐  │
        │  │  KIS   │  │ Kiwoom │  │
        │  └────────┘  └────────┘  │
        └──────────────────────────┘
```

### 4.2 강제 규칙 (Enforcement Rules)

#### Rule 1: 모든 REST API 호출은 gatekeeper 경유
```python
# ❌ 잘못된 예시 (금지)
async with session.get(kis_url, headers=headers) as resp:
    data = await resp.json()

# ✅ 올바른 예시 (필수)
from src.api_gateway.rate_limiter import gatekeeper

if await gatekeeper.wait_acquire("KIS", timeout=10.0):
    async with session.get(kis_url, headers=headers) as resp:
        data = await resp.json()
else:
    logger.warning("Rate limit timeout, skipping request")
```

#### Rule 2: 타임아웃 처리 필수
```python
# Timeout은 최대 10초로 제한
await gatekeeper.wait_acquire("KIS", timeout=10.0)

# Timeout 발생 시 graceful degradation
if not acquired:
    # 복구 작업 연기, 알림 발송 등
    await queue_for_retry(request)
```

### 4.3 적용 대상 모듈

| 모듈 | 현재 상태 | 비고 |
|------|-----------|------|
| `collector_kis.py` | ✅ 적용 완료 | - |
| `collector_kiwoom.py` | ✅ 적용 완료 | - |
| `BackfillManager` | ✅ 적용 완료 | API Hub v2 Queue 전환 (2026-01-23) |
| `RecoveryOrchestrator` | ✅ 적용 완료 | BackfillManager 경유 (2026-01-22) |
| `impute_final_candles.py` | ✅ 적용 완료 | Ground Truth 우선순위 로직 (2026-01-22) |
| `verification-worker` | ✅ 적용 완료 | API Hub v2 마이그레이션 (2026-01-23) |
| `history-collector` | ✅ 적용 완료 | API Hub v2 마이그레이션 (2026-01-23) |

### 4.4 GatewayWorker → API Hub v2 (Superseded)

> **Note**: 본 섹션의 GatewayWorker 계획은 **API Hub v2**로 대체되었습니다.
> - **ISSUE-037**: API Hub v2 Phase 1 - Mock Mode ✅ Done
> - **ISSUE-040**: API Hub v2 Phase 2 - Real API Integration ✅ Done
> - **ISSUE-041**: API Hub v2 Phase 3 - Container Unification ✅ Done
>
> 참조: [API Hub v2 Overview](../../specs/api_hub_v2_overview.md)

~~현재 `src/api_gateway/worker.py`는 스터브 상태이며 미배포입니다.~~

**현재 상태 (2026-01-23)**:
- API Hub v2가 중앙 집중식 API 통제 역할 수행
- `src/api_gateway/hub/` 디렉토리에 구현 완료
- TokenManager, RateLimiter, CircuitBreaker 통합

### 4.5 Container-based E2E Verification & CI Fail-Fast [UPDATED]
**배경**: 운영 환경의 오설정이 배포 단계에서 검출되지 않아 발생하는 장애를 방지하기 위해 '성공'뿐만 아니라 '의도된 실패'를 CI에서 검증함.

#### A. Self-Diagnosis & Container Health [STRICT]
- **Fail-Fast**: 필수 변수 누락 시 즉시 종료(`Exit 1`)를 넘어서, CI 가상 환경에서 실제 종료 코드(Non-zero)를 검출함.
- **Docker Healthcheck**: `docker-compose.yml`에 전용 헬스체크 도입.
  ```yaml
  healthcheck:
    test: ["CMD", "python", "-c", "import sys; from src.core.health import check; sys.exit(0 if check() else 1)"]
    interval: 30s
    timeout: 10s
    retries: 3
  ```

#### B. CI Negative Smoke Test (Pillar 3 Verification)
- **`smoke_test.sh` 확장**:
  1. **Positive Test**: 정상적인 `.env.prod` 주입 시 30초 이상 가동 확인.
  2. **Negative Test**: 필수 키(`KIS_API_KEY`)를 고의로 제거한 환경에서 컨테이너가 10초 이내에 `Exited (1)` 상태로 전이되는지 검증.
- **CI 차단**: 네거티브 테스트 실패(즉, 설정 오류에도 컨테이너가 죽지 않고 떠 있는 경우) 시 PR 머지를 자동 차단함.

---

## 5. Council Review

### 👔 PM (Project Manager)
> "비즈니스 관점에서 '참값(Ground Truth)'은 백테스팅 결과의 신뢰도를 좌우하는 핵심입니다. REST API 분봉은 거래소 공식 데이터이므로 법적 분쟁이나 감사 시 유일하게 인정받을 수 있는 데이터입니다."

### 🏛️ Architect
> "아키텍처 관점에서 볼 때, 틱 데이터는 '원천(Raw Source)'이고 분봉은 '파생(Derived)'입니다. 그러나 틱 수집 과정에서 누락이 발생할 수 있으므로, REST API 분봉을 '검증 기준(Validation Reference)'으로 삼아 틱 데이터의 완전성을 교차 검증하는 것이 올바른 구조입니다."

### 🔬 Data Scientist
> "통계적 관점에서 REST API 분봉은 '모집단(Population)'에 가깝고, 틱 집계 분봉은 '표본(Sample)'에 가깝습니다. 따라서 머신러닝 학습 데이터나 백테스팅용 최종 데이터셋은 반드시 'REST API 분봉'을 Ground Truth로 사용해야 합니다."

### 🏗️ Infra
> "인프라 관점에서 REST API는 외부 리소스이므로 호출량을 엄격히 통제해야 합니다. 모든 REST API 호출은 반드시 `RedisRateLimiter`를 경유해야 하며, 이를 강제하기 위해 `GatewayWorker` 패턴을 도입하는 것이 필수적입니다."

### 💻 Developer
> "개발자 입장에서 '참값'이 명확하지 않으면 코드 곳곳에서 혼란이 발생합니다. 명확한 우선순위를 정의해야 합니다: 1순위 = REST API 분봉, 2순위 = Volume Check 통과한 틱 집계, 3순위 = Manual Review."

### 🛡️ QA
> "품질 보증 관점에서 '참값'은 재현 가능해야 합니다. REST API는 과거 데이터를 언제든 다시 조회할 수 있으므로 '재현 가능한 참값'입니다. 따라서 최종 검증 및 품질 리포트는 반드시 REST API 기준으로 생성되어야 합니다."

**PM Final Decision**: ✅ **만장일치 승인** (2026-01-22)

---

## 6. Implementation Plan

### Phase 1: 정책 문서화 (Week 1)
- [x] RFC-009 작성 및 승인
- [x] `ground_truth_policy.md` 작성 ✅ 2026-01-22
- [x] `BACKLOG.md` 업데이트 ✅ 2026-01-22

### Phase 2: 코드 수정 (Week 1-2)
- [x] `BackfillManager.fetch_real_ticks()`: gatekeeper 통합 ✅ 2026-01-22
- [x] `RecoveryOrchestrator.run_hybrid_recovery()`: gatekeeper 통합 (via BackfillManager) ✅ 2026-01-22
- [x] `impute_final_candles.py`: 참값 우선순위 로직 적용 ✅ 2026-01-22
- [x] Database Migration: `source_type` 컬럼 추가 (`006_add_source_type_to_candles.sql`) ✅ 2026-01-22

### Phase 3: 인프라 배포 (Week 2)
- [x] Redis 물리적 분리 (별도 컨테이너 `redis-gatekeeper`) ✅ 2026-01-22
- [x] ~~`GatewayWorker` 실제 구현 및 배포~~ → **API Hub v2로 대체** ✅ 2026-01-23
  - ISSUE-037, 040, 041 통해 완료

### Phase 4: 검증 (Week 3-4) [UPDATED 2026-01-23]
**통합 테스트 전략**: Unit → Integration → E2E Container 실구동
**참고**: 본 문서 Section 10 (Council of Six - Testing Strategy Review)

#### Week 3: Unit & Integration Tests
- [ ] **Unit Tests (90% coverage 목표)**
  - [ ] `test_startup_health.py`: RFC-009 Section 4.5 Self-Diagnosis 검증
  - [ ] `test_ground_truth_policy.py`: Section 3.1 참값 우선순위 검증
  - [ ] `test_market_schedule.py`: Section 6.2 Market-Aware Filter 검증
  - [ ] `test_tiered_recovery.py`: 4단계 복구 로직 검증
- [ ] **Integration Tests (Redis/DB 통합)**
  - [ ] `test_gap_recovery_engine.py`: SSH-Worker Gap 탐지 + 복구 통합
  - [ ] `test_api_hub_compliance.py`: Section 4.2 Rate Limit 강제 검증
  - [ ] `test_schema_migration.py`: Section 3.3 source_type 컬럼 검증
- [ ] **CI/CD 통합**: GitHub Actions Workflow 구성

#### Week 4: E2E Container Tests & Chaos Engineering
- [ ] **E2E Tests (docker-compose 기반)**
  - [ ] `test_ssh_worker_startup.py`: Container 재시작 시 자동 복구
  - [ ] `test_market_aware_filter.py`: PRE_MARKET 준비 모드 검증
  - [ ] `test_fail_fast.py`: 환경변수 누락 시 Exit 1 검증
- [ ] **Chaos Tests (고의 장애 주입)**
  - [ ] Multiple Worker Restart with Jitter (Thundering Herd 방지)
  - [ ] Network Failure Recovery (네트워크 단절 → 복구)
  - [ ] Redis Failure Causes Fail-Fast (의존성 장애 감지)
- [ ] **1주일 파일럿 운영** + Ground Truth 정책 검증

---

## 7. Risks & Mitigation

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| **API 한도 초과** | 서비스 중단 | ~~GatewayWorker~~ API Hub v2 배포 | ✅ **Mitigated** |
| **레거시 코드 미발견** | 429 에러 발생 | Grep 검색 + Linter 추가 | ✅ **Mitigated** (Phase 3-B) |
| **DB 마이그레이션 실패** | 데이터 손실 | 백업 선행, Rollback 계획 | ✅ **Mitigated** |

---

## 8. Success Metrics [UPDATED 2026-01-23]

### Compliance Metrics
- [ ] 모든 REST API 호출부에 `gatekeeper` 적용률 = 100%
- [ ] 429 에러 발생률 = 0%
- [ ] 백테스팅 결과 재현율 = 100%
- [ ] Ground Truth 정책 준수율 = 100%

### Test Coverage Metrics (Council Approved)
- [ ] **Unit Tests**: 90% code coverage (Critical Paths 우선)
- [ ] **Integration Tests**: 80% API/DB 통합 검증
- [ ] **E2E Tests**: 5 Critical Paths 통과
  1. Startup Health Check (Section 4.5)
  2. Gap Detection + Recovery (SSH-Worker)
  3. Market-Aware Filter (Section 6.2)
  4. Rate Limit Enforcement (Section 4.2)
  5. Fail-Fast on Configuration Error

### Operational Metrics
- [ ] SSH-Worker Gap Recovery Success Rate >= 95%
- [ ] RFC-009 Compliance Rate (Tier-0 + Tier-1 Recovery) >= 80%
- [ ] Container Startup Health Check Pass Rate = 100%
- [ ] Chaos Test Survival Rate = 100% (모든 장애 시나리오 복구)

---

## 9. References

- [RFC-007: Collector Isolation](RFC-007-collector-isolation.md)
- [RFC-008: Tick Completeness QA](RFC-008-tick-completeness-qa.md)
- [ISSUE-031: Hybrid Recovery](../../ARCHIVE/issues/ISSUE-031.md)
- [SSH-Worker Idea](../../ideas/stock_monitoring/ID-stateful-self-healing-worker.md)
- [ID-hybrid-multi-vendor-validation.md](../../ideas/ID-hybrid-multi-vendor-validation.md)
- [API Hub v2 Overview](../../specs/api_hub_v2_overview.md) [SUPERSEDES GatewayWorker]
- [Ground Truth Policy](../ground_truth_policy.md) [SSoT for Config Values]

> **Note**: RFC-009 Test Strategy는 본 문서 Section 10에 통합되어 있습니다.

---

## 10. Council of Six - Testing Strategy Review [NEW 2026-01-23]

### 검토 대상
**RFC-009 + SSH-Worker 통합 테스트 전략** (Unit → Integration → E2E Container 실구동)

### 👔 PM (Project Manager)
> "이 테스트 전략은 RFC-009의 '100% 준수'와 SSH-Worker의 '자가 치유' 신뢰성을 동시에 검증하는 완벽한 설계다. 특히 Tier 3의 Chaos Engineering은 '실제로 장애가 발생해도 시스템이 스스로 회복하는가?'를 검증하므로 비즈니스 연속성 측면에서 핵심 가치가 있다. Unit 테스트 90% 목표는 야심차지만 달성 가능하며, CI/CD 통합으로 모든 PR에서 자동 검증되는 점이 품질 보증에 탁월하다. E2E 테스트의 'Fail-Fast on Missing Env Var' 시나리오는 운영 사고를 배포 전에 차단하므로 즉시 구현해야 한다. 전체 구조가 Test Pyramid를 정확히 따르고 있어 테스트 실행 시간과 신뢰도의 균형이 우수하다. **승인하며, Week 1부터 Unit Tests 구현을 시작하라.**"

### 🏛️ Architect
> "아키텍처 관점에서 이 테스트 전략은 RFC-009의 계층적 구조를 완벽히 반영하고 있다. 'Startup Health Checker'가 RFC-009 Section 4.5를 검증하는 Unit Test로 명시된 점이 인상적이며, Integration Test의 'API Hub Compliance' 검증은 Rate Limiter의 실제 동작을 검증하므로 아키텍처 무결성을 보장한다. Tiered Recovery의 4단계(TIER-0~3)를 각각 독립적으로 테스트하는 구조는 복구 전략의 각 계층이 올바르게 작동하는지 명확히 검증할 수 있다. E2E의 'Market-Aware Filter' 테스트는 MarketSchedule 유틸리티의 실전 동작을 검증하므로 시스템의 시간 민감성을 보장한다. Chaos Test의 'Multiple Worker Restart with Jitter'는 Thundering Herd Problem 방지를 실증하므로 분산 시스템 안정성의 핵심이다. 단 한 가지 제안: `docker-compose.test.yml`을 실제 운영 환경과 최대한 동일하게 구성하여 'Production-Parity'를 확보하라."

### 🔬 Data Scientist
> "데이터 과학자 입장에서 RFC-009의 Ground Truth Policy를 검증하는 `test_ground_truth_policy.py`는 백테스팅 신뢰도를 보장하는 결정적 테스트다. 'should_use_for_backtesting'이 REST API만 통과시키는 로직을 Unit Test로 검증하므로, 잘못된 데이터 소스가 백테스트에 유입되는 것을 코드 레벨에서 차단한다. Integration Test의 'end_to_end_recovery_flow'가 복구된 데이터의 `source_type = 'REST_API_KIS'`를 DB에서 직접 검증하는 점이 탁월하다. 이는 복구 프로세스가 Ground Truth Policy를 준수하는지 실제 데이터베이스에서 확인하므로 데이터 무결성을 보장한다. Chaos Test의 Recovery Stats Tracking(`compliance_rate` 계산)은 RFC-009 준수율을 정량적으로 측정하므로 데이터 품질 리포팅에 즉시 활용 가능하다. 제안: Recovery Stats를 TimescaleDB에 지속적으로 저장하여 시계열 분석 및 품질 추이 모니터링을 가능하게 하라."

### 🔧 Infrastructure Engineer
> "인프라 관점에서 이 테스트 전략은 운영 안정성을 실전에서 검증하는 완벽한 구성이다. E2E의 'Container Network Failure Recovery' 테스트는 실제 네트워크 파티션 시나리오를 재현하므로 클라우드 환경의 불안정성에 대한 회복력을 검증한다. 'Redis Failure Causes Fail-Fast' 테스트는 의존성 장애 시 침묵의 실패(Silent Failure)를 방지하므로 운영자가 즉시 문제를 인지할 수 있다. GitHub Actions Workflow의 'services' 블록에서 Redis/TimescaleDB를 CI 환경에 프로비저닝하는 구조는 실제 인프라를 모사하므로 테스트 신뢰도가 높다. Chaos Test의 'Multiple Worker Restart'는 Jitter 로직이 실제로 API Hub 부하를 분산하는지 검증하므로 스케일 아웃 시나리오의 안정성을 보장한다. 제안: E2E 테스트 실행 후 리소스 정리(`docker-compose down -v`)를 반드시 수행하여 CI 환경의 디스크/네트워크 리소스 고갈을 방지하라. 이미 Workflow에 포함되어 있어 완벽하다."

### 👨‍💻 Developer
> "개발자로서 이 테스트 구조는 TDD(Test-Driven Development)를 실천하기에 이상적이다. Unit Test의 `test_missing_env_var_fails`는 pytest의 `raises(SystemExit)`를 사용하여 Fail-Fast 동작을 검증하므로, 개발 중 환경변수 누락을 즉시 감지할 수 있다. `conftest.py`의 Shared Fixtures(`mock_redis`, `mock_db`)는 테스트 코드의 중복을 제거하므로 유지보수성이 우수하다. Integration Test가 실제 Redis/DB를 사용하는 점은 Mock의 한계를 극복하므로 실전 동작을 정확히 검증한다. E2E의 `subprocess.run()`을 사용한 Docker 제어는 Python 코드에서 전체 시스템을 오케스트레이션하므로 디버깅이 용이하다. CI Workflow의 Coverage Upload(`codecov`)는 테스트 커버리지를 시각화하므로 미검증 코드를 즉시 파악할 수 있다. 제안: `pytest -m unit` / `-m integration` / `-m e2e` 마커를 사용하여 개발자가 상황에 따라 필요한 테스트만 선택 실행할 수 있도록 하라. 이미 README에 명시되어 있어 완벽하다."

### 🧪 QA Engineer
> "QA 관점에서 이 테스트 전략은 'Shift-Left Testing' 원칙을 완벽히 구현하고 있다. Unit Test의 `test_rate_limiter_config_validation`은 설정 오류를 코드 레벨에서 검증하므로 QA 단계 이전에 결함을 제거한다. Integration Test의 'Rate Limit Enforcement'는 60개 요청 시 최소 2초가 소요되는지 검증하므로, Rate Limiter의 실제 동작을 정량적으로 측정한다. E2E의 'Fail-Fast' 테스트는 `Exited (1)` 상태를 직접 확인하므로, 운영 환경의 설정 오류 시나리오를 완벽히 재현한다. Chaos Test의 네트워크 단절/복구 시나리오는 프로덕션에서 발생 가능한 실제 장애를 시뮬레이션하므로 회귀 테스트(Regression Test)로 지속 실행해야 한다. GitHub Actions의 'Upload Logs on Failure'는 테스트 실패 시 전체 컨테이너 로그를 아티팩트로 저장하므로 실패 원인 분석이 즉시 가능하다. Coverage Goal의 'Critical Paths' 정의는 우선순위 기반 테스트를 가능하게 하므로 QA 리소스를 효율적으로 배분할 수 있다. **승인하며, Unit Tests부터 순차적으로 구현하여 CI에 통합하라.**"

### 📝 Doc Specialist
> "문서화 관점에서 `tests/rfc009/README.md`는 테스트 전략의 완벽한 가이드다. Test Pyramid 다이어그램은 시각적으로 계층 구조를 이해시키므로 신규 개발자의 온보딩 시간을 단축한다. 각 테스트 파일의 Docstring에 RFC-009 Section 번호를 명시한 점은 테스트와 요구사항의 추적성(Traceability)을 보장하므로 감사(Audit) 대응에 유리하다. 'Quick Start' 섹션의 단계별 명령어는 로컬 개발 환경 설정을 5분 이내에 완료할 수 있게 하므로 개발자 경험이 우수하다. 'Maintenance' 섹션의 '테스트 실패 시' 체크리스트는 장애 대응 절차를 표준화하므로 운영 효율성을 높인다. GitHub Actions Workflow의 YAML 코드가 전체 공개되어 있어 CI/CD 파이프라인의 투명성이 완벽하다. 제안: 각 테스트 파일의 상단에 '이 테스트가 실패하면 어떤 영향이 있는가?'를 명시하여 테스트의 비즈니스 가치를 명확히 하라. 예: `# 🚨 Critical: 이 테스트 실패 시 운영 환경에서 Silent Failure 발생 가능`."

### PM의 최종 결정
> "Council 전원의 만장일치 승인 및 각 페르소나의 건설적 제안을 바탕으로, **RFC-009 + SSH-Worker 통합 테스트 전략**을 공식 승인한다. 이 테스트 전략은 RFC-009의 '100% 강제 준수'를 코드 레벨에서 검증하며, SSH-Worker의 '자가 치유' 신뢰성을 실전 시나리오로 입증한다. 특히 Tier 3의 Chaos Engineering은 프로덕션 장애 대응 능력을 사전 검증하므로 비즈니스 연속성의 핵심 자산이다. 즉시 다음 단계를 실행하라:
> 
> 1. **Week 1**: Unit Tests 구현 (목표: 90% coverage)
> 2. **Week 2**: Integration Tests 구현 + CI 통합
> 3. **Week 3**: E2E Tests 구현 (docker-compose.test.yml 포함)
> 4. **Week 4**: Chaos Tests 구현 + 전체 테스트 스위트 검증
> 
> 이 테스트 전략은 RFC-009 Section 6 'Implementation Plan - Phase 4: 검증'에 공식 포함되며, 모든 PR은 최소한 Unit Tests 통과를 필수 조건으로 한다. **승인 완료. 즉시 구현 착수하라.**"

---

**Status Update**: ✅ Approved by Council of Six (2026-01-22)
**Testing Strategy Approved**: ✅ Council Review Completed (2026-01-23)
**API Hub v2 Integration**: ✅ Phase 1-3 완료 (ISSUE-037, 040, 041) - GatewayWorker 대체
**Document Sync**: ✅ Ground Truth Policy 기준 동기화 (2026-01-23)
**Next Steps**: Phase 4 실행 (Unit Tests → Integration → E2E Container 실구동)
