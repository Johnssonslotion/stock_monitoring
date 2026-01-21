# IDEA: Hybrid Storage Tiering (TimescaleDB + DuckDB)
**Status**: 💡 Seed
**Priority**: P1

## 1. 개요 (Abstract)
현재 시스템은 TimescaleDB와 DuckDB를 혼용하고 있으나, 명확한 역할 분담과 데이터 수명 주기(Lifecycle) 관리가 부족하다.
**TimescaleDB**를 고성능 실시간(Hot) 데이터 저장소로, **DuckDB(Parquet)**를 장기 보관 및 대용량 분석(Cold/Warm) 아카이브로 활용하는 **계층화된 스토리지 전략(Storage Tiering)**을 제안한다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: TimescaleDB는 최근 데이터(예: 30일) 처리에 최적화되어 있고, DuckDB는 압축률이 뛰어난 Parquet 파일을 기반으로 대용량 OLAP 처리에 강하다. 두 장점을 결합하면 비용과 성능을 모두 잡을 수 있다.
- **기대 효과**:
    - **TimescaleDB 경량화**: Retention Policy를 적용하여 최근 데이터만 유지, 쿼리 속도 유지 및 EBS 비용 절감.
    - **무제한 아카이빙**: DuckDB/s3 기반으로 과거 데이터를 저렴하게 영구 보관.
    - **분석 효율성**: Data Scientist는 DuckDB 파일만으로 로컬에서 무거운 백테스팅 수행 가능 (운영 DB 부하 Zero).

## 3. 계층화 전략 (Tiering Strategy)

### Tier 1: Hot Data (TimescaleDB)
- **Retention**: **최근 7일** (권장) ~ 최대 30일.
    - *이유*: 오라클 프리티어 스토리지(200GB Limit) 고려 시, Orderbook 데이터가 포함되면 용량이 급격히 증가함. 1주일 치 데이터면 실시간 차트 및 단기 지표 산출에 충분함.
- **Role**: 초단기 실시간 모니터링, 라이브 트레이딩 시그널 계산.

### Tier 2: Cold/Archive Data (DuckDB)
- **Retention**: **영구 (Permanent)**.
- **Scope**: **Full Raw Data (Tick & Orderbook)**.
    - *이유*: 백테스팅 시 체결 데이터(Tick)뿐만 아니라 당시의 시장 유동성(Orderbook) 정보가 필수적임. DuckDB/Parquet는 압축률이 높아(약 1/5 ~ 1/10) Raw Data 전체를 저장하기에 최적임.
- **Action**: 매일 자정, `D-8`일자 데이터를 TimescaleDB에서 추출 -> Parquet 변환 -> DuckDB 로딩 -> TimescaleDB Drop.

## 4. 구체화 세션 (Persona Feedback)
- **Architect**: "TimescaleDB의 `Tiered Storage` 기능을 쓰면 S3로 자동 이동되지만, DuckDB 포맷(Parquet)으로 직접 관리하는 것이 **Vendor Lock-in 탈피**와 **로컬 분석**에 유리함."
- **Data Scientist**: "환영함. 매번 DB 접속해서 `SELECT` 하는 것보다 S3에서 Parquet 긁어와서 로컬 DuckDB로 분석하는 게 훨씬 빠르고 편함."
- **DevOps**: "디스크 용량 알람에서 해방될 수 있음. 단, 'Move & Delete' 파이프라인의 안정성 검증(데이터 유실 방지)이 필수적임."

## 5. 데이터 접근 패턴 (Access Patterns)
**앱(Frontend)에서 7일 지난 데이터를 요청할 경우 어떻게 할 것인가?**

### A. 일반 차트 (Candle Chart) -> TimescaleDB (Long-Term)
- **전략**: `Raw Tick`은 삭제하더라도, 이를 집계한 **`1분/1시간/1일 봉(Candle)`** 데이터는 용량이 작으므로 TimescaleDB에 **영구(또는 5년)** 보관한다.
- **구현**: TimescaleDB의 `Continuous Aggregates` 기능 활용.
- **효과**: 사용자가 1년 치 차트를 조회해도 Tick을 뒤질 필요 없이 가벼운 Candle 테이블만 조회하므로 빠르고 간편함.

### B. 틱 정밀 조회 (Tick History) -> DuckDB (Direct Query)
- **전략**: 사용자가 과거 특정 시점의 **체결 내역(Tick)**이나 **호가창(Orderbook)**을 정밀하게 보고자 할 때만 DuckDB에 쿼리한다.
- **구현**: API 서버가 요청된 기간(`Current - 7days`)을 확인하고, 범위를 벗어나면 DuckDB 연결을 통해 Parquet 파일을 직접 조회하여 반환한다. (굳이 Timescale로 복원하지 않음)

## 6. 로드맵 연동 시나리오
- **Pillar 4 (Data Reliability)**: 아카이빙 파이프라인 구축.
- **ISSUE-025 (Recovery)**: 아카이브된 파일에서 DB로 역로딩하는 기능과 연계됨.
