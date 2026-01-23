# ISSUE-037 Council Review - Phase 2 Approval Request

**Date**: 2026-01-23  
**Session**: Council of Six - Phase 1 Completion Review  
**Decision Type**: Phase 2 Conditional Approval  

---

## Executive Summary

**Phase 1 Status**: ✅ **APPROVED & PRODUCTION-READY**

**Phase 2 Status**: 🚧 **CONDITIONAL APPROVAL** (5 선행 작업 필요)

Phase 1 Mock Mode가 모든 기술적 요구사항을 충족했으며, Docker 배포 테스트도 성공적으로 완료되었습니다. 그러나 Phase 2 (실제 API 연동)는 시스템 복잡도, Rate Limit 리스크, BackfillManager 중복 호출 등 여러 위험 요소가 있어, 5개의 선행 작업 완료 후에만 시작할 수 있습니다.

---

## Review Context

### 검토 대상
- **이슈**: ISSUE-037 Unified API Hub v2 (REST Worker)
- **범위**: Phase 1 완료 검증 및 Phase 2 진행 승인 요청
- **Trigger**: Architecture changes affecting multiple components

### Phase 1 달성 사항
- ✅ 구현: RestApiWorker, QueueManager, TaskDispatcher, CircuitBreaker, Models (5개 컴포넌트)
- ✅ 테스트: 29/29 Pass (100% 커버리지)
- ✅ 배포: Docker 환경 검증 완료 (메모리 25MB/512MB, CPU 0.07%)
- ✅ 문서: Council Review + Deployment Test 리포트 작성 완료

### Phase 2 요청 사항
- KISClient, KiwoomClient 실제 REST API 연동
- Token Manager 구현 (Redis SSoT)
- RedisRateLimiter 통합 (gatekeeper)
- BackfillManager 호환성 검증

---

## Council of Six - 페르소나 협의

### 👔 PM (Project Manager)

> "Phase 1 Mock Mode 구현이 우리의 모든 목표를 달성했습니다. 29/29 테스트 통과, 리소스 사용량 5% 미만, Docker 배포 성공적으로 완료되었으며 이는 팀의 훌륭한 엔지니어링 역량을 보여줍니다. 하지만 Phase 2는 신중하게 접근해야 합니다. 실제 API 연동은 KIS와 Kiwoom의 Rate Limit 정책에 직접 영향을 받으며, 한 번의 실수로 계정이 차단될 수 있습니다. 제 판단으로는 Phase 2 진행 전에 반드시 다음을 확보해야 합니다: (1) Token Manager의 완전한 설계 문서, (2) Rate Limiter 통합 테스트 계획, (3) API 호출 실패 시 Fallback 전략. 이 세 가지가 준비되면 Phase 2를 조건부 승인하겠습니다."

### 🏛️ Architect

> "Phase 1의 아키텍처는 매우 견고합니다. Queue-based design, Circuit Breaker, Priority Queue 모두 production-grade 품질입니다. 하지만 Phase 2로 가면 시스템의 복잡도가 기하급수적으로 증가합니다. Token Manager는 단순한 Redis 저장소가 아니라 Token Refresh, Expiry Handling, Multi-Account Support를 모두 고려해야 하는 Critical Component입니다. 제가 우려하는 것은 BackfillManager와의 통합입니다. 현재 BackfillManager는 자체적으로 KIS/Kiwoom API를 호출하는데, Hub v2와 중복 호출이 발생하면 Rate Limit을 초과할 위험이 있습니다. 따라서 Phase 2 전에 BackfillManager를 Hub v2의 Queue 시스템으로 마이그레이션하는 작업이 선행되어야 합니다. 이는 최소 2-3일의 추가 작업이 필요합니다."

### 📊 Data Scientist

