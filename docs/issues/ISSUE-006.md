# ISSUE-006: DB 뷰 재생성 및 집계 복구 (DB View & Aggregation Restoration)

**Status**: Open  
**Priority**: P0 (Critical)  
**Type**: Bug / Data Quality  
**Created**: 2026-01-17  
**Assignee**: Backend Engineer  

## Problem Description
캔들 데이터(1m, 5m, 1h, 1d)에 대한 데이터베이스 뷰와 연속 집계(Continuous Aggregates)가 누락되었거나 검증이 필요합니다. 이는 데이터 무결성과 쿼리 성능에 치명적입니다.

## Design (TimescaleDB Configuration)

### Views
```sql
-- 1분봉 뷰
CREATE VIEW candles_1m AS 
SELECT * FROM market_candles WHERE interval = '1m';

-- Continuous Aggregates
CREATE MATERIALIZED VIEW candles_5m
WITH (timescaledb.continuous) AS
SELECT 
  time_bucket('5 minutes', timestamp) AS bucket,
  symbol,
  first(open, timestamp) AS open,
  max(high) AS high,
  min(low) AS low,
  last(close, timestamp) AS close,
  sum(volume) AS volume
FROM market_candles
GROUP BY bucket, symbol;
```

## Implementation Checklist
- [ ] `market_candles` 데이터 보존(Retention) 정책 확인
- [ ] `public.candles_1m` 뷰 재생성
- [ ] 5분/1시간/1일 단위의 연속 집계 생성
- [ ] Refresh 정책 등록
- [ ] `SELECT count(*)` 쿼리로 모든 시간대 데이터 검증

## Acceptance Criteria
- [ ] 모든 집계 뷰에서 데이터 존재 여부 확인 (count > 0)
- [ ] 쿼리 성능: 1일치 데이터 < 50ms

## Related PRs
(To be added)
