# IDEA: Network-Independent Logic Verification Strategy (Local-First)
**Status**: 💡 Seed
**Priority**: P1

## 1. 개요 (Abstract)
현재 실제 인스턴스(KIS/Kiwoom) 연결이 불가능하거나 제한적인 로컬 개발 환경에서, 순수 논리(Pure Logic) 검증만으로 해결할 수 있는 고부가가치 이슈들을 식별하고 해결 전략을 수립한다. 이는 'Data First' 및 'High Performance' 원칙을 준수하며, 운영 환경 배포 시 안정성을 담보하는 기초가 된다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: 데이터 파이프라인의 변환 로직(Type Casting), 의존성 검증(Smoke Test), 파일 파싱(Log Recovery)은 외부 네트워크 없이도 Mocking과 Sample Data만으로 100% 검증 가능하다.
- **기대 효과**:
    - **Zero Cost**: 외부 API 호출 비용 없이 로직 결함 수정.
    - **Speed**: 네트워크 레이턴시 없는 고속 반복 테스트(Loop) 가능.
    - **Stability**: 배포 전 'Logical Defect' 사전 제거.

## 3. 대상 이슈 및 공략 전략 (Target Issues)

### A. ISSUE-022: TickArchiver DuckDB Type Conversion (High Priority)
- **문제**: Redis에서 오는 데이터 타입(str/int/float)이 DuckDB Schema(TIMESTAMP)와 불일치.
- **로컬 해결 전략**:
    - `tests/test_duckdb_conversion.py` 신규 작성.
    - 다양한 Edge Case(Null, Int Timestamp, ISO String, Float Timestamp)를 포함한 Mock 딕셔너리 생성.
    - `DuckDBArchiver._convert_type()` 메서드 단위 테스트 수행.
    - **필요 리소스**: 로컬 DuckDB 파일 (`:memory:` 모드 권장).

### B. ISSUE-025: Raw Log (JSONL) Recovery Script (High Priority)
- **문제**: 누락된 틱 데이터를 파일(JSONL)에서 다시 읽어 복구해야 함.
- **로컬 해결 전략**:
    - `data/raw/sample_tick.jsonl` 샘플 파일 생성 (10~20라인).
    - 파싱 로직(`LogParser`) 구현 및 `On Conflict Do Nothing` 쿼리 생성 로직 검증.
    - 실제 DB Insert 대신 SQL 생성 결과만 검증하는 'Dry Run' 모드 개발.
    - **필요 리소스**: 샘플 JSONL 파일.

### C. ISSUE-027: Smoke Test (Development Efficiency)
- **문제**: 배포 후 모듈 임포트 에러 발생 빈번.
- **로컬 해결 전략**:
    - `tests/test_smoke_modules.py` 작성.
    - 주요 라이브러리(`httpx`, `pandas`, `redis`, `sqlalchemy` 등) 및 내부 모듈(`src.*`) 임포트 시도.
    - `pytest`로 실행하여 1초 이내 통과 여부 확인.
    - **필요 리소스**: `poetry` 환경.

### D. ISSUE-024: Recovery Worker Dependency
- **문제**: `httpx` 누락.
- **로컬 해결 전략**:
    - `ISSUE-027`의 Smoke Test에 `import httpx` 추가.
    - `poetry add httpx` 수행 및 `lock` 파일 갱신.

## 4. 구체화 세션 (Persona Feedback)
- **Architect**: "ISSUE-022의 DuckDB 타입 문제는 스키마 유연성을 위해 가장 시급함. 로컬에서 `:memory:` DB로 테스트하면 빠름."
- **Data Scientist**: "ISSUE-025는 데이터 무결성 복구를 위해 필수적임. 파싱 로직의 정규표현식 최적화도 로컬에서 진행해야 함."
- **DevOps**: "ISSUE-027 Smoke Test는 CI 파이프라인의 필수 관문임. 로컬에서 먼저 돌려보고 커밋하는 문화를 만들어야 함."

## 5. 로드맵 연동 시나리오
- **Pillar 2 (System Stability)**: ISSUE-022, ISSUE-024, ISSUE-027
- **Pillar 4 (Data Reliability)**: ISSUE-025
