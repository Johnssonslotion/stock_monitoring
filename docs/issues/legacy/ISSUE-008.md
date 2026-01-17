# ISSUE-008: 실시간 호가(OrderBook) 스트리밍 구현 (OrderBook Streaming)

**Status**: Open (작성 완료)
**Priority**: P1 (Critical)
**Type**: Feature
**Created**: 2026-01-17
**Assignee**: Backend Engineer

## 문제 설명 (Problem Description)
데이 트레이더(Scalper)를 위해 실시간 호가(Hoga) 데이터 스트리밍이 필수적입니다. 매번 전체 스냅샷을 전송하는 대신, 변경분(Delta)만 전송하여 대역폭 사용량을 최적화해야 합니다.

## 완료 조건 (Acceptance Criteria)
- [ ] `stream_orderbook` 핸들러 구현.
- [ ] 호가 잔량 변동분(Delta) 전송 로직 구현 (대역폭 절약).

## 기술 상세 (Technical Details)
- **Source**: KIS WebSocket (H0STASP0)
- **Optimization**: 브로드캐스트 전 Diff 계산.
