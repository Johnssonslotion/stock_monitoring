# ISSUE-002: Virtual Investment Platform - Frontend UI

**Status**: Todo  
**Priority**: P1  
**Type**: feature  
**Created**: 2026-01-17  
**Assignee**: Frontend Developer  
**Related**: `ISSUE-001`, `docs/specs/virtual_investment_api.md`

## Problem Description
가상 투자 플랫폼의 사용자 인터페이스를 구현하여 사용자가 데스크탑 앱에서 주문을 입력하고 포지션/PnL을 실시간으로 확인할 수 있도록 해야 합니다.

## Acceptance Criteria
- [ ] **Virtual Account Section**: 계좌 정보 표시 (잔고, 통화)
- [ ] **Order Form**: 주문 입력 UI (종목, 매수/매도, 가격, 수량)
- [ ] **Position Table**: 보유 종목 실시간 표시
- [ ] **Order History**: 주문 내역 테이블
- [ ] **PnL Chart**: 손익 그래프 (실현/미실현)
- [ ] **WebSocket Integration**: 실시간 업데이트 (체결, 잔고 변동)

## Technical Details
**Framework**: React + TypeScript  
**Components**:
- `VirtualAccount.tsx` - 메인 컨테이너
- `VirtualOrderForm.tsx` - 주문 입력
- `VirtualPositionTable.tsx` - 포지션 테이블
- `VirtualOrderHistory.tsx` - 주문 내역
- `VirtualPnLChart.tsx` - 손익 차트

**API Endpoints** (ISSUE-001 제공):
- `POST /api/virtual/orders`
- `GET /api/virtual/account`
- `GET /api/virtual/positions`
- `GET /api/virtual/orders`
- `GET /api/virtual/pnl`

**WebSocket**: `ws://localhost:8000/ws/virtual`

## Implementation Plan
### Phase 1: Mock Development (선행 작업 가능)
1. API Spec 기반으로 Mock 데이터 생성
2. UI 컴포넌트 구현 및 레이아웃
3. Mock으로 사용자 플로우 테스트

### Phase 2: Real API Integration (ISSUE-001 완료 후)
1. Mock → Real API 호출 교체
2. WebSocket 연동
3. E2E 테스트

## Dependencies
- **Blocked by**: ISSUE-001 (REST API 엔드포인트 구현 필요)
- **Can start**: Mock 기반 UI 개발은 즉시 시작 가능

## Notes
- ISSUE-001과 파일 충돌 없음 (`src/web/` vs `src/api/`)
- `BACKLOG.md` 커밋 타이밍만 조율
