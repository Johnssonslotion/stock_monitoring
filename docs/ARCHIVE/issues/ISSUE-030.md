# ISSUE-030: [Strategy] Data Management & Hybrid Storage Tiering Policy

**Status**: Done  
**Priority**: P1  
**Type**: policy  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- TimescaleDB와 DuckDB가 역할 구분 없이 중복 데이터를 저장하고 있음.
- 데이터 보관 주기(Retention) 및 수명 주기 정책이 문서화되지 않음.
- `data_acquisition_strategy.md`가 획득에만 초점이 맞춰져 있어 전반적인 관리 전략 부재.

## Solution
- **Hybrid Storage Tiering**: Hot(TimescaleDB/7일) vs Cold(DuckDB/영구) 전략 수립.
- **Documentation**: `data_acquisition_strategy.md`를 `data_management_strategy.md`로 통합 및 개편.
- **Governance**: Infrastructure 및 Database Spec 문서에 새로운 정책 반영.

## Acceptance Criteria
- [x] `docs/data_management_strategy.md` 생성 (Acquisition + Storage + Retention 통합).
- [x] `docs/ideas/stock_monitoring/ID-hybrid-storage-tiering.md` 작성.
- [x] 관련 문서(`infrastructure.md`, `database_specification.md`) 링크 및 정책 업데이트.
