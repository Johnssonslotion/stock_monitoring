# API Hub v2 Configuration Specification

**Project**: ISSUE-037  
**Version**: 1.0  
**Status**: Official  
**Authority**: Council of Six (2026-01-23)  
**Last Updated**: 2026-01-23

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Configuration File Location](#configuration-file-location)
3. [Worker Configuration](#worker-configuration)
4. [Queue Configuration](#queue-configuration)
5. [Circuit Breaker Configuration](#circuit-breaker-configuration)
6. [Provider Configuration](#provider-configuration)
7. [Token Manager Configuration](#token-manager-configuration)
8. [Rate Limiter Configuration](#rate-limiter-configuration)
9. [Monitoring Configuration](#monitoring-configuration)
10. [Testing Configuration](#testing-configuration)
11. [Environment Variable Overrides](#environment-variable-overrides)
12. [Configuration Best Practices](#configuration-best-practices)

---

## Overview

본 문서는 API Hub v2의 모든 설정 옵션에 대한 **단일 참조 문서(Single Source of Truth)**입니다.

### 설계 원칙

1. **YAML First**: 기본 설정은 `configs/api_hub_v2.yaml`에 정의
2. **Env Override**: 민감 정보 및 배포별 설정은 환경변수로 주입
3. **Type Safety**: Pydantic 모델을 통한 런타임 검증
4. **Default Fallback**: 파일이 없어도 기본값으로 동작

### 관련 문서

- **Implementation**: `src/api_gateway/hub/config.py` (HubConfig 클래스)
- **Config File**: `configs/api_hub_v2.yaml` (85 lines)
- **Overview**: `docs/specs/api_hub_v2_overview.md#configuration`
- **Tests**: `tests/unit/test_api_hub_config.py` (23 tests)
- **Ground Truth**: `docs/governance/ground_truth_policy.md#5-api-hub-v2-configuration`

---

## Configuration File Location

| Environment | Path | Override Method |
|-------------|------|-----------------|
| **Default** | `configs/api_hub_v2.yaml` | N/A |
| **Custom** | User-defined | `HUB_CONFIG_PATH` env var |
| **Docker** | `/app/configs/api_hub_v2.yaml` | Volume mount |
| **Test** | In-memory (temp file) | `HubConfig(config_path=...)` |

**Example**:
```bash
# Use custom config
HUB_CONFIG_PATH=/path/to/custom.yaml python -m src.api_gateway.hub

# Docker override
docker run -e HUB_CONFIG_PATH=/app/configs/prod_hub.yaml ...
```

---

## Worker Configuration

### Section: `api_hub.worker`

Worker의 핵심 동작 파라미터를 정의합니다.

| Parameter | Type | Default | Description | Rationale |
|-----------|------|---------|-------------|-----------|
| `redis_url` | string | `redis://localhost:6379/15` | Redis 연결 URL (DB 15 격리) | Queue와 response 캐시를 위한 전용 DB |
| `enable_mock` | bool | `true` | Mock 모드 활성화 | Phase 1: true, Phase 2: false |
| `max_retries` | int | `3` | 태스크 재시도 최대 횟수 | 일시적 실패 대응, 무한 루프 방지 |
| `timeout` | float | `10.0` | 태스크 타임아웃 (초) | Broker API 평균 응답 시간 고려 |
| `batch_size` | int | `100` | 병렬 처리 최대 태스크 수 | 메모리 제약 및 처리량 균형 |
| `shutdown_timeout` | float | `5.0` | 종료 대기 시간 (초) | 진행 중 태스크 완료 대기 |

**Authority**: 
- `enable_mock`: Council Phase 1 승인 (2026-01-23)
- `timeout`: Broker API 벤치마크 (KIS: 평균 2.3s, Kiwoom: 평균 1.8s)
- `max_retries`: ISSUE-037-A BaseAPIClient Spec

**Environment Overrides**:
```bash
REDIS_URL=redis://prod:6379/15
ENABLE_MOCK=false
HUB_MAX_RETRIES=5
HUB_TIMEOUT=15.0
```

**Usage**:
```python
from src.api_gateway.hub.config import hub_config

redis_url = hub_config.get("worker.redis_url")
is_mock = hub_config.is_mock_enabled()
```

---

## Queue Configuration

### Section: `api_hub.queues`

Redis 큐 설정 및 우선순위 정책을 정의합니다.

| Parameter | Type | Default | Description | Rationale |
|-----------|------|---------|-------------|-----------|
| `priority` | string | `api:priority:queue` | 우선순위 큐 키 | 긴급 요청 (체결 조회 등) 우선 처리 |
| `normal` | string | `api:request:queue` | 일반 큐 키 | 정기 조회 및 백그라운드 작업 |
| `response_ttl` | int | `3600` | 응답 캐시 TTL (초) | 중복 요청 방지, 1시간 유효 |
| `max_queue_size` | int | `10000` | 큐 최대 크기 | 메모리 보호, 과부하 감지 |

**Authority**:
- Priority Queue Design: ISSUE-037 Phase 1 Architecture
- TTL: 분봉 데이터 갱신 주기 (1분) × 안전 계수 (60)

**Queue Priority Logic**:
```python
# RestApiWorker 내부 로직 (src/api_gateway/hub/worker.py:161)
result = await queue_manager.redis.blpop(
    [PRIORITY_QUEUE, NORMAL_QUEUE],  # 우선순위 순서
    timeout=1
)
```

**Environment Overrides**:
```bash
HUB_PRIORITY_QUEUE=api:urgent:queue
HUB_NORMAL_QUEUE=api:batch:queue
HUB_RESPONSE_TTL=7200
```

---

## Circuit Breaker Configuration

### Section: `api_hub.circuit_breaker`

API 장애 격리를 위한 Circuit Breaker 임계값을 정의합니다.

| Parameter | Type | Default | Description | Rationale |
|-----------|------|---------|-------------|-----------|
| `failure_threshold` | int | `5` | Circuit 오픈 임계값 (연속 실패 수) | Broker API 간헐적 장애 허용 |
| `recovery_timeout` | float | `30.0` | Half-Open 전환 대기 시간 (초) | API 서버 복구 시간 고려 |
| `half_open_max_calls` | int | `3` | Half-Open 상태 테스트 호출 수 | 점진적 복구 검증 |
| `success_threshold` | int | `2` | Circuit 닫힘 임계값 (연속 성공 수) | 안정성 확인 |

**Authority**:
- Design: Martin Fowler's Circuit Breaker Pattern
- Thresholds: ISSUE-037 Phase 1 Integration Tests (4/4 passing)
- Recovery Timeout: Broker API SLA (99.5% uptime, 평균 장애 지속 30초)

**State Transitions**:
```
CLOSED → OPEN: failure_count >= failure_threshold
OPEN → HALF_OPEN: recovery_timeout 경과
HALF_OPEN → CLOSED: success_count >= success_threshold
HALF_OPEN → OPEN: 1회 실패
```

**Environment Overrides**:
```bash
HUB_CB_FAILURE_THRESHOLD=10  # 더 관대하게
HUB_CB_RECOVERY_TIMEOUT=60.0  # 더 긴 복구 대기
```

**Monitoring**:
- Circuit Open 시 `monitoring.alert_on_circuit_open=true`이면 알림 발송
- Metric: `circuit_breaker_state{provider="KIS"}` (Prometheus)

---

## Provider Configuration

### Section: `api_hub.providers.<PROVIDER_NAME>`

증권사별 API 설정 및 Rate Limit을 정의합니다.

### KIS (Korea Investment & Securities)

| Parameter | Type | Default | Description | Authority |
|-----------|------|---------|-------------|-----------|
| `enabled` | bool | `true` | Provider 활성화 여부 | Phase 2 구현 상태 |
| `base_url` | string | `${KIS_BASE_URL}` | API Base URL | [KIS OpenAPI 공식 문서](https://apiportal.koreainvestment.com) |
| `timeout` | float | `10.0` | 요청 타임아웃 (초) | KIS API 평균 응답 시간 + 2σ |
| `rate_limit.requests_per_second` | int | `20` | 초당 요청 제한 | **Ground Truth**: KIS API 공식 Rate Limit (20 req/s) |
| `rate_limit.burst` | int | `5` | Burst 허용량 | 단기 급증 허용, Token Bucket 알고리즘 |
| `retry.max_attempts` | int | `3` | 재시도 최대 횟수 | Circuit Breaker와 협동 |
| `retry.backoff_factor` | float | `2.0` | Exponential Backoff 계수 | 1초 → 2초 → 4초 |

### KIWOOM (Kiwoom Securities)

| Parameter | Type | Default | Description | Authority |
|-----------|------|---------|-------------|-----------|
| `enabled` | bool | `true` | Provider 활성화 여부 | Phase 2 구현 상태 |
| `base_url` | string | `${KIWOOM_API_URL}` | API Base URL | Kiwoom REST API 문서 |
| `timeout` | float | `10.0` | 요청 타임아웃 (초) | Kiwoom API 평균 응답 시간 + 2σ |
| `rate_limit.requests_per_second` | int | `10` | 초당 요청 제한 | **Ground Truth**: Kiwoom API 공식 Rate Limit (10 req/s) |
| `rate_limit.burst` | int | `3` | Burst 허용량 | KIS보다 보수적 설정 |
| `retry.max_attempts` | int | `3` | 재시도 최대 횟수 | Circuit Breaker와 협동 |
| `retry.backoff_factor` | float | `2.0` | Exponential Backoff 계수 | 1초 → 2초 → 4초 |

**Authority**:
- **Rate Limits**: `docs/governance/ground_truth_policy.md` (Section 5.1)
- **Retry Logic**: ISSUE-037-A BaseAPIClient Spec
- **Timeout**: Broker API Benchmarks (2026-01-20 측정)

**Environment Overrides**:
```bash
KIS_BASE_URL=https://openapi.koreainvestment.com:9443
KIWOOM_API_URL=https://api.kiwoom.com
```

**Extensibility**:
새 Provider 추가 시 동일한 구조로 정의:
```yaml
providers:
  LS:  # LS증권
    enabled: true
    base_url: "${LS_API_URL}"
    timeout: 10.0
    rate_limit:
      requests_per_second: 15
      burst: 5
    retry:
      max_attempts: 3
      backoff_factor: 2.0
```

---

## Token Manager Configuration

### Section: `api_hub.token_manager`

OAuth 토큰 자동 갱신 정책을 정의합니다 (Phase 2).

| Parameter | Type | Default | Description | Rationale |
|-----------|------|---------|-------------|-----------|
| `redis_key_prefix` | string | `api:token:` | Token 저장 키 접두사 | Provider별 격리: `api:token:KIS`, `api:token:KIWOOM` |
| `auto_refresh_margin` | int | `300` | 자동 갱신 마진 (초, 5분) | 만료 전 여유 시간, Clock Skew 대응 |
| `max_refresh_retries` | int | `3` | 갱신 실패 재시도 횟수 | Network 장애 허용 |
| `refresh_backoff_factor` | float | `2.0` | Exponential Backoff 계수 | 1초 → 2초 → 4초 |
| `token_ttl_buffer` | int | `60` | TTL 안전 버퍼 (초, 1분) | Redis 만료와 실제 토큰 만료 간 Gap |

**Authority**:
- Design: ISSUE-037-C Token Manager Spec (200+ lines)
- Refresh Margin: OAuth 2.0 Best Practices (RFC 6749)
- TTL Buffer: Clock Skew 허용 (NTP ±1초 × 60)

**Token Lifecycle**:
```
1. Issue: POST /oauth2/token
2. Store: SETEX api:token:KIS <token> <ttl>
3. Auto-Refresh: TTL < auto_refresh_margin일 때 자동 갱신
4. Expiry: TTL = 0 시 재발급
```

**Environment Overrides**:
```bash
HUB_TOKEN_PREFIX=oauth:token:
HUB_TOKEN_REFRESH_MARGIN=600  # 10분 전 갱신
```

---

## Rate Limiter Configuration

### Section: `api_hub.rate_limiter`

Redis Gatekeeper 기반 Global Rate Limiting 설정을 정의합니다 (Phase 2).

| Parameter | Type | Default | Description | Rationale |
|-----------|------|---------|-------------|-----------|
| `redis_url` | string | `redis://redis-gatekeeper:6379/0` | Rate Limiter 전용 Redis | 물리적 분리 (Council 2차 결정) |
| `enabled` | bool | `true` | Rate Limiting 활성화 | Production 필수, Dev 선택 |
| `global_limit` | int | `50` | 전체 Provider 통합 제한 (req/s) | KIS(20) + Kiwoom(10) + 여유(20) |
| `per_provider_limit` | bool | `true` | Provider별 개별 제한 적용 | `providers.*.rate_limit` 참조 |
| `algorithm` | string | `sliding_window` | Rate Limit 알고리즘 | 정확도 vs 성능 균형 |
| `rejection_ttl` | int | `60` | Rejection 기록 TTL (초) | 통계 및 디버깅용 |

**Authority**:
- Redis Gatekeeper: `deploy/docker-compose.yml:21` (Council 2차 결정)
- Algorithm: ISSUE-037-D Rate Limiter Integration Plan
- Global Limit: Ground Truth Policy (Section 5.1 합산)

**Algorithm Comparison**:

| Algorithm | Accuracy | Performance | Use Case |
|-----------|----------|-------------|----------|
| `fixed_window` | Medium | High | High throughput, less precision |
| `sliding_window` | **High** | Medium | **Production (Default)** |
| `token_bucket` | High | Medium | Burst-heavy workloads |

**Environment Overrides**:
```bash
RATE_LIMITER_URL=redis://limiter:6379/0
HUB_GLOBAL_RATE_LIMIT=100  # 더 높은 한도
HUB_RATE_LIMIT_ALGORITHM=token_bucket
```

**Metrics**:
- `rate_limiter_allowed_total{provider="KIS"}`
- `rate_limiter_rejected_total{provider="KIS"}`
- `rate_limiter_current_rate{provider="KIS"}`

---

## Monitoring Configuration

### Section: `api_hub.monitoring`

로깅, 메트릭, 헬스체크 설정을 정의합니다.

| Parameter | Type | Default | Description | Rationale |
|-----------|------|---------|-------------|-----------|
| `log_level` | string | `INFO` | 로그 레벨 | Production: INFO, Debug: DEBUG |
| `metrics_enabled` | bool | `true` | Prometheus 메트릭 활성화 | 성능 모니터링 필수 |
| `health_check_interval` | float | `10.0` | 헬스체크 주기 (초) | Docker healthcheck와 동기화 |
| `alert_on_circuit_open` | bool | `true` | Circuit Open 시 알림 발송 | 장애 즉시 통지 |

**Authority**:
- Log Level: 12-Factor App Principles
- Metrics: Prometheus Best Practices
- Health Check: `deploy/docker-compose.yml:436` (healthcheck 정의)

**Log Levels**:
```
DEBUG: 모든 Config 로딩, 요청/응답 상세
INFO: 태스크 처리, Circuit 상태 변화
WARNING: Retry, Rate Limit 초과
ERROR: API 호출 실패, Circuit Open
```

**Environment Overrides**:
```bash
LOG_LEVEL=DEBUG  # 상세 디버깅
HUB_METRICS_ENABLED=false  # 테스트 환경
```

---

## Testing Configuration

### Section: `api_hub.testing`

개발 및 테스트 환경 전용 설정을 정의합니다.

| Parameter | Type | Default | Description | Use Case |
|-----------|------|---------|-------------|----------|
| `mock_latency_ms` | int | `100` | Mock API 지연 시간 (ms) | 네트워크 지연 시뮬레이션 |
| `mock_failure_rate` | float | `0.0` | Mock API 실패 비율 (0.0-1.0) | Circuit Breaker 테스트 |
| `enable_test_endpoints` | bool | `false` | 테스트 전용 엔드포인트 활성화 | Integration Test 전용 |

**Authority**:
- ISSUE-037-E Phase 2 Test Plan
- Mock Testing Strategy: `tests/integration/test_api_hub_v2_integration.py`

**Example Usage**:
```yaml
# Production
testing:
  mock_latency_ms: 100
  mock_failure_rate: 0.0
  enable_test_endpoints: false

# Integration Test
testing:
  mock_latency_ms: 50  # 빠른 테스트
  mock_failure_rate: 0.3  # 30% 실패로 Circuit Breaker 테스트
  enable_test_endpoints: true
```

**Environment Overrides**:
```bash
HUB_MOCK_LATENCY_MS=200
HUB_MOCK_FAILURE_RATE=0.5  # 50% 실패 시뮬레이션
HUB_ENABLE_TEST_ENDPOINTS=true
```

---

## Environment Variable Overrides

모든 Config 값은 환경변수로 재정의 가능합니다.

### Override Priority

```
1. Environment Variables (highest)
2. YAML Config File
3. Default Values (lowest)
```

### Complete Override Table

| Config Path | Environment Variable | Type | Example |
|-------------|---------------------|------|---------|
| `worker.redis_url` | `REDIS_URL` | string | `redis://prod:6379/15` |
| `worker.enable_mock` | `ENABLE_MOCK` | bool | `false` |
| `worker.max_retries` | `HUB_MAX_RETRIES` | int | `5` |
| `worker.timeout` | `HUB_TIMEOUT` | float | `15.0` |
| `worker.batch_size` | `HUB_BATCH_SIZE` | int | `200` |
| `worker.shutdown_timeout` | `HUB_SHUTDOWN_TIMEOUT` | float | `10.0` |
| `queues.priority` | `HUB_PRIORITY_QUEUE` | string | `api:urgent:queue` |
| `queues.normal` | `HUB_NORMAL_QUEUE` | string | `api:batch:queue` |
| `queues.response_ttl` | `HUB_RESPONSE_TTL` | int | `7200` |
| `queues.max_queue_size` | `HUB_MAX_QUEUE_SIZE` | int | `20000` |
| `circuit_breaker.failure_threshold` | `HUB_CB_FAILURE_THRESHOLD` | int | `10` |
| `circuit_breaker.recovery_timeout` | `HUB_CB_RECOVERY_TIMEOUT` | float | `60.0` |
| `circuit_breaker.half_open_max_calls` | `HUB_CB_HALF_OPEN_MAX` | int | `5` |
| `circuit_breaker.success_threshold` | `HUB_CB_SUCCESS_THRESHOLD` | int | `3` |
| `providers.KIS.base_url` | `KIS_BASE_URL` | string | `https://api.kis.com` |
| `providers.KIWOOM.base_url` | `KIWOOM_API_URL` | string | `https://api.kiwoom.com` |
| `token_manager.redis_key_prefix` | `HUB_TOKEN_PREFIX` | string | `oauth:token:` |
| `token_manager.auto_refresh_margin` | `HUB_TOKEN_REFRESH_MARGIN` | int | `600` |
| `token_manager.max_refresh_retries` | `HUB_TOKEN_MAX_RETRIES` | int | `5` |
| `token_manager.refresh_backoff_factor` | `HUB_TOKEN_BACKOFF` | float | `3.0` |
| `token_manager.token_ttl_buffer` | `HUB_TOKEN_TTL_BUFFER` | int | `120` |
| `rate_limiter.redis_url` | `RATE_LIMITER_URL` | string | `redis://limiter:6379/0` |
| `rate_limiter.enabled` | `HUB_RATE_LIMITER_ENABLED` | bool | `false` |
| `rate_limiter.global_limit` | `HUB_GLOBAL_RATE_LIMIT` | int | `100` |
| `rate_limiter.per_provider_limit` | `HUB_PER_PROVIDER_LIMIT` | bool | `false` |
| `rate_limiter.algorithm` | `HUB_RATE_LIMIT_ALGORITHM` | string | `token_bucket` |
| `rate_limiter.rejection_ttl` | `HUB_REJECTION_TTL` | int | `120` |
| `monitoring.log_level` | `LOG_LEVEL` | string | `DEBUG` |
| `monitoring.metrics_enabled` | `HUB_METRICS_ENABLED` | bool | `false` |
| `monitoring.health_check_interval` | `HUB_HEALTH_CHECK_INTERVAL` | float | `5.0` |
| `monitoring.alert_on_circuit_open` | `HUB_ALERT_ON_CB_OPEN` | bool | `false` |
| `testing.mock_latency_ms` | `HUB_MOCK_LATENCY_MS` | int | `200` |
| `testing.mock_failure_rate` | `HUB_MOCK_FAILURE_RATE` | float | `0.5` |
| `testing.enable_test_endpoints` | `HUB_ENABLE_TEST_ENDPOINTS` | bool | `true` |

**Full Schema**: See `.env.schema.yaml` for complete list

---

## Configuration Best Practices

### 1. Separation of Concerns

**DO**:
- YAML: 정적 설정 (timeout, rate limit, circuit breaker 임계값)
- Env Vars: 민감 정보 (API keys, secrets) 및 배포별 설정 (Redis URL)

**DON'T**:
- YAML에 하드코딩된 API Key (보안 위험)
- Env Var로 모든 설정 관리 (가독성 저하)

### 2. Mock Mode First

**개발/테스트 플로우**:
```bash
# 1. Mock 모드로 기능 검증
ENABLE_MOCK=true pytest tests/integration/

# 2. 설정 검증
ENABLE_MOCK=true python -m src.api_gateway.hub --dry-run

# 3. 실제 API 모드로 전환
ENABLE_MOCK=false KIS_APP_KEY=... python -m src.api_gateway.hub
```

### 3. Rate Limiting Alignment

**Ground Truth와 동기화**:
```yaml
# configs/api_hub_v2.yaml
providers:
  KIS:
    rate_limit:
      requests_per_second: 20  # ← Ground Truth Policy 참조
```

**변경 시 동기화 필요**:
1. Broker API 공식 문서 확인
2. `docs/governance/ground_truth_policy.md` 업데이트
3. `configs/api_hub_v2.yaml` 업데이트
4. `/council-review` 워크플로우 호출

### 4. Circuit Breaker Tuning

**Production Monitoring 기반 조정**:
```bash
# Baseline (Default)
HUB_CB_FAILURE_THRESHOLD=5
HUB_CB_RECOVERY_TIMEOUT=30.0

# High Availability (더 관대하게)
HUB_CB_FAILURE_THRESHOLD=10
HUB_CB_RECOVERY_TIMEOUT=60.0

# Strict (장애 민감)
HUB_CB_FAILURE_THRESHOLD=3
HUB_CB_RECOVERY_TIMEOUT=15.0
```

**Metrics 기반 의사결정**:
- `circuit_breaker_open_total` > 10/hour → `failure_threshold` 증가 고려
- `api_request_duration_seconds` p99 > 5s → `timeout` 증가 고려

### 5. Resource Limits

**Docker 리소스와 Config 정렬**:
```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 1G

# configs/api_hub_v2.yaml
worker:
  batch_size: 100  # ← 1GB 메모리 기준으로 조정
  timeout: 10.0  # ← CPU 1 코어 기준으로 조정
```

**Rule of Thumb**:
- `batch_size` = Memory (GB) × 100
- `timeout` = CPU (cores) × 10 seconds

---

## Validation

### Test Configuration

```bash
# 1. Config 파일 로딩 테스트
PYTHONPATH=. poetry run pytest tests/unit/test_api_hub_config.py -v

# 2. 실제 환경 테스트
python3 -c "
from src.api_gateway.hub.config import hub_config
print(f'Redis: {hub_config.get_redis_url()}')
print(f'Mock: {hub_config.is_mock_enabled()}')
print(f'KIS Rate Limit: {hub_config.get_provider_config(\"KIS\")[\"rate_limit\"][\"requests_per_second\"]}/s')
"

# 3. Integration 테스트
PYTHONPATH=. poetry run pytest tests/integration/test_api_hub_v2_integration.py -v -m manual
```

### Schema Validation

Pydantic 모델이 자동으로 검증:
```python
# src/api_gateway/hub/config.py
class ApiHubConfig(BaseModel):
    worker: WorkerConfig  # ← 자동 타입 체크
    queues: QueueConfig
    circuit_breaker: CircuitBreakerConfig
    providers: Dict[str, ProviderConfig]
    ...
```

**Invalid Config 예시**:
```yaml
# ❌ 잘못된 설정
worker:
  timeout: "not_a_number"  # Validation Error

circuit_breaker:
  failure_threshold: -5  # Negative value not allowed
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `Config file not found` | `HUB_CONFIG_PATH` 잘못 지정 | 기본값 사용 or 올바른 경로 지정 |
| `Pydantic ValidationError` | Config 값 타입 불일치 | YAML 파일 수정 or Env Var 타입 확인 |
| `Redis connection refused` | `worker.redis_url` 불일치 | Docker network 확인 or Redis 실행 상태 확인 |
| `Rate limit too aggressive` | `providers.*.rate_limit` 너무 낮음 | Ground Truth Policy 참조하여 상향 조정 |
| `Circuit always open` | `failure_threshold` 너무 낮음 | 임계값 증가 or 타임아웃 증가 |

### Debug Commands

```bash
# Config 로딩 디버깅
LOG_LEVEL=DEBUG python -c "from src.api_gateway.hub.config import hub_config"

# 환경변수 우선순위 확인
env | grep HUB_

# Docker 내부 Config 확인
docker exec gateway-worker-real cat /app/configs/api_hub_v2.yaml
```

---

## Related Documents

- **Implementation**: `src/api_gateway/hub/config.py` (HubConfig class, 331 lines)
- **Tests**: `tests/unit/test_api_hub_config.py` (23 tests, 100% passing)
- **Overview**: `docs/specs/api_hub_v2_overview.md#configuration` (Usage guide)
- **Ground Truth**: `docs/governance/ground_truth_policy.md#5-api-hub-v2-configuration`
- **Environment Schema**: `.env.schema.yaml` (Complete variable list)
- **Docker**: `deploy/docker-compose.yml` (gateway-worker-mock, gateway-worker-real)
- **Phase 2 Prerequisites**: 
  - `docs/specs/api_hub_base_client_spec.md` (BaseAPIClient design)
  - `docs/specs/token_manager_spec.md` (Token Manager design)
  - `docs/specs/rate_limiter_integration_plan.md` (Rate Limiter integration)

---

## Changelog

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-01-23 | Initial specification | Council of Six |

---

> [!NOTE]
> 본 문서는 API Hub v2 Config의 **단일 참조 문서(SSoT)**입니다.  
> 설정 변경 시 반드시 본 문서를 먼저 업데이트하고, Council Review를 거쳐야 합니다.
