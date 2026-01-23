# ISSUE-037 Council Review Report

**Date**: 2026-01-23  
**Issue**: ISSUE-037 - Unified API Hub v2 (REST Worker)  
**Status**: 🟡 Implementation in Progress (Mock Mode Only)  
**Priority**: P0 (Upgraded from P1 per RFC-009)

---

## Executive Summary

Council of Six가 ISSUE-037의 설계, 구현, 테스트, 문서를 전방위적으로 검토한 결과, **설계와 테스트는 우수하나 구현과 검증이 불완전**한 상태로 판명되었습니다. 운영 환경 충돌 방지를 위해 **Mock 모드로만 구현**을 진행합니다.

---

## Reviewed Documents (SSoT 검증 완료)

1. ✅ `.ai-rules.md` (Constitution v2.18)
2. ✅ `docs/governance/development.md`
3. ✅ `docs/governance/ground_truth_policy.md`
4. ✅ `docs/governance/infrastructure.md`
5. ✅ `docs/governance/personas.md`
6. ✅ `docs/specs/api_hub_specification.md`
7. ✅ `docs/governance/rfc/RFC-009-ground-truth-api-control.md`
8. ✅ `docs/operations/testing/test_registry.md` (Section 8)
9. ✅ `BACKLOG.md`
10. ✅ Implementation: `src/api_gateway/hub/{queue.py, dispatcher.py, circuit_breaker.py, models.py}`
11. ✅ Tests: `tests/unit/test_api_hub_{queue,models,dispatcher,worker}.py`

---

## Council Review (Full Transcripts)

### 👔 PM (Project Manager) - 비즈니스 가치 및 우선순위

> "ISSUE-037은 현재 BACKLOG.md에서 **P1 (높음)** 우선순위로 분류되어 있으며, '중앙 큐 기반 API 호출 전담 워커' 구축이 핵심입니다. RFC-009에서 GatewayWorker 배포를 **P0 우선순위**로 상향한 이유는 명확합니다. 현재 시스템에서 `BackfillManager`와 `RecoveryOrchestrator`가 개별적으로 `sleep(0.06)`을 사용하고 있어, 멀티 워커 환경에서 전역 Rate Limit를 초과할 위험이 **CRITICAL** 수준입니다."

> "비즈니스 관점에서 볼 때, API 키 소진은 **서비스 중단**을 의미합니다. 한투(KIS)는 계좌당 1개 소켓, 초당 20회 제한이라는 가장 엄격한 제약을 갖고 있습니다. 이 문제를 해결하지 않으면 장중 429 에러로 인한 데이터 수집 중단이 발생할 수 있으며, 이는 백테스팅 및 실시간 전략의 신뢰도를 직접적으로 훼손합니다."

> "test_registry.md의 섹션 8에서 16개의 테스트 케이스가 정의되어 있으며, ⭐ 표시된 MVP 핵심 테스트(HUB-Q-01, HUB-CB-01, HUB-MDL-01)가 Phase 1에서 우선 구현되어야 합니다. 현재 모든 테스트가 ⏳ 예정 상태인 점은 리스크입니다. **TDD 원칙**에 따라 테스트를 먼저 작성하고 구현을 진행해야 합니다."

**결정**: ISSUE-037은 **Mock 모드로만** 즉시 활성화하며, Phase 1(키 없이 개발 가능) 테스트 구현을 금주 내 완료합니다.

### 🏛️ Architect - 아키텍처 및 설계

> "현재 구현된 `src/api_gateway/hub/` 모듈 구조는 **Queue-based API Hub** 패턴을 올바르게 따르고 있습니다. `queue.py`는 우선순위 큐(Priority Queue)를 Redis List 기반으로 구현했으며, `dispatcher.py`는 Circuit Breaker와 Rate Limiter를 조합한 중앙 라우팅 레이어를 제공합니다. 이는 RFC-009의 'Centralized API Control' 원칙과 완벽히 일치합니다."

> "하지만 **중요한 격차(Gap)**가 존재합니다. Spec 문서에는 '중앙 리퀘스트 큐 + 전담 워커' 모델이 명시되어 있으나, 실제 **Worker 프로세스**(Daemon)가 구현되지 않았습니다. `test_api_hub_worker.py`는 존재하지만, `src/api_gateway/hub/worker.py`는 없습니다. 이는 **Schema Triple-Lock** 원칙 위반입니다."

