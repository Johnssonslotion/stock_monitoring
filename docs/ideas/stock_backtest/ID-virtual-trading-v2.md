# IDEA: 하이퍼 리얼리즘 가상 거래 시스템 (Hyper-Realistic Virtual Trading System)
**Status**: 🌿 Sprouting (Drafting)
**Priority**: P1 (Strategic)

## 1. 개요 (Abstract)
현재의 `VirtualExchange`는 주문 즉시 체결되는 단순한 로직으로 구성되어 있어, 실제 시장의 마찰(Friction)과 지연(Latency)을 반영하지 못합니다. 본 아이디어는 이를 개선하여 슬리피지(Slippage), 부분 체결(Partial Fill), 주문 취소 지연 등을 포함한 **하이퍼 리얼리즘 시뮬레이션 환경**으로 고도화하는 것을 목표로 합니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: 가상 거래 환경이 실제 시장과 유사할수록(마찰 비용 포함), 백테스트 결과와 실제 운영 수익률 간의 괴리(Alpha Decay)를 최소화할 수 있다.
- **기대 효과**:
    - **Accuracy**: 슬리피지를 반영하여 보다 보수적이고 정확한 전략 평가 가능.
    - **Robustness**: 네트워크 지연 및 주문 거부 시나리오에 대한 전략의 회복력 검증.
    - **Compliance**: 실제 브로커 API와 1:1 매칭되는 인터페이스 제공으로 코드 수정 없이 실거래 전환 가능.

## 3. 구체화 세션 (Council of Six Deliberation)

> ### 👔 PM (Project Manager)
> "전략의 수익률이 엑셀 상에서만 화려한 것은 아무 의미가 없습니다. 가상 거래 시스템이 실제 시장의 '가혹함'을 반영하지 못한다면, 그것은 개발자의 자기만족일 뿐입니다. 이번 고도화를 통해 실제 운영에서 발생할 수 있는 모든 비용과 리스크를 백테스트 단계에서 걸러낼 수 있는 환경을 구축해야 합니다. 이는 프로젝트의 중기 신뢰성을 확보하는 핵심 필러가 될 것입니다."

> ### 🏛️ Architect
> "현재의 `VirtualExchange`는 'Place -> Match -> Fill'이 하나의 트랜잭션으로 묶여 있는 강결합 구조입니다. 이를 'Order Ingress -> Matching Engine -> Execution Report'로 비동기 분리해야 합니다. Redis를 이벤트 버스로 활용하여 주문 상태 변화를 스트리밍하고, 실제 거래소와 유사한 비동기 메커니즘을 도입함으로써 시스템의 응집도를 높이고 확장성을 확보할 수 있습니다."

> ### 🔬 Data Scientist
> "단순 수수료 계산을 넘어, 호가창(Orderbook)의 가용 잔량을 기반으로 한 동적 슬리피지 모델링이 필요합니다. 10단계 호가 데이터를 활용하여 대량 주문 시 발생하는 가격 충격(Price Impact)을 수학적으로 모델링해야 합니다. 또한, 과거의 체결 강도와 거래량을 바탕으로 한 부분 체결 확률 모델을 도입하여 시뮬레이션의 차원을 높여야 합니다."

> ### 🔧 Infrastructure Engineer
> "가상 거래소의 상태를 관리하는 `virtual_*` 테이블들의 인덱스 최적화와 트랜잭션 격리 수준 설정이 중요합니다. 또한, Redis를 통한 주문 이벤트 전파 시 지연 시간을 최소화하기 위한 설정이 필요합니다. Zero Cost 원칙에 따라, 가상 거래 엔진이 과도한 CPU/Memory를 점유하지 않도록 경량화된 매칭 엔진(Lite-Matching)으로 설계하겠습니다."

> ### 👨‍💻 Developer
> "사용자 입장에서는 `VirtualBroker`와 `RealBroker`를 코드 한 줄로 교체할 수 있어야 합니다. 추상 베이스 클래스인 `Broker` 인터페이스를 엄격히 준수하도록 `VirtualExchange`를 리팩토링하겠습니다. 특히, 비동기 처리를 위한 `asyncio` Task 관리와 예외 상황(Exception)에 대한 정밀한 핸들링을 통해 엔진의 안정성을 최우선으로 구현하겠습니다."

> ### 🧪 QA Engineer
> "가장 중요한 것은 '결함이 있는 거래 환경'을 시뮬레이션하는 것입니다. 카오스 엔지니어링 원칙을 적용하여, 의도적으로 주문 지연을 발생시키거나 Redis 연결 끊김, DB 락 경합 상황을 주입하여 전략 코드가 어떻게 반응하는지 테스트하겠습니다. '테스트되지 않은 가상 환경은 또 다른 가짜 환경'일 뿐이라는 점을 명심하겠습니다."

## 4. 로드맵 연동 시나리오
- **Pillar**: Pillar 6 (Virtual Exchange)
- **Target Component**: `src/broker/virtual.py`, `src/broker/cost_model.py`, `tests/test_virtual_broker.py`

## 5. 제안하는 다음 단계 (Next Steps)
1. **ISSUE-014 (Audit)**: 현재 코드의 구조적 한계점 정밀 분석 및 리팩토링 스펙 정의.
2. **Spec Creation**: 비동기 매칭 엔진 및 슬리피지 모델에 대한 상세 명세(`docs/specs/virtual_matching_engine.md`) 작성.
3. **PoC**: Redis 기반의 주문 상태 전파 및 비동기 체결 로직 프로토타입 구현.