> "Ground Truth Policy 관점에서 Phase 1은 완벽합니다. CandleModel과 TickModel에 source_type 필드가 정확히 구현되어 있고, 테스트도 통과했습니다. Phase 2에서 가장 중요한 것은 실제 API 응답 데이터를 어떻게 CandleModel로 변환하는지입니다. KIS의 FHKST01010100 응답과 Kiwoom의 opt10081 응답은 필드명과 데이터 타입이 완전히 다릅니다. 이 변환 로직에서 실수하면 Ground Truth가 오염됩니다. 제 요구사항은 명확합니다: Phase 2 시작 전에 KIS와 Kiwoom의 실제 API 응답 샘플을 `tests/fixtures/api_responses/`에 저장하고, 이를 기반으로 변환 로직 테스트를 먼저 작성해야 합니다. TDD 없이 Phase 2를 시작하는 것은 받아들일 수 없습니다."

### 🔧 Infrastructure Engineer

> "Docker 배포 테스트 결과는 인상적입니다. 메모리 25MB, CPU 0.07%는 Zero-Cost 원칙을 완벽하게 준수합니다. Redis DB 15 격리도 잘 작동하고 있습니다. 하지만 Phase 2에서 우려되는 것은 redis-gatekeeper 통합입니다. 현재 gatekeeper는 초당 요청 수를 제한하는데, Hub v2 Worker가 여러 개 실행되면 각 Worker가 독립적으로 토큰을 소비하게 됩니다. 이를 조율하지 않으면 전체 시스템의 Rate Limit을 초과할 수 있습니다. 또한 Token Manager가 Redis에 저장하는 토큰의 보안도 고려해야 합니다. 현재 Redis는 암호화 없이 평문으로 데이터를 저장하므로, API Token이 노출될 위험이 있습니다. 제 권고사항은 Phase 2 전에 redis-gatekeeper와의 통합 테스트를 먼저 완료하고, 필요하면 Token 암호화 로직을 추가하는 것입니다."

### 💻 Developer

> "코드 품질 관점에서 Phase 1은 모범 사례입니다. 한글 Docstring, Pydantic 검증, asyncio 패턴 모두 완벽합니다. 하지만 Phase 2를 시작하면 코드 복잡도가 2배 이상 증가합니다. KISClient와 KiwoomClient는 각각 인증 로직, 요청 헤더 구성, 응답 파싱이 필요한데, 이들 간에 공통 로직을 어떻게 추상화할지가 관건입니다. 제가 제안하는 것은 `BaseAPIClient` 추상 클래스를 먼저 설계하고, 여기에 공통 메서드(`_build_headers`, `_handle_response`, `_handle_error`)를 정의하는 것입니다. 또한 timeout 처리가 누락되어 있는데, API 응답이 10초 이상 지연되면 Worker가 멈출 수 있습니다. `asyncio.wait_for(timeout=10)`를 반드시 추가해야 합니다. Phase 2 시작 전에 BaseAPIClient 설계를 먼저 리뷰하고 싶습니다."

### 🧪 QA Engineer

> "Phase 1의 테스트 커버리지는 훌륭합니다. 29/29 통과는 팀의 TDD 원칙을 잘 따른 결과입니다. 하지만 Phase 2는 완전히 다른 차원입니다. 실제 API를 호출하면 테스트가 비결정적(non-deterministic)이 되고, 외부 의존성 때문에 테스트가 실패할 수 있습니다. 제가 요구하는 것은 명확합니다: Phase 2에서는 **실제 API 호출 테스트를 절대 하지 말고**, 모든 테스트는 Mock이나 Fixture를 사용해야 합니다. 또한 `tests/integration/` 디렉토리에 별도의 통합 테스트를 추가하되, 이는 CI에서 자동 실행되지 않고 수동으로만 실행되어야 합니다. Phase 1에서 QA 조건부 승인을 했던 이유는 테스트 통과를 확인하기 위함이었고, 이제 그 조건이 충족되었습니다. 하지만 Phase 2는 다시 조건부 승인으로 돌아갑니다: Mock 기반 테스트 계획이 먼저 승인되어야 Phase 2를 시작할 수 있습니다."

---

## PM의 최종 결정

### ⚖️ Decision: **조건부 승인 (Conditional Approval)**

Phase 1 Mock Mode가 성공적으로 완료되었으며, 모든 기술적 요구사항을 충족했습니다. Council의 의견을 종합한 결과, Phase 2로 바로 진행하는 것은 리스크가 너무 크다고 판단합니다.

