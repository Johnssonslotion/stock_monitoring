# ISSUE-033: [Bug] TimescaleArchiver Schema Mismatch & Missing Relation

**Status**: Resolved  
**Priority**: P0  
**Type**: bug  
**Created**: 2026-01-21  
**Assignee**: Developer

## Problem Description
실시간 데이터 수집 중 `timescale-archiver`가 데이터를 TimescaleDB에 적재하지 못하는 현상이 발견됨. 
로그 확인 결과 `column "source" does not exist` 및 `relation "market_orderbook" does not exist` 오류가 반복적으로 발생하고 있음.

이는 `src/data_ingestion/archiver/timescale_archiver.py`의 `init_db` 메서드에서 정의한 테이블 스키마와 실제 `flush` 및 `copy_records_to_table`에서 사용하는 컬럼 목록이 일치하지 않아 발생하는 문제로 판단됨.

## Acceptance Criteria
- [x] `market_ticks` 테이블에 `source`, `broker`, `received_time` 등의 필수 컬럼이 포함되도록 `init_db` 수정
- [x] `market_orderbook` 테이블이 없을 경우 자동 생성하는 로직 추가
- [x] 서비스 재시작 후 TimescaleDB에 데이터가 정상적으로 적재되는지 확인 (SQL query 결과 > 0) ✅ 494,505 ticks/1h (2026-01-23 검증)
- [x] Sentinel 알림에서 관련 에러가 사라지는지 확인 ✅ timescale-archiver 정상 동작 중

## Technical Details
- **Archiver Source**: `src/data_ingestion/archiver/timescale_archiver.py`
- **Error Log**: 
  - `ERROR:TimescaleArchiver:DB Flush Error: column "source" does not exist`
  - `ERROR:TimescaleArchiver:Orderbook Save Error: relation "market_orderbook" does not exist`

## Resolution Plan
1. `init_db` 메서드의 `CREATE TABLE` 구문을 실제 `market_ticks` 테이블 스펙에 맞게 업데이트.
2. `save_orderbook` 호출 시 필요한 `market_orderbook` 테이블 생성 로직을 `init_db`에 추가.
3. 배포 환경의 DB 스키마와 코드를 동기화.

## Related
- Branch: `bug/ISSUE-033-timescale-archiver-fix`
- RFC: N/A (기존 로직 버그 수정)

## Failure Analysis (ZEVS)
- **Why did existing tests miss this?**: `test_smoke_modules.py`는 import 성공 여부만 체크하며, 런타임의 DB 연동 및 스키마 정합성은 체크하지 못함.
- **Regression Test ID**: `RT-033-TIMESCALE-SCHEMA-SYNC`
