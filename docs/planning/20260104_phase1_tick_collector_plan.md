# 구현 계획: 틱 데이터 수집기 (TickCollector)

## Goal
Upbit WebSocket API를 통해 실시간 체결 데이터를 수집하고, 정규화하여 Redis Pub/Sub으로 발행.

## Proposed Changes
- [NEW] `src/data_ingestion/ticks/collector.py`: Asyncio 기반 WebSocket 수집기
- [NEW] `tests/test_collector.py`: 정규화 로직 단위 테스트

## Verification
- pytest 실행 확인 (3 passed)
