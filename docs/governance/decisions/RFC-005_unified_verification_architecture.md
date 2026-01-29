# RFC-005: Unified Verification Architecture

**Status**: 🟢 Accepted (Council Approved)
**Date**: 2026-01-29
**Author**: Developer Persona
**Reviewers**: Council of Six

## 1. Context (Problem)
현재 검증 시스템은 두 가지 컴포넌트로 파편화되어 있습니다.
1.  `VerificationWorker` (ISSUE-044): Queue 기반으로 장 마감 후 KIS-Kiwoom 간의 API 교차 검증을 수행.
2.  `RealtimeVerifier` (ISSUE-043): Interval 루프 기반으로 장 중 DB-API 간의 데이터 정합성을 검증.

이로 인해 유지보수 비용이 이중으로 발생하며, "DB vs API 비교"라는 핵심 로직이 `RealtimeVerifier`에만 존재하여 장 마감 후 전수 검증(Batch)에 활용되지 못하는 한계가 있었습니다.

## 2. Decision (Solution)
**"VerificationWorker를 단일 검증 엔진(Core Engine)으로 통합한다."**

- **Framework**: Redis Queue (`verify:queue`) 기반의 Throttling 아키텍처를 유지.
- **Logic**: `RealtimeVerifier`의 "DB vs API Compare" 로직을 `VerificationWorker`의 Consumer로 이식.
- **Deprecation**: 독립 실행되던 `RealtimeVerifier` 루프를 제거하고, 스케줄러가 Queue에 Task를 넣는 방식으로 변경.

### Technical Spec
- **Queue**: `verify:queue` (Normal), `verify:queue:priority` (Recovery)
- **Task Types**:
    - `verify_db_integrity`: (New) DB View vs API Comparison.
    - `recovery`: (Existing) Fetch from API -> Upsert to DB.
- **Scheduler**:
    - `16:10 KST`: Daily Batch (All Symbols) -> Creates `verify_db_integrity` tasks.
    - `Market Hours`: Every Minute -> Creates `verify_db_integrity` tasks (Priority Symbols).

## 3. Consequences (Impact)
### Positive
- **Single Lineage**: 모든 검증/복구 작업이 Queue를 통하므로 로그 추적과 모니터링이 단일화됨.
- **Improved Integrity**: 장 마감 후에도 "DB에 실제 저장된 값"을 전수 검사하므로, 틱 누락을 100% 잡아낼 수 있음.
- **Resource Efficiency**: 중복된 Redis Connection 제거.

### Negative
- **Latency**: Queue 대기열이 밀릴 경우 실시간 검증(Realtime)이 수초 지연될 수 있음 (Priority Queue로 완화).

## 4. Alternatives Considered
- **RealtimeVerifier 중심 통합**: Queue가 없어 대량 트래픽(Batch) 처리 시 API Rate Limit 제어가 어려움 -> **반려**.
- **현행 유지**: 로직 중복과 관리 포인트 이원화 -> **반려**.
