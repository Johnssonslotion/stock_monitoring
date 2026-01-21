# ISSUE-036: [Task] DB 통합 - stock_test → stockval 마이그레이션

**Status**: Open
**Priority**: P1
**Type**: task
**Created**: 2026-01-21
**Assignee**: Developer

## Problem Description

환경변수 설정 오류로 인해 TimescaleDB 데이터가 두 개의 DB에 분산 저장됨:
- `.env` 및 `.env.prod`에서 `DB_NAME=stock_test`로 잘못 설정
- 2026-01-21 00:22부터 `stock_test` DB에 데이터 적재 시작
- 기존 `stockval` DB와 데이터 단절 발생

### 현재 데이터 분포

| DB | 테이블 | 건수 | 시작 | 종료 |
|----|--------|------|------|------|
| stockval | market_ticks | 4,211,496 | 2026-01-05 00:00 | 2026-01-20 06:30 |
| stockval | market_orderbook | 858,331 | 2026-01-12 05:55 | 2026-01-19 03:52 |
| stock_test | market_ticks | 450,763 | 2026-01-21 00:22 | 현재 |
| stock_test | market_orderbook | 318,652 | 2026-01-21 00:21 | 2026-01-21 01:12 |

**Data Gap**: 2026-01-20 06:30 ~ 2026-01-21 00:22 (약 18시간)

## Acceptance Criteria

- [ ] `stock_test.market_ticks` 데이터를 `stockval.market_ticks`로 마이그레이션
- [ ] `stock_test.market_orderbook` 데이터를 `stockval.market_orderbook`로 마이그레이션
- [ ] `.env` 파일의 `DB_NAME`을 `stockval`로 수정
- [ ] `.env.prod` 파일의 `DB_NAME`을 `stockval`로 수정
- [ ] 컨테이너 재시작 후 `stockval` DB에 정상 적재 확인
- [ ] 데이터 연속성 검증 (gap 확인)

## Technical Details

### 마이그레이션 방법

```sql
-- Option 1: pg_dump/restore
pg_dump -U postgres -d stock_test -t market_ticks --data-only | psql -U postgres -d stockval

-- Option 2: INSERT SELECT (same server)
INSERT INTO stockval.public.market_ticks
SELECT * FROM stock_test.public.market_ticks;
```

### 환경변수 수정 대상

- `/home/ubuntu/workspace/stock_monitoring/.env` (line 23)
- `/home/ubuntu/workspace/stock_monitoring/.env.prod` (line 23)

## Resolution Plan

1. 현재 archiver 일시 중지 (데이터 유실 방지를 위해 Redis에 버퍼링)
2. `stock_test` → `stockval` 데이터 마이그레이션 실행
3. `.env`, `.env.prod` 수정
4. 컨테이너 재시작
5. 데이터 적재 정상 확인

## Related

- ISSUE-033: TimescaleDB Schema Mismatch (원인 분석 중 발견)
- Branch: TBD

## Notes

- 18시간 gap은 별도 복구 불가 (원본 데이터 없음)
- 마이그레이션 시 중복 데이터 주의 (time + symbol + sequence_number 기준)
