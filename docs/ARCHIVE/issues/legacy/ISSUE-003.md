# ISSUE-003: DB 뷰 재생성 및 집계 복구 (DB View & Aggregation Restoration)

**Status**: Open (작성 완료)
**Priority**: P0 (Critical)
**Type**: Bug / Data Quality
**Created**: 2026-01-17
**Assignee**: Backend Engineer

## 문제 설명 (Problem Description)
캔들 데이터(1m, 5m, 1h, 1d)에 대한 데이터베이스 뷰와 연속 집계(Continuous Aggregates)가 누락되었거나 검증이 필요합니다. 이는 데이터 무결성과 쿼리 성능에 치명적입니다.

## 완료 조건 (Acceptance Criteria)
- [ ] `market_candles` 데이터 보존(Retention) 정책 확인.
- [ ] `public.candles_1m` 뷰 재생성.
- [ ] 5분/1시간/1일 단위의 연속 집계(Continuous Aggregates) 생성 및 Refresh 정책 등록.
- [ ] `SELECT count(*)` 쿼리로 모든 시간대의 데이터 존재 여부 검증.

## 기술 상세 (Technical Details)
- **DB**: TimescaleDB
- **Key Tables**: `market_candles`, `candles_1m`, `candles_5m` 등.
