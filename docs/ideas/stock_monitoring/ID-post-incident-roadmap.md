# IDEA: Post-Incident Roadmap & Stability Transition
**Status**: 💡 Seed (Idea)
**Priority**: P1

## 1. 개요 (Abstract)
2026-01-20 데이터 누락 사고(77% 손실)를 'Layered Strategy'로 성공적으로 복구하고 시스템 안정성을 확보했습니다.
이제 비상 대응 모드에서 정상 운영 모드(Operational Mode)로 전환하고, 입증된 복구 전략을 표준화하며, 미뤄두었던 전략 구현(Strategy Implementation) 단계를 준비해야 합니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: "Layered Recovery Strategy (Log + Tick API + Minute API)"를 표준 프로토콜로 정착시키면 향후 유사 사고 시에도 95% 이상의 데이터 정합성을 보장할 수 있다.
- **기대 효과**:
    - 데이터 신뢰성 확보 (Correlation 0.99+)
    - 운영 비용 최적화 (API Call 효율화)
    - 새로운 트레이딩 전략 개발을 위한 탄탄한 기반 마련

## 3. 구체화 세션 (Elaboration)
- **Data Persona**: 1월 20일 데이터 정합성(24,377 vs 25,813 차이)에 대한 정밀 재검증이 필요하지만, 89%~94% 수준의 커버리지는 전략 백테스팅에 유의미함.
- **Infra Persona**: Redis/Container 안정성 확보 확인. 이제 비용 절감(Zero Cost) 원칙을 유지하며 스케일링 가능한 구조인지 재점검 필요.
- **Strategy Persona**: 데이터가 확보되었으므로, 실제 'Sector Rotation' 감지 로직이나 'Momentum' 전략을 입힐 차례.

## 4. 로드맵 연동 시나리오
- **Pillar 1 (Data)**: Layered Recovery Protocol 공식화 (Spec 문서화).
- **Pillar 2 (Strategy)**: Alpha Strategy 구현 (다음 마일스톤).
