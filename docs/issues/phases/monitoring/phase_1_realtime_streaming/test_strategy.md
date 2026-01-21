# Phase 1: Real-time Streaming - Test Strategy

## Unit Testing
- [ ] **WS Router**: `/ws/system` 연결 및 인증 테스트.
- [ ] **Message Handler**: Redis Pub/Sub 메시지가 WS 클라이언트로 올바르게 라우팅되는지 확인.
- [ ] **Schema Validation**: 전송되는 JSON 패킷이 `SystemMetric` 스키마를 준수하는지 검증.

## Integration Testing
- [ ] **Sentinel-to-Dashboard**: `sentinel.py`에서 생성된 지표가 대시보드 UI까지 도달하는 전체 경로 검사.
- [ ] **Concurrency**: 다중 클라이언트 접속 시 성능 및 리소스 경합 확인.

## Chaos Testing
- [ ] **Reconnect Policy**: Redis 중단 또는 백엔드 재시작 시 클라이언트의 자동 재연결 능력 검증.
