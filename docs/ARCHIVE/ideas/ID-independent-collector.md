# IDEA: Independent Collector Module Architecture

**Status**: 🌿 Sprouting (Drafting)
**Priority**: P1
**Category**: Infrastructure
**Source**: User Feedback

## 1. 개요 (Abstract)
현재 수집 모듈(Collector)이 다른 시스템 구성 요소(백엔드, 전략 등)와 결합되어 있을 가능성을 배제하고, 이를 완전히 독립적인 서비스 또는 모듈로 분리하여 독자적인 생명주기를 갖도록 설계합니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: 수집 모듈을 독립적으로 구성하면 특정 브로커(KIS, 키움, 미래)의 API 변경이나 장애가 전체 시스템에 미치는 영향을 최소화할 수 있다.
- **기대 효과**:
  - 모듈별 독립 배포 가능 (Microservices 준비)
  - 데이터 유실 방지(Circuit Breaker 적용 용이)
  - 테스트 및 유지보수 효율성 증대

## 3. 구체화 세션 (Elaboration)
- **Architect**: 수집기 전용 인터페이스(`BaseCollector`)를 강화하고, Redis/Kafka 등을 통한 비동기 데이터 전달을 표준화해야 합니다.
- **Developer**: 현재 `unified_collector.py`에 집중된 로직을 개별 프로세스로 분리할 수 있는 구조로 리팩토링이 필요합니다.
- **QA**: 수집 모듈만 별도로 Chaos Test를 수행할 수 있는 환경을 구축해야 합니다.

## 4. 로드맵 연동 시나리오
- **Pillar**: Infrastructure & Data Reliability
- **Next Step**: RFC 작성 및 수집기 엔진 리팩토링 (Current Backlog: 수집단 개편 항목 고도화)