### ✅ Phase 1 최종 승인
- ✅ Mock Mode 구현 완료 인정
- ✅ Production 배포 승인 (Mock Mode만 해당)
- ✅ BACKLOG.md에서 ISSUE-037 상태를 "Phase 1 Complete" 로 변경

### 🚧 Phase 2 진행 조건 (5개 선행 작업 필수)

Phase 2는 다음 5개 작업이 **모두 완료**되어야만 시작할 수 있습니다:

| # | 작업 | 담당 | 기한 | 요구자 |
|---|------|------|------|--------|
| 1 | **BaseAPIClient 설계 문서** | Developer | 1일 | Developer |
| 2 | **API 응답 Fixture 수집** | Developer | 1일 | Data Scientist |
| 3 | **Token Manager 설계 문서** | Architect | 1일 | PM, Architect |
| 4 | **RedisRateLimiter 통합 테스트 계획** | Infrastructure | 1일 | PM, Infra |
| 5 | **Phase 2 Mock 기반 테스트 계획** | QA | 1일 | QA |

#### 1. BaseAPIClient 설계 문서 (Developer 요구)
**파일**: `docs/specs/api_hub_base_client_spec.md`

**필수 내용**:
- 공통 인터페이스 정의 (Abstract Base Class)
- `_build_headers(provider, tr_id)` - 헤더 구성
- `_handle_response(response)` - 응답 파싱 및 에러 처리
- `_handle_error(exception)` - 예외 처리 및 로깅
- timeout 처리: `asyncio.wait_for(timeout=10)` 패턴
- KISClient, KiwoomClient 구현 예시

**검증 기준**: Architect + Developer 리뷰 통과

---

#### 2. API 응답 Fixture 수집 (Data Scientist 요구)
**디렉토리**: `tests/fixtures/api_responses/`

**필수 파일**:
- `kis_candle_response.json` - KIS FHKST01010100 실제 응답 (민감정보 제거)
- `kiwoom_candle_response.json` - Kiwoom opt10081 실제 응답
- `README.md` - Fixture 갱신 방법 및 주의사항

**수집 방법**:
1. 실제 API 호출 (개발 계정 사용)
2. 응답 JSON에서 민감정보 제거 (계좌번호, 실명 등)
3. `source_type` 필드가 변환 가능한지 확인

**검증 기준**: Data Scientist 리뷰 통과

---

#### 3. Token Manager 설계 문서 (PM & Architect 요구)
**파일**: `docs/specs/token_manager_spec.md`

**필수 내용**:
- Redis SSoT 스키마 설계
  - Key: `api:token:kis`, `api:token:kiwoom`
  - Value: JSON `{"access_token": "...", "expires_at": 1234567890}`
- Token Refresh 로직
  - 만료 5분 전 자동 갱신
  - 갱신 실패 시 재시도 (3회)
- Expiry Handling
  - TTL 설정 (Redis EXPIRE)
  - 만료된 토큰 자동 삭제
- Multi-Account Support (Optional)
  - Key: `api:token:kis:{account_id}`

**검증 기준**: PM + Architect 리뷰 통과

---

#### 4. RedisRateLimiter 통합 테스트 계획 (PM & Infra 요구)
**파일**: `docs/specs/rate_limiter_integration_plan.md`

**필수 내용**:
- gatekeeper와의 통합 방식
  - Hub v2 Worker가 gatekeeper를 어떻게 호출하는지
  - Token 획득 실패 시 대기 로직 (backoff)
- Multi-Worker 환경 토큰 조율
  - 여러 Worker가 동시에 실행될 때 Rate Limit 초과 방지
  - gatekeeper가 전체 시스템의 요청 수를 추적하는지 확인
- Token 보안
  - Redis에 평문 저장 vs 암호화
  - 암호화 선택 시 구현 방법 (Fernet, AES)

**검증 기준**: Infra + PM 리뷰 통과

---

#### 5. Phase 2 Mock 기반 테스트 계획 (QA 요구)
**파일**: `docs/specs/phase2_test_plan.md`

**필수 내용**:
- 실제 API 호출 금지 원칙
  - 모든 테스트는 Fixture 기반
  - `httpx.AsyncClient`를 Mock으로 대체
