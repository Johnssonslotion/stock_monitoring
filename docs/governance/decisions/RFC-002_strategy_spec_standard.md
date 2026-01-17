# RFC-002: Strategy Specification Standard

- **Status**: Accepted
- **Date**: 2026-01-17
- **Drivers**: Antigravity AI, Governance Council

## Context
현재 `src/backtest/strategies/` 경로에 `BaseStrategy.py` 등 전략 코드가 존재하나, 이에 대한 명세(Spec)가 전무합니다. 이는 "No Spec, No Code" 원칙을 위반하는 상태입니다. 전략 로직은 자금과 직결되므로 엄격한 정의가 필요합니다.

## Problem
- **Hidden Logic**: 코드만 보고 전략의 의도를 파악해야 하므로 오류 검증이 어려움.
- **Compliance Violation**: Spec Verification Gate 통과 불가.

## Decision
1.  **Mandatory Spec**: 모든 전략 클래스(Strategy Class)는 구현 전 반드시 `docs/specs/strategies/` 하위에 1:1 대응하는 Markdown Spec 파일을 가져야 한다.
2.  **Spec Structure**: 전략 Spec은 다음 항목을 반드시 포함해야 한다.
    - **Logic Description**: 진입/청산 조건 (수식 포함)
    - **Parameters**: 파라미터 이름, 타입, 기본값, 범위
    - **Data Requirements**: 필요한 데이터 종류 (Tick, 1Min, Orderbook)
    - **Edge Cases**: 데이터 누락, 장 시작/마감 시 처리 방침

## Consequences
- **Positive**: 전략 검증 용이성 증대, "No Spec No Code" 원칙 준수.
- **Negative**: 초기 문서화 비용 증가.
