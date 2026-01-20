# IDEA: Dual Tick Recovery Strategy (KIS + Kiwoom)
**Status**: 🌿 Sprouting
**Priority**: P1

## 1. 개요 (Abstract)
기존에는 KIS REST API만이 유일한 복구(Recovery) 수단으로 여겨졌으나, **Kiwoom `ka10079` (틱 차트) API**의 실험 성공을 통해 **Kiwoom 또한 당일 과거 틱 데이터의 완전한 복구가 가능함**이 입증되었다. 이에 따라, 단일 복구 의존성을 탈피하고 **Dual Recovery Pipeline**을 구축하여 데이터 가용성을 100%에 수렴시킨다.

## 2. 실험 결과 요약 (Experiment Findings)
- **API**: Kiwoom `ka10079` (주식틱차트조회)
- **Capability**:
    - **Tick Fidelity**: `tic_scope=1` 설정 시 모든 체결 틱 조회 가능.
    - **Pagination**: `next-key` 헤더를 이용한 역순(최신→과거) 페이징 지원. `resp-cnt: 900` (1회 호출당 900건).
    - **Performance**: REST 호출로 대량의 틱 데이터 수집 가능.
- **Constraints**:
    - `User-Agent` 헤더 필수 (WAF 우회).
    - OAuth2 토큰 필요.

## 3. Dual Recovery Strategy
이제 우리는 두 개의 강력한 무기를 갖게 되었습니다.

| Feature | KIS REST (`FHKST01010300`) | Kiwoom REST (`ka10079`) |
|:---:|:---:|:---:|
| **Method** | 시세체결조회 | 틱차트조회 |
| **Direction** | 과거 → 현재 | 현재 → 과거 (추정) |
| **Recovery Role** | **Primary** (Gap Fill) | **Secondary** (Validation & Fallback) |
| **Pros** | 익숙한 REST, 단순함 | 정밀한 차트 데이터, 대량 조회 용이 |
| **Cons** | Rate Limit (초당 20건 제한) | Pagination Logic 복잡 (Next Key) |

## 4. 로드맵 연동 시나리오
- **Pillar**: Resilience
- **Action Items**:
    1. **Kiwoom Recovery Script 작성**: `scripts/recovery/recover_kiwoom_ticks.py` (ka10079 활용).
    2. **Recovery Manager 통합**:
        - Step 1: KIS 시도.
        - Step 2: KIS 실패/제한 시 Kiwoom으로 자동 절체(Failover).
    3. **Cross-Validation**: 장 마감 후 KIS 복구분 vs Kiwoom 복구분 대조.
