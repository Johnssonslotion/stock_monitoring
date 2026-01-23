# IDEA: API Hub Centralized Integration & Real-time Recovery

**Status**: 🌳 Growing (Active Development)
**Priority**: P0
**Council Review**: ✅ 만장일치 승인 (2026-01-23)
**Activated From**: DEF-API-HUB-001 → ISSUE-040

## 1. 개요 (Abstract)
현재 파편화되어 있는 KIS/Kiwoom API 호출 로직(BackfillManager, Collectors 등)을 새롭게 구축된 **API Hub (RestApiWorker)**로 일원화하고, 이를 통해 데이터 정합성(Ground Truth)을 보장하는 실시간 복구 체계를 구축합니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: 모든 REST API 요청을 단일 통로(API Hub)로 제어하면 Rate Limit 위반을 원천 차단하고, 토큰 관리를 중앙 집중화할 수 있다.
- **기대 효과**:
    - **안정성**: KIS 1초 5건/20건 제한을 전역적으로 관리 가능.
    - **일관성**: 모든 복구 데이터가 동일한 정규화 로직을 거쳐 DuckDB에 적재됨.
    - **자동화**: Sentinel이 감지한 즉시 복구 태스크를 발행하여 데이터 공백 최소화.

### 3.2 KIS 분당 호출 제한(EGW00133) 전략 (Dual Redis Sync)
- **Risk**: 여러 워커가 동시에 토큰 갱신을 시도할 경우 1분 제한에 걸려 전체 시스템 마비 가능.
- **물리적 역할 분담**:
    1. **Main Redis (`REDIS_URL`)**: 토큰(SSoT) 저장 및 **분산 락(Redlock)** 수행. 
        - 갱신 전 락 획득 필수. 락 소유자만 API 호출. 나머지 워커는 Redis의 캐시된 토큰 사용.
    2. **Gatekeeper Redis (`REDIS_URL_GATEKEEPER`)**: 초당 호출 제한(Rate Limit) 전용.
        - 모든 채널(REST/WS)의 사용량을 합산하여 원천 차단.

### 3.3 WS vs REST 키 정수기 (Shared Secret Governance)
- **문제**: 단일 API 키로 WebSocket과 REST를 동시 사용 시 세션 끊김 현상 발생 가능.
- **전략**: `gatekeeper`의 설정을 통합(`api:ratelimit:total`)하여, WS 점유량과 REST 요청량을 단일 버킷에서 관리.

## 4. 기존 RFC 정합성 검토 결과 (Alignment Summary)
- [rfc_alignment_report.md](../../../.gemini/antigravity/brain/a358d432-76aa-4efb-a908-366ba34647d0/rfc_alignment_report.md)

### 4.1 주요 정합성 포인트
- **Mandatory Hub**: RFC-009의 Library형 Gatekeeper 방식을 API Hub 서비스형 강제 호출 방식으로 승격 제안.
- **Dual Redis Logic**: `main-redis`는 분산 락(분당 호출), `gatekeeper-redis`는 정격 제어(초당 호출)로 물리적 분할 최적화.
- **Token Consistency**: Redlock 도입으로 KIS의 1분당 토큰 갱신 경합 문제 해결.

## 5. 후속 작업 (Next Action)
- [ ] **RFC-009 Revised Draft**: API Hub 강제화 조항 추가 및 승인 절차.
- [ ] **TokenManager Update**: 분산 락 적용 및 KIS 분당 제한 회피 로직 구현.
- [ ] **Backfill Integration**: 레거시 호출부의 메시지 큐 전환.

## 4. 로드맵 연동 시나리오
- **Pillar 2 (Data Ingestion)**: [master_roadmap.md](../../strategy/master_roadmap.md) 수집 안정성 고도화 항목에 포함.
- **Pillar 3 (System Reliability)**: Self-healing(자동 복구) 체계의 핵심 모듈로 작동.
