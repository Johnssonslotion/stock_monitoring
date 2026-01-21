# IDEA: Timestamp Pinning & Unified Time Logic
**Status**: 💡 Seed (Idea)
**Priority**: P1

## 1. 개요 (Abstract)
- **문제**: 시스템 여러 지점에서 `datetime.now()`를 호출할 경우, 데이터 수신 시점과 검증 시점 간의 미세한 지터(Jitter)로 인해 정합성 검증이 실패하거나 지연 시간이 부정확하게 측정됨.
- **해결**: "Ingestion Gate Pinning" 패턴을 정립하고, 시간 관련 유틸리티를 SSoT화하여 불확실성을 제거함.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: 수집기 진입점에서 시점을 고정(Pinning)하여 하위 모델과 Archiver까지 동일 객체를 전파하면, DB 인덱스 정렬 및 Latency 분석의 정확도가 99.9% 보장될 것임.
- **기대 효과**:
  - `received_time` 과 `timestamp` 간의 역전 현상 방지.
  - 네트워크 지연(Latency)의 정교한 프로파일링 가능.
  - 테스트 코드에서의 시간 결정론(Determinism) 확보.

## 3. 구체화 세션 (Elaboration)
- **Leo (Data Scientist)**: "틱 데이터의 전후 관계를 따질 때 브로커 시간뿐만 아니라 우리 시스템 수신 시간의 일관성이 매우 중요함. 밀리초 단위 오차가 누적되면 분석 결과가 왜곡됨."
- **Narae (DevOps)**: "하드웨어 시계 오차(Clock Drift)도 고려해야 하므로, 가급적 시스템 전체에서 UTC 기반의 단일 시간 소스를 사용하도록 강제해야 함."
- **Minho (Systems)**: "Pydantic 모델의 `default_factory`에 의존하기보다, 핸들러 초입에서 명시적으로 생성해 인자로 넘기는 것이 추적성이 좋음."

## 4. 로드맵 연동 시나리오
- **Pillar 2: High Performance & Reliability**
  - 가용성 및 성능 모니터링 레이어의 핵심 지표(Latency Trace)로 활용.
  - `src/utils/time_manager.py` (시스템 표준 시간 관리자) 도입 검토.

## 5. 제안하는 구체적인 코드 패턴
1. **The Pinning Pattern**:
   ```python
   def on_receive(raw_data):
       received_at = datetime.now(timezone.utc) # 진입점에서 고정
       data = MarketData(..., received_time=received_at)
   ```
2. **Context Manager / Decorator**:
   - 수집 핸들러에 `@trace_time` 데코레이터를 붙여 수신 시간을 자동으로 주입하는 방식.
3. **No-Now Principle**:
   - 비즈니스 로직(특히 DB 적재 관련) 내부에서는 직접적인 `datetime.now()` 호출을 금지하고, 항상 외부로부터 주입(Dependency Injection)받거나 전용 유틸리티 사용.