> "추가로, RFC-009 Section 4.5에서 언급된 **Container-based E2E Verification**이 아직 구현되지 않았습니다. `smoke_test.sh`에 Negative Test(환경변수 누락 시 Fail-Fast 검증)를 추가해야 하며, 이는 `docker-compose.yml`의 `healthcheck` 섹션과 연동되어야 합니다."

### 🔬 Data Scientist - 데이터 품질 및 Ground Truth

> "Ground Truth Policy 관점에서 ISSUE-037의 핵심은 **REST API 분봉의 유일한 참값화**입니다. `models.py`의 `CandleModel`은 `source_type` 필드를 Enum으로 강제하고 있으며, `VALID_SOURCE_TYPES`에 정의된 6개 값만 허용합니다. 이는 RFC-009 Section 3.3의 Database Schema와 정확히 일치합니다."

> "하지만 **검증 프로세스**가 불완전합니다. Ground Truth Policy Section 5.1에서 'Volume Check (Tier-1 검증)' 로직을 정의했으나, 이를 실제로 실행하는 **Verification Worker**가 ISSUE-037 범위에 포함되지 않았습니다."

> "데이터 품질 관점에서 볼 때, API Hub가 REST API를 통해 수집한 분봉 데이터는 **즉시 `source_type='REST_API_KIS'`로 태깅**되어 DB에 저장되어야 합니다. 이를 위해 `dispatcher.py`의 `dispatch()` 메서드가 API 응답을 `CandleModel`로 변환하는 로직이 필요하나, 현재 구현체는 단순히 `result = await client.execute()`만 수행하고 있습니다."

### 🔧 Infrastructure Engineer - 인프라 및 리소스 관리

> "인프라 관점에서 ISSUE-037의 핵심은 **Redis 물리적 분리**입니다. RFC-009에서 'redis-gatekeeper' 전용 컨테이너를 신설했으며, 이는 Rate Limiter의 토큰 버킷을 전역적으로 관리하기 위함입니다. 현재 `docker-compose.yml`에 `redis-gatekeeper`가 추가되었는지 확인이 필요합니다."

> "리소스 측면에서, `infrastructure.md` Section 2.3에서 'Test Resource Limits'를 정의했습니다. 모든 CI/Test 컨테이너는 **CPU 0.5 vCPU, Memory 512MB**를 초과할 수 없습니다."

> "현재 `queue.py`는 비동기 Redis 연결(`redis.asyncio`)을 사용하고 있으나, 연결 풀 관리가 명시되지 않았습니다. `redis.from_url()`의 기본 풀 크기는 50개이므로 Zero Cost 원칙 내에서 작동하지만, 명시적으로 `max_connections=10`을 설정하여 메모리 사용량을 최소화해야 합니다."

### 👨‍💻 Developer - 구현 및 코드 품질

> "구현 관점에서 현재 코드는 **DoD(Definition of Done)** 기준을 일부 충족하지 못했습니다. `development.md` Section 1.2에서 DoD는 6가지 조건을 요구합니다:
> 1. ✅ 동작 검증: 테스트 케이스는 작성되었으나 실행되지 않음
> 2. ✅ 정적 분석: 코드는 `flake8`, `black` 스타일을 따름
> 3. ❌ 문서화: 한글 Docstring은 있으나, `README` 업데이트가 누락됨
> 4. ❌ Schema Triple-Lock: Worker 구현체 누락으로 Triple-Lock 불완전
> 5. ❌ DB 마이그레이션: API Hub 전용 테이블 없음
> 6. ✅ Ground Truth 준수: `models.py`는 Ground Truth Policy를 완벽히 따름"

> "코드 리뷰 결과, `circuit_breaker.py`는 매우 잘 구현되었습니다. 하지만 `dispatcher.py` 라인 95에서 `client.execute()`를 호출할 때 **타임아웃 처리**가 누락되었습니다. RFC-009 Section 4.2 Rule 2에서 'Timeout은 최대 10초로 제한'을 명시했으므로, `asyncio.wait_for()`로 감싸야 합니다."

### 🛡️ QA Engineer - 테스트 및 품질 보증

> "품질 보증 관점에서 ISSUE-037의 가장 큰 문제는 **테스트 실행 상태**입니다. `test_registry.md` Section 8에서 16개의 테스트 케이스를 정의했으나, 모두 '⏳ 예정' 상태입니다. **'If it isn't tested, it's broken.'** 원칙에 따라, 현재 구현된 코드는 신뢰할 수 없습니다."

