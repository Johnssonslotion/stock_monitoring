# ISSUE-040: API Hub v2 Phase 2 - Real API Integration

**Status**: ✅ Complete
**Priority**: P0
**Created**: 2026-01-23
**Activated From**: DEF-API-HUB-001
**Council Review**: ✅ 만장일치 승인 (2026-01-23)
**Assignee**: Developer Persona

---

## 1. 개요

ISSUE-037에서 완료된 API Hub v2 Phase 1 (Mock Mode)을 기반으로, 실제 KIS/Kiwoom REST API와 연동하는 Phase 2를 구현합니다.

### 핵심 목표
1. **Real API Client 구현**: KISClient, KiwoomClient (BaseAPIClient 상속)
2. **Token Manager 완성**: Redlock 분산 락 추가
3. **Rate Limiter 통합**: redis-gatekeeper와 연동
4. **BackfillManager 전환**: 레거시 직접 호출 → API Hub Queue 기반

---

## 2. Council Review 결과 (2026-01-23)

### 만장일치 승인

| 페르소나 | 결정 | 핵심 의견 |
|---|---|---|
| PM | ✅ | 운영 안정성 및 확장성 핵심 과제 |
| Architect | ✅ | Redlock 분산 락 구현 필수 |
| Data Scientist | ✅ | Ground Truth 데이터 완전성 보장 |
| Infra | ✅ | Dual Redis 구조 적절, 토큰 보안 Phase 3 검토 |
| Developer | ✅ | Redlock 우선 구현, Fixture 기반 테스트 |
| QA | ✅ | 90%+ 테스트 커버리지 DoD |

---

## 3. 구현 계획

### Phase 2-A: 핵심 인프라 (Critical Path)

| 태스크 | 설명 | 상태 |
|---|---|---|
| **2-A-1** | TokenManager Redlock 구현 | ✅ 완료 (14 tests) |
| **2-A-2** | BaseAPIClient + TokenManager 통합 | ✅ 완료 (8 tests) |
| **2-A-3** | Rate Limiter (gatekeeper) 통합 | ⏳ 대기 |

### Phase 2-B: Provider Client 구현

| 태스크 | 설명 | 상태 |
|---|---|---|
| **2-B-1** | KISClient 실제 구현 | ✅ 완료 (Phase 1에서 이미 구현) |
| **2-B-2** | KiwoomClient 실제 구현 | ✅ 완료 (Phase 1에서 이미 구현) |
| **2-B-3** | Fixture 기반 단위 테스트 | ✅ 완료 (8 tests) |

### Phase 2-C: 레거시 전환

| 태스크 | 설명 | 상태 |
|---|---|---|
| **2-C-1** | BackfillManager Queue 전환 | ✅ 완료 (use_hub 옵션) |
| **2-C-2** | APIHubClient 생성 | ✅ 완료 (client.py) |
| **2-C-3** | QueueManager 결과 저장/조회 | ✅ 완료 (set_response, get_response) |

---

## 4. 기술 상세

### 4.1 Redlock 분산 락 (TokenManager)

```python
# 여러 워커가 동시에 토큰 갱신 시도 방지
async def refresh_token_with_lock(self, provider: str):
    lock_key = f"api:token:{provider}:lock"

    # Redlock 획득 (10초 TTL)
    if await self.redis.set(lock_key, "1", nx=True, ex=10):
        try:
            return await self._do_refresh(provider)
        finally:
            await self.redis.delete(lock_key)
    else:
        # 다른 워커가 갱신 중, 대기 후 캐시된 토큰 사용
        await asyncio.sleep(1)
        return await self.get_token(provider)
```

### 4.2 Dual Redis 구조

| Redis | 용도 | DB | Key Pattern |
|---|---|---|---|
| **Main** | Token SSoT + Redlock | 15 | `api:token:{provider}` |
| **Gatekeeper** | Rate Limit | 0 | `api:ratelimit:{provider}:*` |

### 4.3 Ground Truth Policy 준수

- **KIS Rate Limit**: 20 req/s (Ground Truth Policy 섹션 8.1)
- **Kiwoom Rate Limit**: 10 req/s
- **Circuit Breaker**: failure_threshold=5, recovery_timeout=30s

---

## 5. 테스트 전략

### DoD (Definition of Done)
- [ ] Unit Test 커버리지 90%+
- [ ] Fixture 기반 테스트 (실제 API 호출 없음)
- [ ] Circuit Breaker 상태 전이 테스트
- [ ] Redlock 경합 테스트
- [ ] Docker 배포 검증

### 테스트 파일
- `tests/unit/test_api_hub_clients.py`
- `tests/unit/test_token_manager.py`
- `tests/integration/test_api_hub_v2_integration.py`

---

## 6. 관련 문서

- **Spec**: [api_hub_v2_overview.md](../../specs/api_hub_v2_overview.md)
- **BaseAPIClient**: [api_hub_base_client_spec.md](../../specs/api_hub_base_client_spec.md)
- **Token Manager**: [token_manager_spec.md](../../specs/token_manager_spec.md)
- **Idea**: [ID-apihub-integration.md](../../ideas/stock_monitoring/ID-apihub-integration.md)
- **RFC**: [RFC-009](../../governance/rfc/RFC-009-ground-truth-api-control.md)
- **Ground Truth**: [ground_truth_policy.md](../../governance/ground_truth_policy.md)

---

## 7. 변경 이력

| 날짜 | 버전 | 변경 내용 |
|---|---|---|
| 2026-01-23 | 1.0 | DEF-API-HUB-001 활성화, Council 승인 |
| 2026-01-23 | 1.1 | Phase 2-A 완료: Redlock + TokenManager 통합 (74/74 tests) |
| 2026-01-23 | 1.2 | Phase 2-A-3: Rate Limiter (Gatekeeper) 통합 |
| 2026-01-23 | 2.0 | **Phase 2 완료**: BackfillManager Queue 전환, APIHubClient 추가 |
| 2026-01-23 | 2.1 | **Merged to develop**: Tag develop-20260123-0826, Gap Analysis PASS |

---

**Owner**: Developer Persona
**Review Cycle**: Completed
**Merge Tag**: develop-20260123-0826
