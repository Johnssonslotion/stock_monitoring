# 프로젝트 대전략 (Grand Strategy): The Road to Alpha

**Version**: 1.0
**Date**: 2026-01-04
**Status**: Approved by Council of Seven

## 0. 서문 (Preamble)
본 문서는 `stock_monitoring` 프로젝트가 나아가야 할 거시적인 이정표(Milestone)를 정의한다. 단순한 개발 단계의 나열이 아니라, 각 단계가 **완결성**을 가지며 다음 단계의 **기반**이 되는 진화적(Evolutionary) 로드맵이다.

---

## Phase 1: Foundation & Ingestion (기반 및 수집)
> **Context**: "데이터가 흘러야 피가 돈다."

*   **Goal**: 끊김 없는(Seamless) 실시간 틱 데이터 파이프라인 구축.
*   **Deliverables**: `TickCollector`, `Redis Pub/Sub`, `DuckDB Archiver`.
*   **Key Constraints**:
    *   **Resource**: 오라클 프리티어 메모리 한계 준수 (Infra).
    *   **Stability**: 네트워크 단절 시 자동 복구 (QA).
*   **Persona Comments**:
    *   **Infra**: "메모리 누수 잡는 단계입니다. 여기서 못 잡으면 뒤는 없습니다."
    *   **Dev**: "비동기(Asyncio) 패턴을 확실하게 잡고 가겠습니다."

## Phase 2: Analysis & Feature Engineering (분석 및 가공)
> **Context**: "원석을 보석으로."

*   **Goal**: 단순 틱 데이터를 트레이딩에 사용 가능한 **지표(Signal)**로 실시간 변환.
*   **Deliverables**: `StreamProcessor`, `FeatureStore` (CVD, OI, VPIN 등).
*   **Key Constraints**:
    *   **Latency**: 지표 생성 지연 시간 < 10ms (Data Scientist).
*   **Persona Comments**:
    *   **Data Scientist**: "여기가 핵심입니다. 쓰레기 데이터를 넣으면 쓰레기 전략이 나옵니다."
    *   **Architect**: "계산 로직과 수집 로직의 결합도를 0으로 만드세요."

## Phase 3: Strategy & Experimentation (전략 및 실험)
> **Context**: "가설을 검증하라."

*   **Goal**: 격리된 환경에서 다양한 전략을 실험하고 검증.
*   **Deliverables**: `Backtester`, `PaperTrader`, `Experiment Branch (exp/*)`.
*   **Key Constraints**:
    *   **Isolation**: 운영 환경 오염 절대 금지 (Architect).
    *   **Config**: 코드 수정 없는 파라미터 튜닝 (PM).
*   **Persona Comments**:
    *   **Researcher**: "브랜치 전략 덕분에 마음 놓고 실험하겠습니다."
    *   **QA**: "검증 안 된 전략은 배포 승인 안 해줍니다."

## Phase 4: Execution & Trading (실행 및 매매)
> **Context**: "전장에 나가라."

*   **Goal**: 실제 자산을 운용하여 Alpha 창출.
*   **Deliverables**: `OrderExecutor`, `RiskManager` (Kill Switch).
*   **Key Constraints**:
    *   **Safety**: 자산 보호를 위한 2중, 3중 안전장치 (PM).
*   **Persona Comments**:
    *   **PM**: "수익률보다 중요한 건 **MDD 방어**입니다."
    *   **QA**: "주문 실패 시나리오 테스트(Chaos Test) 준비 끝났습니다."

---

## 5. 승인 프로세스 (Approval Process)
각 Phase 진입 전과 완료 후, **PM(사용자)의 전략적 승인**을 득해야 한다.
1.  **Pre-Approval**: 해당 단계의 상세 구현 계획(Implementation Plan) 승인.
2.  **Post-Review**: 결과물 데모 및 회고.
