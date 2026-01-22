# Failure Mode and Effects Analysis (FEMA)

이 문서는 `stock_monitoring` 시스템에서 발생했거나 발생 가능한 실패 모드(Failure Mode)를 분석하고, 이에 대한 영향도 및 대응 전략(복구/테스트)을 정의합니다.

## 1. 개요
- **목적**: 장애 발생 가능성을 사전에 인지하고, 발생 시 즉각적인 복구 및 테스트 케이스 확보.
- **분석 및 관리 워크플로우**:
    - **분석 (Idea/Logic)**: 새로운 실패 가능성 브레인스토밍은 **[`/brainstorm`](../../../.agent/workflows/brainstorm.md)**을 사용합니다.
    - **생애주기 (Test)**: 실패 모드에 대응하는 테스트 등록 및 검증은 **[`/manage-tests`](../../.agent/workflows/manage-tests.md)**를 따릅니다.

## 2. 실패 모드 분석 (FMEA Matrix)

| Category | Failure Mode | Impact (Effect) | Severity | Detection | Recovery / Countermeasures |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Broker** | `invalid tr_key` | 특정 시장(US/KR) 데이터 수집 불가 | High | Connection Logs | Dual-Socket 분리 및 엔드포인트 명세 엄수 |
| **Broker** | Head-of-Line Blocking | 호가 데이터 홍수로 인한 체결 데이터 지연/탈락 | Mid | Latency Monitoring | Dual-Socket 아키텍처 (Traffic Isolation) |
| **Broker** | ALREADY_IN_SUBSCRIBE | 재연결 시 구독 중복 오류로 데이터 수집 중단 | High | Error Logs | `cleanup_subscriptions()` (명시적 Unsubscribe) |
| **Broker** | Test Endpoint Illusion | 연결 성공 로그와 달리 실데이터 0건 | High | DB Row Count | Deep Verification (DB 직접 조회) 규칙 준수 |
| **System** | Silent Archiver Failure | 수집기는 정상이지만 DB 저장이 안 됨 (데이터 증발) | Critical | Sentinel (Rate limit 0) | `restart: unless-stopped` 및 Sentinel Alert |
| **System** | Secrets Missing | `KIS_APP_SECRET` 등 필수 환경변수 누락으로 수집 불가 | High | Startup Logs | 배포 체크리스트 강화 및 환경변수 유효성 검사 로직 |
| **System** | Disk Full | 아카이브 파일/로그 누적으로 인한 저장소 고갈 | Mid | Disk Monitoring | 7일 경과 데이터 자동 Drop 정책 (Retention Policy) |
| **System** | DB Synchronization Error | 환경변수 오설정으로 데이터가 2개 이상의 DB에 분산 저장 | Mid | DB Row Count Check | 환경별(Dev/Prod) DB URL 선언적 관리 및 로그 명시 |
| **Logic** | Sync Drift | Dual Socket 간 타임스탬프 불일치 | Low | Data Drift Analysis | Timezone Aware (KST) 처리 및 Gap Recovery |
| **Logic** | Real-time Gap | 네트워크 일시 순단으로 인한 데이터 누락 | Mid | Gap Detector | Real-time Gap Recovery (Rest API Fallback) |
| **Process** | Log Reliance Bias | "Success" 로그만 믿고 장애를 방치함 | Critical | Manual Inspection | Deep Verification Gate 및 Automated Smoke Test |
| **Process** | Environment Drift | 개발용 Config가 운영에 적용되어 의도치 않은 서비스 중단 | High | Startup Banner | 실행 시 환경 인디케이터 로그 출력 강제 |
| **Archiving** | System Metrics Type Mismatch | Sentinel이 발행한 메트릭 데이터 타입이 Archiver 스키마와 불일치 | Mid | Archiver Error Logs | 스키마 검증 테스트 및 Sentinel 발행 데이터 타입 검증 (TS-TYPE-01) |
| **Infrastructure** | Container DNS Resolution Failure | docker-compose.yml 호스트 이름 변경 후 DNS 해결 실패 | Critical | Startup Connection Errors | DNS resolution 테스트 및 network alias 검증 (INF-DNS-01) |
| **Infrastructure** | Partial Restart Network Inconsistency | 일부 컨테이너만 재시작 시 네트워크 alias 미적용 | High | Service Health Checks | Full stack restart policy 및 health check automation (INF-HEALTH-01) |

## 3. 상세 대응 전략

### 3.1 Sentinel "Dead Man's Switch" (Level 1)
- **Metric**: Redis `ticker.kr` & `orderbook.kr` 메시지 발생률.
- **Threshold**: 장중(09:00-15:30) 60초간 메시지 0건 시 즉시 경고 및 1단계 복구(Restart) 트리거.
- **Ref**: [Recovery Strategy](../../strategy/recovery_strategy.md)

### 3.2 Deep Verification Protocol (Level 2)
- 모든 배포 및 복구 작업 후에는 로그의 "Success" 메시지 대신 **DB 쿼리 결과(`SELECT COUNT(*)`)**를 최종 성공 기준으로 삼음.
- **Rule**: [ai-rules.md Section 2.1](../../../.ai-rules.md)

### 3.3 Data Layered Recovery (Level 3)
- 실시간 누락 발생 시 다음 순서로 복구 시도:
    1. **Raw Log (JSONL) Recovery**: 로컬에 저장된 로그 파일로부터 DB 재적재.
    2. **Broker REST API Recovery**: KIS/Kiwoom REST API를 통한 과거 데이터 보충.
    3. **Daily Triangulation**: 매일 장 종료 후 벤더 간 데이터 교차 검증 및 보정.

### 3.4 System Metrics Type Safety (Level 2)
- **문제**: Sentinel이 `system.metrics` 채널에 발행하는 데이터 구조가 Archiver의 예상 타입과 불일치
- **원인**: `meta` 필드를 dict로 발행하지만, Archiver가 일부 케이스에서 str로 기대
- **대응**:
    1. **Schema Validation Test (TS-TYPE-01)**: Sentinel 발행 데이터와 DB 스키마 타입 일치 검증
    2. **Pre-publish Validation**: Sentinel이 메트릭 발행 전 데이터 타입 검증
    3. **Archiver Error Handling**: 타입 불일치 시 에러 로깅 및 알림, 서비스 중단 방지

### 3.5 Infrastructure Network Resilience (Level 1)
- **문제**: docker-compose.yml 변경 후 컨테이너가 서비스 호스트를 찾지 못함
- **원인**:
    1. 호스트 이름 변경 시 DNS alias 미적용
    2. 부분 재시작으로 인한 네트워크 구성 불일치
- **대응**:
    1. **DNS Resolution Test (INF-DNS-01)**: 모든 컨테이너가 필수 호스트(timescaledb, redis)를 resolve할 수 있는지 검증
    2. **Network Alias Validation (INF-NET-01)**: docker-compose.yml의 alias 설정과 실제 네트워크 구성 일치 확인
    3. **Full Stack Restart Policy**: 인프라 변경 시 `make down && make up`을 통한 전체 재시작 강제
    4. **Startup Health Check (INF-HEALTH-01)**: 모든 서비스가 30초 내 정상 상태 도달 검증

## 4. 관련 문서
- [Runbook: Data Collection Recovery](../runbooks/data_collection_recovery.md)
- [Recovery Strategy](../../strategy/recovery_strategy.md)
- [Test Registry](test_registry.md)
