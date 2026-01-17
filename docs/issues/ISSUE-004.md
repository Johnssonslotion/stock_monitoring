# ISSUE-004: 웹소켓 연결 관리자 구현 (WebSocket Connection Manager Implementation)

**Status**: Open (작성 완료)
**Priority**: P1 (High)
**Type**: Feature
**Created**: 2026-01-17
**Assignee**: Backend Engineer

## 문제 설명 (Problem Description)
KIS API는 "API Key 당 하나의 소켓 연결" 정책을 엄격하게 적용합니다. 구독을 다중화하고 재연결을 자동으로 처리하기 위한 중앙 집중식 `ConnectionManager`가 필요합니다.

## 완료 조건 (Acceptance Criteria)
- [ ] **싱글 소켓 정책 (Single Socket Policy)**: 전역적으로 API Key 당 1개의 소켓만 생성되도록 강제.
- [ ] **다중화 (Multiplexing)**: 단일 소켓 연결 위에서 여러 심볼(종목) 구독 처리.
- [ ] **복구 능력 (Recoverability)**: 연결 끊김 시 60초 이내 자동 재접속(Backoff 알고리즘 포함).
- [ ] **Redis Pub/Sub**: `stock:ticks` 채널로 틱 데이터 발행.

## 기술 상세 (Technical Details)
- **File**: `src/backend/ws/manager.py`
- **Redis**: 데이터 수집과 소비를 분리하기 위해 Pub/Sub 패턴 사용.
