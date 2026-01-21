# IDEA: Dual-Provider (KIS+Kiwoom) Minute Data Collection & Load Balancing
**Status**: 🌿 Sprouting (Drafting)
**Priority**: [P1]

## 1. 개요 (Abstract)
- **문제**: 단일 API(KIS)에 의존할 경우, API 서버 장애나 Rate Limit 차단 시 분봉 데이터 수집에 공백이 생길 수 있음.
- **기회**: 이미 구축된 KIS와 Kiwoom 하이브리드 수집 환경을 활용하여, 분봉 데이터 수집 시에도 상호 백업(Dual-Collection) 및 부하 분산을 수행하여 'Zero-Gap' 데이터 환경을 구축함.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: KIS와 Kiwoom을 동시 또는 Fail-over 방식으로 가동하면, 특정 API의 일시적 장애가 전체 데이터 품질에 미치는 영향을 0%로 수렴하게 할 수 있음.
- **기대 효과**:
    - **고가용성 (HA)**: 한쪽 API가 429 에러로 차단되어도 다른 쪽에서 즉시 보충 가능.
    - **데이터 교차 검증**: 동일 시간대 분봉을 양쪽에서 받아 OHLCV 일치 여부를 실시간으로 대조하여 이상치 탐지 가능.
    - **부하 분산**: 70개 종목을 35개씩 나누어 수집함으로써 개별 API 키의 생존 가능성 향상.

## 3. 구체화 세션 (Elaboration - 6인 페르소나 의견)

- **[P1. Architect]**: "기술적으로 이미 GateKeeper가 구축되어 있어 큐 분할만 하면 된다. 다만, KIS는 REST, Kiwoom은 별도 컨테이너 통신이므로 인터페이스 추상화가 선행되어야 함."
- **[P2. Data Scientist]**: "케파는 이미 충분(30 calls/sec vs 1.1 calls/sec 필요)하지만, 데이터 정합성 측면에서 Dual-Collection은 강력한 찬성 항목이다."
- **[P3. DevSecOps]**: "Zero-Cost 원칙에 따라 추가 서버 증설은 불가하다. 현재 A1 인스턴스 내에서 Redis로 완벽하게 제어된다면 리소스 부담은 크지 않을 것."
- **[P4. Quantitative Strategist]**: "백테스트 시 1분봉 공백은 치명적이다. 백업 수집은 선택이 아닌 필수다."
- **[P5. Risk Manager]**: "API 키 노출이나 오남용 위험을 줄이기 위해, 사용 시점에만 큐에서 꺼내 쓰는 방식이 안전하다."
- **[P6. Project Manager]**: "중복 데이터 발생 시 병합(Merge) 로직이 복잡해질 수 있다. SSoT(Single Source of Truth) 기준을 명확히 해야 함."

## 4. 로드맵 연동 시나리오
- **Pillar 1: Data Infrastructure Stability**
- `ISSUE-015` (Gap Auto-completion) 작업의 하위 구현체 또는 다음 단계인 `ISSUE-021` (High-Availability Collection)로 승격 가능.

## 5. 케파(Capacity) 분석 결과
- **현재 수요**: 70종목 * 1분당 1회 = **1.16 TPS**
- **현재 공급 (KIS)**: **30 TPS** (25배 여유)
- **공급 (Kiwoom)**: **30 TPS** (추가 25배 여유)
- **결론**: 케파는 이미 단일 API로도 압도적으로 충분함. 따라서 이 제안의 가치는 '케파 증대'보다는 **'장애 내성(Fault Tolerance) 및 정밀도 향상'**에 있음.
