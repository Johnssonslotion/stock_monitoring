# IDEA: Background Cross-Validation (5-min Interval)
**Status**: 💡 Seed
**Priority**: P2

## 1. 개요 (Abstract)
장 마감 후가 아닌, **장 중(Intraday)**에 백그라운드 워커를 통해 주기적(예: 5분 단위)으로 데이터 정합성을 검증하는 자동화 시스템을 구축한다. 이때, 빠른 집계 성능을 가진 **DuckDB**를 활용하여 시스템 부하를 최소화한다.

## 2. 문제 정의 (Problem)
- **Late Detection**: 현재 구조에서는 장 마감 후 또는 데이터가 완전히 비어있을 때만 문제를 인지할 수 있음 (오늘 사고 사례).
- **Recovery Cost**: 나중에 한꺼번에 복구하려면 API 호출량이 많아짐.

## 3. 제안 전략 (Solution)
### 3.1 5-Minute Sliding Verification
- **주기**: 매 5분마다 직전 5분 창(Window)에 대한 검증 수행.
- **Metric**: `Volume Cross-Check` (거래량 교차 검증) - ID-volume-cross-check.md 참조.
- **Backend**:
    1. **DuckDB**: 수집된 틱 데이터를 실시간으로 DuckDB에 적재(Archiver) 또는 주기적 Sync.
    2. **Aggregator**: DuckDB SQL을 사용하여 해당 5분의 `SUM(volume)` 계산 (매우 빠름).
    3. **Verifier**: Kiwoom/KIS 분봉 API 호출하여 거래량 비교.
    4. **Action**: 오차 발생 시 즉시 `Alert` 및 `Recovery` 트리거.

### 3.2 DuckDB 활용 (DuckDB-Centric)
- TimescaleDB 대신 DuckDB를 집계 엔진으로 사용하는 이유:
    - **OLAP 성능**: 집계 쿼리에 최적화됨.
    - **격리성**: 메인 트랜잭션 DB(Timescale)에 부하를 주지 않음.
    - **파일 기반**: 검증용 스냅샷을 뜨기 용이함.

## 4. 구체화 세션 (Elaboration)
- **Architecture**: `IntegrityWorker` 컨테이너 신설 필요.
- **Optimization**: DuckDB Write Lock 충돌 방지를 위해 `ReadOnly` 연결 또는 `WAL` 모드 적극 활용 필요.
- **Recovery**: 소규모(5분치) 누락 발견 시, 즉시 복구(Fresh Recovery)가 가능하므로 성공률 높음.

## 5. 로드맵 연동 시나리오
- **Phase 3 (Stability)** 항목으로 추가.
- `ID-dual-tick-recovery.md`와 연동하여 "감지(Detection) -> 복구(Recovery)" 파이프라인 완성.