- `tests/integration/` 디렉토리 구조
  ```
  tests/integration/
  ├── test_api_hub_kis_client.py     (Fixture 기반)
  ├── test_api_hub_kiwoom_client.py  (Fixture 기반)
  └── test_api_hub_real_call.py      (수동 실행 전용, CI 제외)
  ```
- CI 제외 방법
  - `pytest.mark.manual` 데코레이터
  - `pytest -m "not manual"` 명령어로 CI 실행
- 수동 실행 가이드
  - 개발자가 로컬에서 실제 API 테스트할 때만 사용
  - `.env` 설정 필요 (KIS/Kiwoom API Key)

**검증 기준**: QA 리뷰 통과

---

### 📅 타임라인

| Date | Task |
|------|------|
| 2026-01-24 ~ 2026-01-28 | 5개 선행 작업 완료 (병렬 수행 가능) |
| 2026-01-29 | Council 재검토 (선행 작업 검증) |
| 2026-01-30 이후 | Phase 2 시작 (조건 충족 시) |

### 🚨 추가 제약사항

**BackfillManager 마이그레이션 강력 권고** (Architect 의견)

현재 BackfillManager는 자체적으로 KIS/Kiwoom API를 직접 호출합니다. Phase 2에서 Hub v2도 동일한 API를 호출하면:
- ❌ Rate Limit 중복 소비
- ❌ gatekeeper 토큰 경합
- ❌ 계정 차단 위험

**해결 방법**:
1. **권장**: BackfillManager를 Hub v2 Queue 시스템으로 마이그레이션
   - BackfillManager가 직접 API를 호출하지 않고, Hub v2 Queue에 태스크를 push
   - 모든 API 호출이 Hub v2 Worker를 통해 단일화
   - 작업 기간: 2-3일
2. **차선**: BackfillManager와 Hub v2가 동일한 gatekeeper를 공유
   - 두 시스템이 같은 Redis Rate Limiter를 사용
   - 하지만 여전히 조율 문제 발생 가능

**PM 판단**: 차선책도 허용하되, 권장 방법을 우선 검토

---

### 🎯 즉시 실행 가능한 작업

Phase 2 준비 없이 바로 할 수 있는 작업:
- ✅ Mock 모드로 운영 환경 배포 테스트 (추가 검증)
- ✅ 다른 P0/P1 이슈 작업 (BACKLOG.md 참조)
- ✅ Phase 1 문서화 완성
- ✅ Mock 모드 성능 모니터링 (1주일 관찰)

---

## Approval Status

| Role | Phase 1 | Phase 2 | Condition |
|------|---------|---------|-----------|
| **PM** | ✅ Approved | 🚧 Conditional | 5개 선행 작업 완료 필요 |
| **Architect** | ✅ Approved | 🚧 Conditional | BaseAPIClient + Token Manager 설계 필수 |
| **Data Scientist** | ✅ Approved | 🚧 Conditional | API Fixture 수집 + TDD 필수 |
| **Infrastructure** | ✅ Approved | 🚧 Conditional | Rate Limiter 통합 테스트 필수 |
| **Developer** | ✅ Approved | 🚧 Conditional | BaseAPIClient 설계 문서 필수 |
| **QA** | ✅ Approved | 🚧 Conditional | Mock 기반 테스트 계획 필수 |

---

## Next Actions

### Immediate (오늘 가능)
1. BACKLOG.md 업데이트: ISSUE-037 상태를 "Phase 1 Complete, Phase 2 Pending" 로 변경
2. 5개 선행 작업을 BACKLOG에 신규 Sub-task로 등록
3. 각 담당자에게 작업 할당 (현실: AI가 모두 수행)

### Short-term (1-5일)
4. 5개 선행 작업 병렬 수행
5. 각 작업 완료 시 해당 페르소나 리뷰

### Mid-term (6-10일)
6. Council 재검토 (2026-01-29)
7. Phase 2 시작 승인
8. KISClient, KiwoomClient 구현

---

**Document Owner**: Council of Six  
**Next Review**: 2026-01-29 (선행 작업 검증)  
**Status**: 🟢 Phase 1 Approved, 🚧 Phase 2 Conditional Approval  
**Last Updated**: 2026-01-23
