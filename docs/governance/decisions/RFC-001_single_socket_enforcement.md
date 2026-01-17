# RFC-001: Single Socket Policy Enforcement

- **Status**: Accepted
- **Date**: 2026-01-17
- **Drivers**: Antigravity AI, Governance Council

## Context
현재 `backend_specification.md` (Section 3.1)는 데이터 수집을 위해 "Dual Socket" (KR/US Primary/Secondary) 연결을 표준으로 정의하고 있습니다. 그러나 프로젝트 헌법인 `.ai-rules.md` (Immutable Law #2)는 "KIS API는 하나의 소켓 연결만 유지한다"라고 명시하며 Dual Socket 시도를 금지하고 있습니다.

## Problem
- **Governance Violation**: Spec과 헌법이 충돌하여 개발자(AI)에게 혼란을 야기함.
- **Operational Risk**: Dual Socket 사용 시 KIS API의 정책 위반으로 인한 계정 차단 또는 데이터 수신 불안정 가능성.

## Decision
1.  **Enforce Single Socket**: `backend_specification.md`를 수정하여 **Single Socket** 만을 유일한 표준으로 인정한다.
2.  **Remove Dual Socket Logic**: `unified_collector.py` 및 관련 코드에서 Dual Socket 지원 로직을 Deprecated 처리하거나 제거한다.
3.  **Safe Failover**: Socket 연결 끊김 시 재접속(Reconnect) 로직을 강화하여 단일 소켓의 안정성을 확보한다.

## Consequences
- **Positive**: 헌법 준수, API 리스크 감소, 리소스 사용 최적화.
- **Negative**: 미국/한국 동시 수신 시 대역폭 병목 가능성 (현재 트래픽 수준에서는 무시 가능).
