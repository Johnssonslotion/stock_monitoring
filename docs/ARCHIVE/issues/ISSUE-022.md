# Issue-022: [Bug] TickArchiver DuckDB 타입 변환 오류 수정

**Status**: Open  
**Priority**: P1  
**Type**: bug  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- Redis에서 전달되는 `int`/`float` 형태의 timestamp가 DuckDB의 `TIMESTAMP` 컬럼으로 저장될 때 `Conversion Error: Unimplemented type for cast (INTEGER -> TIMESTAMP)` 발생.
- 이로 인해 오늘 장중 DuckDB 적재가 전면 중단됨.

## Acceptance Criteria
- [ ] `TickArchiver` 내에서 모든 형태의 timestamp(int, float, str)를 ISO 8601 문자열 또는 `datetime` 객체로 정규화하여 저장.
- [ ] 장 종료 후 재시작 시 에러 없이 데이터 적재 확인.
