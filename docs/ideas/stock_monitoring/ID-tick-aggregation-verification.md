# IDEA: Tick Aggregation Verification (Tick-to-Candle Fidelity)
**Status**: 🌿 Sprouting (Drafting)
**Priority**: P1

## 1. 개요 (Abstract)
현재의 검증(Verification) 로직은 **KIS API 분봉 vs Kiwoom API 분봉**을 비교하는 'Dual API Verification' 방식입니다.
사용자가 제안한 방식은 **"수집된 로컬 틱 데이터를 1분봉으로 합산(Aggregation)한 결과" vs "브로커 공식 API 분봉"**을 비교하여, 수집된 틱 데이터의 무결성(Integrity)을 검증하는 **'Bottom-Up Verification'** 모델입니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: 수집된 틱(Tick)이 정확하다면, 이를 합산한 OHLCV(Open/High/Low/Close/Volume)는 브로커가 제공하는 분봉 데이터와 정확히 일치해야 한다.
- **기대 효과**:
  - **데이터 누락 감지**: 틱이 하나라도 빠지면 거래량(Volume)이나 고가/저가(High/Low)가 불일치하게 되므로 즉시 탐지 가능.
  - **비용 절감**: 두 브로커의 API를 매번 호출하는 대신, 로컬 연산 후 'Reference API(Ground Truth)' 하나만 호출하여 비교 가능.
  - **복구 정밀도**: 어느 시점의 틱이 비었는지 더 정밀하게 추적 가능.

## 3. 구체화 세션 (Elaboration)
**(6인 페르소나 의견)**
- **Architect**: "현재 `src/verification/worker.py`는 API 간 비교에 집중되어 있습니다. `src/data_ingestion/aggregator` 로직을 검증 워커에 포팅하여 'Local Candle'을 실시간 생성해야 합니다."
- **Developer**: "`impute_final_candles.py`에 이미 유사한 로직(Log Aggregation)이 있습니다. 이를 실시간 워커(`RealtimeVerifier`)로 가져와야 합니다."
- **Data Engineer**: "Redis에 틱이 쌓일 때마다 실시간으로 Aggregation하는 Stream Processing 구조가 필요할 수 있습니다."

## 4. 로드맵 연동 시나리오
- **Target Logic**:
  1. `Collector`가 틱 수집 -> Redis/DB 저장.
  2. `Verification Worker`가 1분마다 로컬 틱을 조회 -> OHLCV 생성 (Local Candle).
  3. `Verification Worker`가 KIS REST API 호출 -> 공식 OHLCV 확보 (Ref Candle).
  4. Compare (Local vs Ref).
  5. Diff > Tolerance(0%) -> **Recovery Trigger** (틱 데이터 재수집).

- **Pillar**: **Phase 3 - Reliability & Verification**
