# RFC-007: Virtual Exchange Architecture (Hyper-Realism)

**Status**: ⚪ Draft
**Date**: 2026-01-29
**Author**: Developer Persona
**Related**: [Pillar 6](../../strategy/master_roadmap.md), `ISSUE-001`

## 1. Context (Problem)
단순한 가상 매매를 넘어, 실제 시장의 슬리피지, 수수료, 세금 및 호가 잔량에 따른 체결 가능성을 시뮬레이션할 수 있는 **Hyper-Realistic 가상 거래소** 아키텍처가 필요합니다.

## 2. Shared Principles
- **API Parity**: 실제 브로커(KIS, Kiwoom)와 동일한 인터페이스 형식을 사용하여, 전략 코드를 수정 없이 실전으로 전환 가능해야 함.
- **Latency Emulation**: 통신 지연 및 체결 지연을 시뮬레이션 환경에 반영.

## 3. Decision (Architecture)

### 3.1 `VirtualBroker` Core Logic
1. **Order Matching Engine**:
   - `LIMIT` 주문: Redis의 실시간 호가(`market_orderbook`) 잔량을 확인하여 가격 도달 및 잔량 소진 시 체결 처리.
   - `MARKET` 주문: 현재가(Tick)를 기준으로 즉시 체결하되, 슬리피지 모델 적용.
2. **Cost Calculation Module**:
   - 유관기관 수수료, 세금(거래세), 미수 발생 시 이자 등을 반영한 잔고 계산.

### 3.2 Database Schema
- `virtual_accounts`: 가상 계좌 잔고 및 설정.
- `virtual_positions`: 현재 보유 종목 및 평균 단가.
- `virtual_orders`: 가상 주문 기록 및 상태.
- `virtual_execution_history`: 체결 상세 내역.

## 4. Implementation Plan
1. `src/broker/virtual/` 디렉토리 신설 및 `BaseBroker` 인터페이스 상속.
2. Redis Pub/Sub을 활용한 실시간 체결 처리기(Processor) 개발.
3. `/api/virtual` 엔드포인트 연동 (FastAPI).

## 5. Consequences
- **Pros**: 실전과 매우 유사한 백테스팅 및 가상 투자 환경 제공.
- **Cons**: 호가 기반 체결 로직으로 인해 연산 오버헤드 발생 가능 (Redis 최적화 필요).
