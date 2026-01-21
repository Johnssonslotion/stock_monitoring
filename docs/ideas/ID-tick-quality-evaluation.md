# IDEA: Dual Provider Tick Quality Evaluation
**Status**: 💡 Seed
**Priority**: P2

## 1. 개요 (Abstract)
오늘(2025-01-20) 수집된 데이터(KIS Core 40, Kiwoom All)를 기반으로 두 공급자(Provider) 간의 틱 데이터 품질을 정량적으로 평가하여 비교 분석 리포트를 작성한다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: Kiwoom과 KIS는 수신 시점, 틱 빈도, 호가 갭 등에서 유의미한 차이가 있을 것이다. 특히 Kiwoom이 전 종목 Tick을 수집 중이므로 KIS Core 40 데이터와 1:1 비교가 가능하다.
- **기대 효과**:
    - "Main Provider" 선정에 대한 정량적 근거(Latency, Completeness) 확보.
    - 데이터 보정(Correction) 및 아비트라지(Arbitrage) 전략 수립 가능성 확인.
    - 장애 상황 시 대체(Failover) 신뢰도 평가.

## 3. 평가 지표 (Metrics)
1. **Timestamp Latency**: 동일 체결 건(추정)에 대한 시스템 수신 시각 차이 분포.
2. **Completeness**: 분 단위 틱 카운트 비교 (누락율).
3. **Price Divergence**: 동일 시각(초 단위) 가격 불일치 발생 빈도 및 지속 시간.

## 4. 로드맵 연동
- [Strategy] Data Management & Optimization (ISSUE-030 후속)
- [Quality] Data Integrity Validation
