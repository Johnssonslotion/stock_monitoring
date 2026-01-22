# Issue-026: [Debt] Kiwoom Orderbook Pub/Sub 및 아카이빙 구현

**Status**: Open  
**Priority**: P2  
**Type**: refactor  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- `KiwoomWSCollector`가 실시간 호가(`0D`) 데이터를 수신하고 있으나, Redis로 발행하지 않아 TimescaleDB에 저장되지 않음.
- KIS는 이미 호가 수집 및 저장 로직이 존재하므로 Kiwoom도 동일 규격으로 구현 필요.

## Acceptance Criteria
- [ ] `KiwoomWSCollector`에서 `0D` 메시지 발생 시 Redis 채널로 발행.
- [ ] `TimescaleArchiver`에서 해당 데이터를 수신하여 `market_orderbook` 테이블에 적재.
