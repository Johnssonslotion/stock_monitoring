# Issue-025: [Feature] Raw Log (JSONL) 기반 DB 복구 스크립트 개발

**Status**: Open  
**Priority**: P1  
**Type**: feature  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- 오늘(2026-01-20) 장중 아카이버 장애로 인해 누락된 데이터를 `data/raw/`에 저장된 JSONL 파일로부터 추출하여 DB에 후행 적재해야 함.

## Acceptance Criteria
- [ ] KIS/Kiwoom 원본 로그 파싱 엔진 구현.
- [ ] 파싱된 데이터를 DuckDB 및 TimescaleDB에 중복 없이(On Conflict Do Nothing) 적재하는 기능.
- [ ] 복구 후 DB 건수와 로그 파일 라인 수 비교 검증.
