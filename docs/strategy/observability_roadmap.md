# Roadmap: Observability & Real-time Monitoring

## Overview
현재 시스템의 메트릭 수집 및 모니터링 체계를 REST 폴링 방식에서 **WebSocket 기반 실시간 스트리밍** 및 **지능형 장애 복구** 체계로 진화시킵니다. "No Spec, No Code" 원칙에 따라 모든 백엔드 로직은 명세화된 인터페이스를 따릅니다.

## Quality Gates
- **Pillar 1 (Streaming)**: WebSocket 연결 성공률 99.9%, 레이턴시 500ms 미만.
- **Pillar 2 (Recovery)**: 서비스 중단 감지 시 30초 이내 자동 복구 스크립트 트리거.
- **Pillar 3 (Accuracy)**: DB 메트릭과 실시간 스트리밍 데이터 일치율 100%.

## Strategic Pillars

### Pillar 1: Real-time Infrastructure Monitoring
- **Goal**: 하드코딩된 폴링을 제거하고 실시간 리소스 변화를 대시보드에 반영.
- **Phases**:
    - [x] **Phase 1: WebSocket Backend**: FastAPI `WebsocketRouter` 도입 및 Redis Pub/Sub 연동. (DONE)
    - [x] **Phase 2: Frontend Refactor**: `StreamManager` 통합 및 실시간 차트 렌더링 최적화. (DONE)

### Pillar 2: Intelligent Sentinel (Alerting & Recovery)
- **Goal**: 단순 지표 수집을 넘어, 장애 상황을 스스로 판단하고 조치하는 'Sentinel' 고도화.
- **Phases**:
    - [x] **Phase 1: Sentinel Alert Routing**: 시스템 경고 발생 시 WebSocket을 통한 즉각 전파. (DONE)
    - [ ] **Phase 2: Auto-Recovery Integration**: 백로그 P2 아이템 'Failure Mode 자동 복구' 구현.

## Timeline (Q1 2026)
- **Week 3**: WebSocket 인프라 구축 및 기존 메트릭 스트리밍 전환.
- **Week 4**: Sentinel 장애 감지 및 복구 자동화 인터페이스 정의.

## Council Approval
- **Architect**: "스트리밍 아키텍처 도입으로 백엔드 부하를 줄이고 실시간성을 확보할 수 있어 승인함."
- **QA**: "실시간 데이터의 정합성 검증을 위한 테스트 시나리오가 필수적임."
- **PM**: "프론트엔드 사용자 경험을 한 단계 높이는 중요한 단계임. 즉시 진행 승인."
