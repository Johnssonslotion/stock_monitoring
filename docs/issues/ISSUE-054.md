# ISSUE-054: WebSocket Stream Test Stabilization (ISSUE-008 Follow-up)

## Context
ISSUE-008 (Phase 1) 구현 시 `test_websocket_stream.py`가 타임아웃으로 인해 조건부 Skip 처리되었습니다. 실시간 스트리밍 기능의 안정성 확보를 위해 해당 테스트의 원인을 분석하고 안정화해야 합니다.

## Goals
- [ ] `tests/integration/test_websocket_stream.py` 타임아웃 원인 분석 (Network, Rate Limit, or Logic)
- [ ] WebSocket 연결 및 메시지 수신 테스트 안정화 (Mocking or Environment Tuning)
- [ ] CI 환경에서 Flaky 하지 않도록 개선

## Specs
- **Target Test**: `tests/integration/test_websocket_stream.py`
- **Success Criteria**: 
    - `poetry run pytest tests/integration/test_websocket_stream.py`가 3회 연속 통과
    - 실행 시간 10초 이내 (혹은 적절한 타임아웃 설정)

## Related
- ISSUE-008: Parent Issue
- ISSUE-053: 10-Level Orderbook (Implementation Done)
