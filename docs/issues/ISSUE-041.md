# ISSUE-041: API Hub v2 Phase 3 - 운영 배포 및 Container Unification

**Status**: 🔄 In Progress
**Priority**: P0
**Created**: 2026-01-23
**Branch**: `feat/api-hub-unification`
**Assignee**: Developer Persona

---

## 1. 개요

ISSUE-040(Phase 2)에서 구현된 API Hub v2의 실제 연동 기능을 기반으로, 운영 환경 배포를 위한 최종 검증 및 모니터링 체계를 구축하고, **REST API를 호출하는 모든 컨테이너를 API Hub Queue로 일원화**합니다.

### 핵심 목표
1. **운영 배포 검증**: Docker, 환경 변수, 헬스체크 설정 완비
2. **리얼 API 연동 확인**: 증권사 샌드박스 환경에서의 E2E 테스트 성공
3. **모니터링 강화**: Redlock 경합 및 Rate Limiter 거부 상황에 대한 가시성 확보
4. **Container Unification**: REST API 호출 컨테이너를 API Hub Queue로 통합

---

## 2. 세부 설계 및 작업 목록

### 2.1 운영 배포 검증 (Infra)
- `docker-compose.yml` 내 `gateway-worker-real` 서비스 설정 최종화
- `.env.prod` 내 관련 환경 변수 보안 및 누락 여부 점검

### 2.2 샌드박스 통합 테스트 (QA)
- `tests/integration/test_real_api_sandbox.py` 작성
- 실제 통신을 통한 토큰 갱신 및 데이터 수신 확인

### 2.3 모니터링 구현 (Dev)
- `token_manager.py`: Redlock 경합 발생 시 로그 기록 및 카운터 증가
- `dispatcher.py`: Rate Limit 거부 시 상세 사유 로깅 및 Sentinel 연동 준비

### 2.4 Container Unification (New)

**목표**: REST API를 호출하는 컨테이너들을 API Hub Queue로 일원화

#### 통합 대상

##### ✅ 유지 (WebSocket 전용)
- `kis-service` - KIS WebSocket 실시간 수집
- `kiwoom-service` - Kiwoom WebSocket 실시간 수집

##### 🔄 통합 대상 (REST API 호출)
1. **recovery-worker** - `BackfillManager` (틱 데이터 복구)
   - ✅ ISSUE-040에서 이미 Queue 전환 완료 (`use_hub=True`)
   - 📝 TODO: Docker compose 의존성 명시

2. **verification-worker** - 데이터 검증 및 복구
   - **현재 API 호출**:
     - KIS: 분봉 데이터 조회 (`FHKST01010400`)
     - Kiwoom: 분봉 데이터 조회 (`KIS_CL_PBC_04020`)
     - KIS: 틱 데이터 복구 (`FHKST01010300`)
   - **마이그레이션**: API 호출을 API Hub Queue로 전환

3. **history-collector** - 과거 데이터 수집
   - **현재 API 호출**: KIS 분봉/일봉 히스토리 조회
   - **마이그레이션**: API 호출을 API Hub Queue로 전환

#### 마이그레이션 전략

**Phase 3-A: verification-worker 마이그레이션**
```python
# Before
class KISAPIClient:
    async def fetch_minute_candle(self, session, symbol, target):
        token = await self.get_token(session)
        async with session.get(url, headers=...) as resp:
            ...

# After
class VerificationConsumer:
    def __init__(self):
        self.hub_client = APIHubClient()
    
    async def _process_task(self, session, task):
        result = await self.hub_client.execute(
            provider="KIS",
            tr_id="FHKST01010400",
            params={"symbol": symbol, ...},
            timeout=10.0
        )
```

**작업 내용**:
- `KISAPIClient`, `KiwoomAPIClient` 클래스 제거
- Token Manager 제거 (API Hub가 관리)
- Rate Limiter 제거 (API Hub가 관리)
- API 호출을 `hub_client.execute()`로 전환

**Phase 3-B: history-collector 마이그레이션**
```python
# Before
class HistoryCollector:
    def __init__(self):
        self.auth_manager = KISAuthManager()

# After
class HistoryCollector:
    def __init__(self):
        self.hub_client = APIHubClient()
```

**작업 내용**:
- KIS Auth Manager 제거
- REST API 호출을 API Hub Queue로 전환

**Phase 3-C: Docker Compose 업데이트**
```yaml
recovery-worker:
  depends_on:
    - gateway-worker-real  # 추가

verification-worker:
  depends_on:
    - gateway-worker-real  # 추가

history-collector:
  depends_on:
    - gateway-worker-real  # 추가
```

#### 기대 효과
- ✅ **Rate Limit 통합 관리**: 단일 gatekeeper로 모든 API 조율
- ✅ **Token 관리 통합**: TokenManager 한 곳에서만 관리
- ✅ **유지보수성 향상**: API Client 코드 중복 제거 (~200 lines)
- ✅ **모니터링 개선**: 모든 API 호출이 API Hub 통과 → 중앙 로깅

#### Risk & Mitigation
- **Single Point of Failure**: API Hub Worker 장애 시 전체 영향
  - **Mitigation**: restart policy + Health Check 강화

---

## 3. DoD (Definition of Done)

### Phase 3-A: 운영 배포 및 모니터링
- [ ] 샌드박스 환경 테스트 100% 통과
- [ ] 운영 프로파일 배포 후 10분 이상 안정적 구동 확인
- [ ] Redlock/RateLimit 로그가 표준 포맷에 따라 생성됨

### Phase 3-B: Container Unification
- [ ] `verification-worker` API Hub Queue 전환 완료
- [ ] `history-collector` API Hub Queue 전환 완료
- [ ] Docker compose 파일 업데이트 (의존성 추가)
- [ ] Unit Test 90%+ 커버리지
- [ ] Integration Test 통과

### 최종
- [ ] 갭 분석(Gap Analysis) 통과
- [ ] BACKLOG 업데이트

---

## 4. 관련 문서
- [implementation_plan.md](../../.gemini/antigravity/brain/a2dfdc21-d4e6-471e-b8b2-510fab073ce6/implementation_plan.md)
- [api_hub_v2_overview.md](../specs/api_hub_v2_overview.md)
- **ISSUE-040**: API Hub v2 Phase 2 - Real API Integration
- **RFC-009**: Ground Truth & API Control Policy

---

## 5. 일정 (Container Unification)

| Phase | 작업 | 예상 소요 | 상태 |
|-------|------|----------|------|
| 3-A-1 | verification-worker 마이그레이션 | 4 hours | 🔄 In Progress |
| 3-A-2 | history-collector 마이그레이션 | 3 hours | ⏳ Pending |
| 3-A-3 | Docker compose 업데이트 | 1 hour | ⏳ Pending |
| 3-B | 테스트 작성 및 검증 | 3 hours | ⏳ Pending |
| 3-C | 문서화 | 2 hours | ⏳ Pending |
| **Total** | | **13 hours** | **~2 days** |