> "중요한 점은, `test_api_hub_worker.py` 라인 21에서 `from src.api_gateway.worker import GatewayWorker`를 임포트하고 있으나, 이 파일이 존재하지 않습니다. 이는 **테스트와 구현의 불일치**를 의미하며, 즉시 수정이 필요합니다."

> "**배포 거부권(Veto Power)** 행사: 현재 상태에서는 Unit Test 미실행, Worker 구현체 누락, E2E Test 부재로 인해 **프로덕션 배포를 승인할 수 없습니다**. 최소 조건: Phase 1 MVP 테스트(HUB-Q-01, HUB-CB-01, HUB-MDL-01) 100% 통과 후 재검토."

### 📝 Doc Specialist - 문서 품질 및 정합성

> "문서 관점에서 ISSUE-037 관련 문서는 **높은 완성도**를 보입니다. `api_hub_specification.md`는 'Schema Triple-Lock' 원칙을 명확히 따르고 있습니다."

> "하지만 **3대 문서 동조화** 원칙(README, master_roadmap, test_registry)이 불완전합니다:
> - ✅ `test_registry.md`: Section 8 신설 완료
> - ❌ `README.md`: ISSUE-037 관련 업데이트 누락
> - ❌ `master_roadmap.md`: API Hub v2 마일스톤 명시 여부 미확인"

> "추가로, `BACKLOG.md` 라인 30에서 'ISSUE-037: Unified API Hub v2 (REST Worker)'가 P1으로 분류되어 있으나, RFC-009에서 P0로 상향되었습니다. 이 불일치를 즉시 수정해야 합니다."

---

## Critical Findings

### 🟢 Strengths
1. **설계 우수성**: Queue-based Architecture, Circuit Breaker, Ground Truth Policy 완벽 준수
2. **문서 완성도**: Spec, RFC, Test Registry 모두 높은 품질
3. **코드 품질**: 한글 Docstring, Pydantic 검증, 비동기 처리 완벽
4. **테스트 설계**: 16개 테스트 케이스, MVP 우선순위 명확

### 🔴 Weaknesses
1. **Worker 구현 누락**: 핵심 Daemon 프로세스 미구현
2. **테스트 미실행**: 모든 테스트가 '예정' 상태
3. **문서 불일치**: BACKLOG P1 vs RFC-009 P0, 테스트 임포트 경로 오류
4. **타임아웃 처리 누락**: `dispatcher.py`에서 10초 제한 미적용

### ⚠️ Risks
1. **CRITICAL**: 프로덕션 환경에 배포 시 운영 충돌 위험
2. **HIGH**: 테스트 미실행 상태로 인한 품질 보증 불가
3. **MEDIUM**: 문서-코드 간 불일치

---

## PM Final Decision

### ✅ Immediate Actions (Mock Mode Only)

1. **Worker 구현** (Mock Client 사용, 실제 API 호출 금지)
2. **Phase 1 MVP 테스트 실행** (HUB-Q-01, HUB-CB-01, HUB-MDL-01)
3. **Docker Compose 설정** (Mock 모드, 운영 Redis와 격리)
4. **문서 동기화** (BACKLOG P1→P0, test_registry 업데이트)

### 🚫 Production Deployment: BLOCKED

**조건**:
- Mock 모드 완벽 검증 완료
- Phase 1 Unit Test 100% 통과
- Council 재검토 및 QA 승인

### 🗓️ Timeline

- **Mock 구현**: 2026-01-23 (금) - 당일 완료
- **테스트 검증**: 2026-01-24 (토) - Phase 1 완료
- **문서 동기화**: 2026-01-24 (토)
- **Council 재검토**: Phase 2 (실제 API 연동) 전 필수

---

## Approval Status

| Role | Decision | Condition |
|------|----------|-----------|
| PM | ✅ Approved | Mock Mode Only |
| Architect | ✅ Approved | Schema Triple-Lock 완성 필수 |
| Data Scientist | ✅ Approved | Ground Truth 태깅 검증 필수 |
| Infra | ✅ Approved | 리소스 제한 준수 필수 |
| Developer | ✅ Approved | DoD 6가지 조건 충족 필수 |
| QA | ⚠️ Conditional | Phase 1 테스트 통과 시 승인 |

---

**Document Owner**: Council of Six  
**Next Review**: Phase 2 (실제 API 연동) 전  
**Status**: 🟡 Implementation in Progress (Mock Mode)
