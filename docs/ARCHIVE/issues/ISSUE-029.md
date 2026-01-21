# ISSUE-029: [Feature] Minute-Level Data Validation Table Schema & Aggregation

**Status**: Open  
**Priority**: P1  
**Type**: feature  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- 현재 수집된 Tick 데이터의 완전성(Completeness)을 검증할 수 있는 기준 데이터가 부족함.
- 수집된 데이터가 실제 시장 데이터와 일치하는지, 혹은 누락이 발생했는지 분(Minute) 단위로 교차 검증할 수 있는 메커니즘 필요.

## Proposed Solution (Validation Table Schema)
`market_ticks_validation` (DuckDB)

| Column | Type | Description |
| :--- | :--- | :--- |
| `symbol` | VARCHAR | 종목 코드 |
| `bucket_time` | TIMESTAMP | 1분 단위 Time Bucket (e.g., 09:00:00, 09:01:00) |
| `tick_count_collected` | INT | 수집된 실제 틱 개수 (Archiver 집계) |
| `volume_sum` | INT | 수집된 거래량 합계 |
| `price_open` | DOUBLE | 해당 분의 시가 |
| `price_close` | DOUBLE | 해당 분의 종가 |
| `price_high` | DOUBLE | 해당 분의 고가 |
| `price_low` | DOUBLE | 해당 분의 저가 |
| `updated_at` | TIMESTAMP | 레코드 갱신 시각 |

## Acceptance Criteria
- [ ] **Schema Definition**: DuckDB 내 `market_ticks_validation` 테이블 생성 SQL 작성.
- [ ] **Aggregation Logic**: `market_ticks` 테이블에서 1분 단위로 Group By하여 위 통계치를 산출하고 Validation 테이블에 Upsert하는 쿼리/스크립트 작성.
- [ ] **Validation Point**: 향후 KIS나 Kiwoom의 분봉 API(OHLCV)를 조회하여 이 테이블의 값과 비교함으로써 정합성을 검증함.
