# Infrastructure & Database Rules

## 1. 인프라 원칙
-   **DB**:
    -   **General**: 상시 구동되는 RDBMS 사용 지양 (SQLite/DuckDB 권장).
    -   **Time-Series**: **TimescaleDB (PostgreSQL)** 허용. (틱 데이터의 효율적 압축 및 SQL 질의 지원을 위함).
-   **Queue**: Kafka 금지 (Redis Pub/Sub 사용).
-   **Log**: 파일 로깅은 최소화, 중요 에러만 기록.
-   **Docker Resource** (Single Server Strategy):
    -   **Rule**: **Environment-Based Pruning** (환경별 차등 적용).
    -   **Production (`make up-prod`)**: 배포 직후 `docker system prune -af` 자동 실행. (안정성 최우선, 미사용 캐시/이미지 즉시 제거).
    -   **Development (`make up-dev`)**: Prune 미실행 (빌드 캐시 유지, 빠른 반복 개발).
    -   **Common**: 디스크 사용량 80% 경고 발생 시 수동 Prune 실행.
    -   **Injection**: 모든 컨테이너는 `.env`로부터 `APP_ENV` (`production` | `development`) 변수를 주입받아, 코드 레벨에서 환경을 인지해야 함.

## 2. 실험 및 설정 원칙 (Experimentation & Config)
### 2.1 실험 격리 (Isolation)
-   **브랜치**: 실험은 오직 `exp/` 접두사가 붙은 브랜치에서만 수행한다. (예: `exp/new-scalping`)
-   **데이터**: 운영 DB(Redis/DuckDB)는 **Read-Only**로만 접근한다. 실험 결과는 별도 저장소(Redis Index 10+ 등)에 기록한다.
-   **배포 금지**: `exp/` 브랜치는 절대 운영 서버에 배포되지 않는다.

### 2.2 파라미터 통합 (Configuration)
-   **코드 분리**: 로직(Code)과 설정(Config)을 완벽히 분리한다. 하드코딩된 숫자는 허용하지 않는다.
-   **Config 관리**: 모든 파라미터는 `configs/` 디렉토리 내의 YAML/JSON 파일로 관리하며, `Pydantic` 모델로 검증한다.

### 2.3 테스트 리소스 제한 (Test Resource Limits) [NEW]
- **원칙**: 테스트는 운영 서비스(Prod)의 가용성을 침해해서는 안 된다.
- **제한값**: 모든 CI/Test 컨테이너는 **CPU 50% (0.5 vCPU)**, **Memory 512MB**를 초과할 수 없다.
- **강제**: `Makefile` 또는 CI 스크립트에서 `--cpus` 및 `--memory` 플래그로 강제한다.

## 3. 관찰 가능성 및 복구 (Observability & Recovery)
### 3.1 관찰 가능성 원칙 (Observability Principle)
**규칙**: 데이터 흐름 시스템은 **각 단계마다 측정 가능한 메트릭** 필수.

**Collector**: Metric `published_count`, Log 매 publish  
**Archiver**: Metric `received_count`, `saved_count` (유실 검증)  
**Redis 검증**: `docker exec stock-redis redis-cli PUBSUB NUMSUB "tick.*"`

### 3.2 디버깅 도구 필수 (Production Debugging Tools)
**규칙**: Docker 환경에 **디버깅 명령어** 포함 (`make debug-*`).
**예시**: `make debug-pubsub` → 구독자 0명 발견 → 5분 만에 해결.

### 3.3 둠스데이 프로토콜 (Doomsday Protocol - Automated Failover) [CRITICAL]
**원칙**: "인간의 개입이 필요한 장애 복구는 장애다."
- **Trigger**: 운영 시간(Market Hours) 중 **60초 이상 데이터 유입 0건** (Dead Man's Switch).
- **Action**:
    1. **Level 1**: 컨테이너 강제 재시작 (Restart).
    2. **Level 2**: 5분 내 재발 시, **안전 모드(Single Socket Legacy)**로 자동 전환 (Degrade Mode).
- **Mandate**: 모든 수집기는 이 프로토콜을 준수하는 `Self-Healing` 기능을 탑재해야 한다.

## 4. 검증된 데이터베이스 구조 (Verified DB Schema) [2026-01-12]

### 4.1 TimescaleDB 스키마
**테이블**: `market_ticks` (Hypertable)
```sql
CREATE TABLE market_ticks (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    change DOUBLE PRECISION
);
SELECT create_hypertable('market_ticks', 'time', if_not_exists => TRUE);
CREATE INDEX market_ticks_time_idx ON market_ticks (time DESC);
```

**검증 상태**:
- ✅ 2026-01-12: 644,406건 수집 성공
- ✅ 실시간 Tick 데이터 수집 정상
- ✅ TimescaleDB Hypertable 압축 정상 작동

### 4.2 Redis Pub/Sub 구조
**검증된 채널**: `ticker.kr`, `ticker.us`, `market_ticker` (Legacy)
**Archiver 구독 패턴**: `psubscribe("ticker.*")`

**중요 제약사항**:
- ⚠️ **KIS API 키 제한**: Single Approval Key = Single WebSocket.
- ⚠️ **Dual Socket 불가**: Key 중복 에러 발생.
- ✅ **해결책**: Single Socket Mode + Tick 전용 수집.

**Redis Config**: `config:enable_dual_socket = "false"`

### 4.3 Raw Logger
- **Retention**: 120시간. 최소 48시간(2일) 보존 필수.
- **규칙**: 디스크 부족 시에도 최소 2일치 로그 삭제 금지.

## 5. API 및 보안 원칙 (API & Security Standard) [NEW]

### 5.1 REST API 설계
- **프레임워크**: `FastAPI` + Pydantic.
- **버전 관리**: `/api/v1/...`.

### 5.2 보안 및 인증
- **접근 제어**: **JWT** 또는 **API-Key** 인증 필수.
- **가용성**: 경량 인증 권장 (Zero-Cost).
- **CORS**: White-list 방식 유지.
