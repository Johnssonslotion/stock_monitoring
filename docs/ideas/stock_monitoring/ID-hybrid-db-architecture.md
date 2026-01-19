# IDEA: Hybrid DB Architecture (TimescaleDB → DuckDB)

**Status**: 💡 Seed (Idea)  
**Priority**: P2 (Discussion)  
**Category**: Infrastructure / Architecture  
**Source**: User (2026-01-19)

## 1. 개요 (Abstract)

사용자의 피드백("2GB 메모리는 무결성을 위해 투자할 가치가 있다", "시스템 메트릭 모니터링 용도")을 반영하여, **TimescaleDB(Hot/Real-time)**와 **DuckDB(Cold/Analytics)**를 병행하는 **Hybrid Architecture**를 심도 있게 재검토합니다.

## 2. 가설 및 기대 효과

### 가설 (Revised)
1. **역할 분담**: TimescaleDB는 최근 1~7일치 **Hot Data**와 **System Metrics**를 실시간 관리하고, DuckDB는 전체 과거 데이터와 **Deep Analytics**를 담당한다.
2. **이중 무결성 (Double Integrity)**: 두 DB에 동시에 틱을 적재함으로써, 한쪽이 실패해도 데이터가 보존되는 **Redundancy** 효과를 얻는다.
3. **Aggregation 효율성**:
   - 실시간 차트/모니터링: TimescaleDB `Continuous Aggregates` (우수)
   - 복잡한 다중 봉(15분, 4시간 등) 및 백테스트: DuckDB SQL (유연성 우수)

### 기대 효과
- **운영 안정성**: 시스템 메트릭과 실시간 틱이 TimescaleDB에 안정적으로 저장됨.
- **분석 성능**: 무거운 쿼리는 DuckDB에서 실행하여 실시간 DB 부하 분산.
- **데이터 완전성**: 이중 저장을 통한 유실 위험 최소화.

## 3. 구체화 세션 (Persona Workshop: Round 2)

### 🏗️ Architect
> "Dual Write 아키텍처는 엔터프라이즈급 무결성 패턴입니다. 2GB 메모리로 '이중화'와 '실시간성'을 모두 얻는다면 가성비가 훌륭합니다. **TimescaleDB는 실시간 버퍼(Buffer)** 역할을, **DuckDB는 데이터 호수(Lake)** 역할을 맡기면 됩니다."

### � Data Scientist
> "DuckDB로도 `time_bucket` 집계가 가능하지만, **실시간 스트리밍 데이터**에 대한 Window Function은 TimescaleDB가 훨씬 성숙합니다. 특히 5분봉, 1시간봉 등 **다중 Timeframe**을 실시간으로 말아 올리는 건 TimescaleDB의 전공 분야입니다."

### � DevOps Lead
> "Docker 컨테이너가 하나 더 떠 있다고 해서 무조건 나쁜 건 아닙니다. 이미 모니터링 시스템(Grafana 등)이 TimescaleDB를 바라보고 있다면, 이를 걷어내는 비용이 유지하는 비용보다 큽니다. **유지합시다.**"

### 👨‍� PM (Product Manager)
> "사용자님의 의도가 명확합니다. '무결성 > 리소스 절약'입니다. 틱 데이터는 우리의 자산입니다. **Hybrid 구조로 가되, 두 DB 간의 데이터 동기화(Sync) 전략만 확실히 정의**해주십시오."

## 4. 기술적 검토 (DuckDB Aggregation vs TimescaleDB Aggregation)

| Feature | TimescaleDB | DuckDB | Hybrid 전략 |
| :--- | :--- | :--- | :--- |
| **실시간 1분봉** | `Continuous Aggregates` (자동/즉시) | SQL `GROUP BY` (배치/수동) | **TimescaleDB 담당** (차트용) |
| **다중 Timeframe**| 5m, 1h, 1d 등 계층적 정의 용이 | 쿼리 시점에 계산 (On-demand) | **상호 보완** (실시간: TSDB, 과거: DuckDB) |
| **메모리 효율** | Shared Buffers 점유 | 쿼리 실행 시에만 사용 | DuckDB는 Batch 처리에 집중 |
| **복구(Recovery)**| WAL, Replication | 파일 백업 | **Daily Recovery는 DuckDB 기준 수행** |

## 5. 결론 및 제안 (Revised)

**Hybrid Architecture 채택을 권장합니다.**

**아키텍처 변경안**:
1. **Collector**: Redis로 틱 발행 (기존 동일)
2. **Timescale Archiver**: 실시간 틱 & 메트릭 저장 (Hot Data, 모니터링용)
   - 유지 기간: 최근 7~30일 (Retention Policy 적용)
   - 목적: 실시간 차트, 시스템 관제
3. **DuckDB Archiver (New)**: 배치 틱 저장 (Cold Data, 분석용)
   - 유지 기간: 영구 (Permanent)
   - 목적: 백테스팅, ML 학습, Daily Integrity Check
4. **Daily Recovery**:
   - 장 마감 후 DuckDB 데이터 기준으로 KIS/Kiwoom 검증 수행
   - 누락 발견 시 DuckDB와 TimescaleDB 양쪽에 보정(Upsert) (선택 사항, DuckDB만 해도 무방)

**질문 답변: "DuckDB로 다중 Agg가 무난한가?"**
- **가능은 합니다.** 하지만 실시간으로 계속 들어오는 데이터에 대해 여러 주기의 봉(1m, 3m, 5m, 1h...)을 매번 계산하는 것은 DuckDB보다 **TimescaleDB가 훨씬 효율적이고 간편**합니다. (Materialized View 기능 활용)


## 6. 로드맵 연동
- 이 아이디어는 채택되지 않을 경우 **Deferred Work**로 이동하거나 폐기됩니다.
