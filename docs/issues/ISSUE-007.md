# ISSUE-007: 웹소켓 연결 관리자 구현 (WebSocket Connection Manager)

**Status**: Open  
**Priority**: P1 (High)  
**Type**: Epic Feature  
**Created**: 2026-01-17  
**Assignee**: Backend Engineer  

## Problem Description
KIS API는 "API Key 당 하나의 소켓 연결" 정책을 엄격하게 적용합니다. 구독을 다중화하고 재연결을 자동으로 처리하기 위한 중앙 집중식 `ConnectionManager`가 필요합니다.

## Design (Architecture)

### Multiplexing Strategy
```
KIS WebSocket (Single Connection)
  ↓ Subscribe: [005930, 000660, 035420, ...]
  ↓ Receive ticks
ConnectionManager
  ↓ Redis Pub/Sub (stock:ticks)
  ↓ Broadcast to multiple clients
Dashboard Clients (Browser Tabs)
```

### Auto-Reconnection
- **Backoff Algorithm**: 1s → 2s → 4s → 8s (max 60s)
- **Dead Man's Switch**: 60초간 데이터 0건 → 강제 재연결

## Implementation Checklist
- [ ] `ConnectionManager` 싱글톤 클래스 (`src/backend/ws/manager.py`)
- [ ] 구독 다중화 로직 (여러 심볼 → 단일 소켓)
- [ ] Redis Pub/Sub 연동 (`stock:ticks` 채널)
- [ ] Backoff 재연결 로직
- [ ] 멀티 탭 테스트 (소켓 1개 유지)

## Acceptance Criteria
- [ ] 전역적으로 API Key당 1개의 소켓만 생성
- [ ] 연결 끊김 시 60초 이내 자동 재접속
- [ ] Redis를 통한 틱 데이터 발행 확인

## Related PRs
(To be added)
