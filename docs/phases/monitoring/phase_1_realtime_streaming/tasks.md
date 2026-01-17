# Phase 1: Real-time Streaming - Task Checklist

## Objectives
- REST 폴링 기반 시스템 대시보드를 WebSocket 스트리밍 방식으로 전환.
- Sentinel의 가용성 지표를 실시간으로 전파.

## Deliverables
- [ ] [BACKEND] `/ws/system` WebSocket 엔드포인트 구현
- [ ] [BACKEND] Redis Pub/Sub을 통한 시스템 메트릭 브로드캐스트
- [ ] [FRONTEND] `StreamManager`에 시스템 모니터링 채널 추가
- [ ] [FRONTEND] `SystemDashboard` 컴포넌트 실시간 연동

## Quality Gate
- [ ] `/run-gap-analysis` 통과 (Spec 일치)
- [ ] WebSocket 재연결(Reconnection) 로직 테스트 통합
- [ ] Council Review (Architecture Change) 승인
