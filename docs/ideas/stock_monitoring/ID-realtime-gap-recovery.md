# IDEA: Real-time Gap Recovery System (Hybrid Verification)
**Status**: 📦 Archived (Merged into RFC-008)
**Priority**: P0 (Critical for Operational Stability)
**Merged To**: [RFC-008 Appendix H](../../../docs/rfc/RFC-008-tick-completeness-qa.md#appendix-h-real-time-gap-recovery-mode-added-2026-01-20)
**Archived Date**: 2026-01-20

> ⚠️ **Note**: 이 아이디어는 RFC-008에 Appendix H로 통합되었습니다.
> 향후 변경사항은 RFC-008에서 관리합니다.

## 1. 개요 (Abstract)
장 종료 후가 아닌, **장 중(Real-time)**에 데이터 누락을 즉시 감지하고 복구하는 시스템입니다.
수집된 Tick 데이터와 Kiwoom/KIS 분봉 API 데이터를 실시간으로 대조하여, 차이가 발생하면 즉시 REST API로 부족한 Tick을 채워 넣습니다. 이때 외부 API 호출은 Redis를 통해 엄격하게 제어됩니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: "분봉 API의 Volume 정보"를 Checksum으로 활용하면, 내가 수집한 Tick 데이터의 완전성을 1분 단위로 검증할 수 있다.
- **기대 효과**:
    - **즉시성**: 장 마감까지 기다릴 필요 없이, 누락 발생 1~2분 내에 자동 복구.
    - **API 효율**: 전체 재수집이 아닌 '누락된 구간'만 정밀 타격하여 호출하므로 Rate Limit 준수 용이.
    - **데이터 신뢰도**: Correlation 0.99 상시 유지 보장.

## 3. 구체화 세션 (Elaboration)
- **Architect**: `VerificationWorker`가 1분마다 `Active` 상태인 종목의 지난 1분을 검증.
- **Data Persona**: 분봉 API의 Volume과 Local Tick Sum의 오차(Tolerance) 설정 필요 (예: 1~2% 차이는 무시).
- **Infra Persona**: Redis Rate Limiter가 필수. KIS Tick API는 초당 호출 제한이 있으므로, 동시다발적 누락 시 'Priority Queue'로 중요 종목부터 복구해야 함.

## 4. 제안 아키텍처 (Proposed Architecture)
1.  **Collector**: WebSocket으로 Tick 수집 → DB 적재 (기존)
2.  **Verifier (New)**: `Min + 5sec` 시점에 해당 종목의 1분봉 API 조회.
3.  **Comparator**: `Local Tick Sum` vs `API Volume` 비교.
4.  **Recoverer**: Gap 감지 시 `KIS REST API (Tick)` 요청 (Redis Throttling 적용).
