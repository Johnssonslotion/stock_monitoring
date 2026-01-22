# ISSUE-031: [Feature] 하이브리드 데이터 복구 (로그 기반 + REST 백필)

**상태**: Open
**우선순위**: P1
**유형**: Feature
**생성일**: 2026-01-20
**담당자**: Developer

## 문제 정의 (Problem Description)
현재 데이터 수집 시스템은 네트워크 불안정 등으로 인해 간헐적인 데이터 누락이 발생합니다.
기존의 복구 도구(`backfill_manager.py`, `gap_filler.py`)는 통합되어 있지 않으며, 가장 세밀한 데이터 원천인 Raw Log (JSONL)를 활용하지 못하고 있습니다.
따라서 로컬 리소스(로그)를 우선적으로 활용하고, 복구되지 않은 구간에 대해서만 외부 API를 사용하는 효율적인 "하이브리드 복구 시스템"이 필요합니다.

## 목표 (Goals)
1.  **1차 복구 (Primary)**: Raw JSONL 로그 파일에서 틱 데이터를 파싱하여 복구합니다. (API 호출 0)
2.  **2차 복구 (Secondary)**: 1차 복구 후에도 DuckDB 상에 비어있는 분(Minute) 단위를 감지하여, 해당 구간만 KIS REST API로 백필합니다.
3.  **오케스트레이션**: 이 모든 과정을 단일 명령어로 수행할 수 있는 통합 진입점을 제공합니다.

## 기술적 상세 (Technical Details)
-   **로그 포맷**: `logs/ticks_YYYYMMDD.jsonl` (예상) 또는 `data/logs/...`
-   **데이터베이스**: DuckDB (`market_ticks` 테이블)
-   **API**: KIS `inquire-time-itemconclusion` (TR: FHKST01010300)

## 구현 계획 (Implementation Plan)
### 1. 로그 복구 모듈 (`src/data_ingestion/recovery/log_recovery.py`)
-   JSONL 파일 파싱 로직 구현
-   DuckDB Bulk Insert 최적화
-   오류 데이터 로깅 및 건너뛰기

### 2. 하이브리드 백필 매니저 (`src/data_ingestion/recovery/backfill_manager.py` 개선)
-   기존 REST API 백필 로직에 "누락 구간 감지" 기능 추가
-   `calculate_missing_intervals(symbol, date)` -> `fetch_ticks(intervals)`

### 3. 통합 워커 (`src/data_ingestion/recovery/orchestrator.py`)
-   `run_recovery(date, symbols)` 함수 제공
-   [Logs] -> [Gap Check] -> [REST API] 순차 실행

## 검증 계획 (Verification)
-   **로그 복구 테스트**: 샘플 JSONL 파일을 생성하고 DuckDB 적재 여부 확인
-   **하이브리드 테스트**: 일부러 로그에 구멍을 낸 뒤, REST API가 해당 구간만 호출하는지 확인 (Mock 활용)
