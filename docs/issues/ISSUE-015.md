# ISSUE-015: 데이터 누락 자동 보완 (Data Gap Auto-Completion)

**Status**: Open
**Priority**: P1
**Type**: feature
**Created**: 2026-01-19
**Assignee**: Developer

## Problem Description
네트워크 지연, 소켓 연결 불안정, 또는 시스템 장애로 인해 수집된 틱(Tick) 데이터에 누락(Gap)이 발생할 수 있습니다. 현재 시스템은 `Doomsday Check`를 통해 완전 중단(0건)은 감지하지만, 시퀀스 중간의 미세한 누락(Sequence Skip)은 감지하지 못하며, 사후 복구 로직이 부재합니다.

## Acceptance Criteria
- [ ] **Integrity Checker**: 특정 종목/시간대의 데이터 연속성을 검증하여 누락 여부 판별.
- [ ] **Gap Detection**: 누락된 데이터 구간(`start_time` ~ `end_time`)을 정확히 식별.
- [ ] **Data Recovery**: 키움 `opt10079`(주식틱차트조회) TR을 활용하여 누락 구간 데이터 확보.
- [ ] **Deduplication**: 복구된 데이터를 DuckDB에 병합할 때 중복 데이터 방지 (Upsert/Ignore).
- [ ] **Scheduler**: 장 마감 후 또는 유휴 시간에 복구 작업이 자동으로 수행되어야 함.

## Resolution Plan
1. **Gap Analysis Logic 구현**:
   - `src/monitoring/integrity_checker.py` 생성.
   - DuckDB 쿼리를 통해 시퀀스/타임스탬프 기반 누락 감지.
2. **Recovery Worker 구현**:
   - `src/recovery/recovery_worker.py` 생성.
   - 누락 리포트를 기반으로 키움 API 요청 스케줄링.
3. **Integration**:
   - `master_roadmap.md` Pillar 2 (Data Integrity) 연동.
   - Sentinel 서비스와 연동하여 필요 시 즉시 복구(Hotfix) 또는 배치 복구 트리거.

## Related
- Idea: [ID-data-recovery-auto-completion](../ideas/stock_backtest/ID-data-recovery-auto-completion.md)
- Backlog: `Failure Mode Auto Recovery` (P2)
