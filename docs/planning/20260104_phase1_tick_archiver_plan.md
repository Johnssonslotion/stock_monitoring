# 구현 계획: 틱 데이터 아카이버 (TickArchiver)

## Goal
Redis에서 실시간 틱 데이터를 구독하여 DuckDB에 Batch Insert로 영구 저장.

## Proposed Changes
- [NEW] `src/data_ingestion/ticks/archiver.py`: Batch Insert (100건 또는 1초 주기)
- [NEW] `tests/test_archiver.py`: DB 저장 검증

## Verification
- pytest 실행 확인 (2 passed)
- DuckDB 파일 생성 확인
