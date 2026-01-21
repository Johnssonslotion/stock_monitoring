# ISSUE-036: [Task] DB 통합 및 스키마 정합성 복구
**Status**: [x] Done
**Priority**: P0
**Type**: task
**Created**: 2026-01-21
**Assignee**: Developer

## Problem Description
- **DB 분산 저장**: `.env` 오류로 `stock_test`와 `stockval`에 데이터가 쪼개짐.
- **Schema Mismatch**: `market_orderbook` 테이블이 마이그레이션(ARRAY)과 아카이버(43컬럼) 간 불일치.
- **Metadata Loss**: 수집기 모델에서 `broker`, `received_time` 등 필수 필드 누락.
- **Governance Gap**: AI가 `migrate.sh` 체계를 인식하지 못하고 독자적인 DDL을 시도함.

## Acceptance Criteria
- [x] `stock_test` → `stockval` 데이터 마이그레이션 전략 수립 (유저 수행)
- [x] 마이그레이션 004번(Orderbook)을 실제 DB 구조와 100% 동기화
- [x] 아카이버 내 하드코딩된 DDL 제거 및 `migrate.sh` 권한 위임
- [x] 수집기 모델(`KiwoomTickData`, `MarketData`) 메타데이터 보강
- [x] **Constitution Law #10 (Time Determinism)** 신설 및 `datetime.now()` 처리 표준화
- [x] `stockval` DB 정합성(Status: MATCH) 확인

## Resolution Details
1. **004_add_market_orderbook.sql**: 실제 운영 DB의 43컬럼 구조로 보정하여 SSoT 확보.
2. **timescale_archiver.py**: `init_db`에서 DDL을 제거하고 존재 여부만 검증하도록 수정.
3. **Law #10**: 타임스탬프 핀닝(Pinning) 패턴을 절대 거버넌스로 격상하여 파편화 방지.
4. **ADR-005, 007, 008**: 인식 실패 사후 분석 및 Triple-Lock 원칙 문서화.

## Related
- ISSUE-033: TimescaleDB Schema Mismatch (Resolved)
- Branch: `fix/ISSUE-036-recovery`

## Notes

- 18시간 gap은 별도 복구 불가 (원본 데이터 없음)
- 마이그레이션 시 중복 데이터 주의 (time + symbol + sequence_number 기준)
