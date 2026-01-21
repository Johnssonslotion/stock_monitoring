# ISSUE-013: Virtual Trading Audit

**Status**: Open 🌿
**Priority**: P1 (Strategic)
**Type**: Audit / Refactoring
**Created**: 2026-01-19
**Assignee**: Architect / Backend Engineer
**Related Idea**: [IDEA-005 (Hyper-Realistic Virtual Trading)](../ARCHIVE/ideas/ID-virtual-trading-v2.md)

## 1. 문제 정의 (Problem Statement)
현재 `src/broker/virtual.py`에 구현된 가상 거래 엔진은 '즉시 체결'이라는 단순화된 로직에 의존하고 있어, 실제 시장의 마찰(슬리피지, 주문 지연) 및 비동기적 특성을 반영하지 못하고 있음. 전략의 현실성을 확보하기 위해 현재 구조를 진단하고 비동기 매칭 엔진으로의 전환을 설계해야 함.

## 2. 주요 점검 항목 (Audit Checklist)
- [ ] **체결 모델링 (Execution Model)**: 
    - `place_order` 내의 즉시 체결 로직을 비동기 'Place -> Match -> Fill' 흐름으로 분리 가능한지 검토.
    - 호가창(Orderbook) 데이터를 활용한 슬리피지 계산 로직 부재 확인.
- [ ] **기능 누락 (Missing Features)**:
    - `cancel_order`가 항상 `False`를 반환하는 문제 (취소 기능 미지원).
    - 부분 체결(Partial Fill) 처리 로직 부재.
- [ ] **이벤트 시스템 (Event System)**:
    - Redis를 통한 `virtual.execution`, `virtual.account` 이벤트 발행의 일관성 및 지연 시간 검증.
- [ ] **데이터 무결성 (Data Integrity)**:
    - `virtual_accounts`, `virtual_positions`, `virtual_orders` 테이블 간의 원자성(Atomicity) 보장 여부 (현재 transaction 사용 중이나 예외 처리 보강 필요).

## 3. 디자인 가이드라인 (Design Guidelines)
- **Interface Consistency**: `src/broker/base.py`의 `Broker` 인터페이스와 100% 호환되어야 함.
- **Complexity**: Zero Cost 원칙에 따라 과도한 리소스를 사용하지 않는 경량 매칭 로직 지향.
- **Traceability**: 모든 주문 상태 변화는 `virtual_orders` 테스크에 히스토리가 남아야 함.

## 4. 수락 기준 (Acceptance Criteria)
- [ ] 현재 구현의 한계점을 정리한 Audit Report (ISSUE 내 또는 별도 문서) 작성.
- [ ] 슬리피지 및 비동기 매칭을 반영한 차세대 가상 거래 엔진 Spec 문서(`docs/specs/`) 작성.
- [ ] 리팩토링을 위한 단위 테스트 시나리오 정의.
