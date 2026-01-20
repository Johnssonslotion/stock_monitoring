# IDEA: KIS-Kiwoom Dual Vendor Tick Comparison Strategy

**Status**: 💡 Seed (Idea)
**Priority**: P1

## 1. 개요 (Abstract)
현재 시스템은 KIS와 Kiwoom 두 곳으로부터 동일 또는 상호 보완적인 틱 데이터를 수집하고 있습니다. 이 두 소스의 데이터를 정밀하게 비교하여 데이터의 신뢰성을 검증하고, 각 벤더의 지연 시간(Latency) 및 결측률을 분석하여 최적의 데이터 소스를 선택하거나 하이브리드 수집 전략을 고도화하고자 합니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: 
    - 동일한 체결 이벤트에 대해 두 벤더의 가격은 일치해야 하지만, 거래량(누적 또는 단일) 처리 방식이나 수신 시점(Latency)에는 유의미한 차이가 있을 것이다.
    - 특정 시장 상황(급변장)에서 한 쪽 벤더의 데이터가 더 빨리 들어오거나 누락이 적을 것이다.
- **기대 효과**:
    - **데이터 무결성 확보**: 두 소스 간 교차 검증을 통해 유실된 틱을 즉시 감지하고 상호 보완 가능.
    - **지연 시간 최적화**: 더 빠른 벤더의 데이터를 우선적으로 사용하여 매매 신호 발생 지연 최소화.
    - **복구 자동화**: 한 쪽 소스의 데이터가 비정상일 때 자동으로 타 소스로 대체하는 로직의 근거 마련.

## 3. 구체화 세션 (Elaboration)
- **주요 비교 항목**:
    1. **Time Alignment**: 초 단위 또는 밀리초 단위의 체결 시각 일치 여부.
    2. **Execution No Matching**: Kiwoom의 체결번호를 기준으로 KIS 데이터 매칭 (Fuzzy Matching 필요 가능성).
    3. **Price/Volume Consistency**: 체결가와 체결량의 정확한 일치 확인.
    4. **Network Latency**: 거래소 체결 시각(`time`) 대비 서버 수신 시각(`received_time`)의 차이 (V1 vs V2).
    5. **Tick Completeness**: 특정 구간에서 한 쪽에서만 수집된 틱의 비율 분석.

- **6인 페르소나 초기 의견**:
    - **Pro_Dev**: "asyncpg를 이용한 대량 데이터 조인 연산으로 초 단위 일치율을 계산하는 모듈이 필요합니다."
    - **Reliability_Eng**: "Fuzzy Matching 시 허용 오차 범위를 정의해야 합니다. 예를 들어 ±1초 이내의 동일 가격/거래량은 동일 틱으로 간주할 것인가?"
    - **Quantum_Trader**: "지연 시간 비교가 가장 핵심입니다. 수신 속도 차이가 100ms 이상 벌어지는 구간을 찾아야 합니다."

- **기술적 구현 (SQL 예시)**:
    ```sql
    -- 1. 두 벤더 간 초 단위 일치율 및 지연 시간 분석 (샘플)
    SELECT 
        k.time as k_time,
        q.time as q_time,
        k.symbol,
        k.price,
        k.received_time - q.received_time as latency_diff
    FROM market_ticks_recovery k
    JOIN market_ticks_recovery q 
        ON k.symbol = q.symbol 
        AND k.time = q.time 
        AND k.price = q.price
    WHERE k.source = 'KIS' AND q.source = 'KIWOOM'
    LIMIT 100;

    -- 2. 특정 소스에만 존재하는 유니크 틱 탐지
    SELECT source, count(*) 
    FROM market_ticks_recovery 
    WHERE (time, symbol, price, volume) NOT IN (
        SELECT time, symbol, price, volume 
        FROM market_ticks_recovery 
        WHERE source = 'KIS'
    ) AND source = 'KIWOOM'
    GROUP BY source;
    ```

## 4. 로드맵 연동 시나리오
- **Pillar 2: Data Quality & Resilience** 에 포함될 예정.
- 실시간 수집 상태 모니터링 대시보드에 '벤더 간 정합성 지수' 항목 추가 가능.
