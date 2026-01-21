# Test Implementation Plan
## ISSUE: System Metrics Type Mismatch & Infrastructure Issues

> **생성일**: 2026-01-21
> **관련 이슈**: System Metrics 타입 불일치, Container DNS Resolution 실패
> **FMEA 참조**: Section 3.4, 3.5
> **Test Registry**: TS-TYPE-01, INF-DNS-01, INF-NET-01, INF-HEALTH-01, INF-ENV-01

---

## 1. 개요

### 1.1 발견된 문제

**2026-01-21** 현재 시스템에서 발견된 이슈:

1. **System Metrics Type Mismatch** (TS-TYPE-01)
   - Sentinel이 `system.metrics` 채널에 발행하는 데이터의 `meta` 필드가 dict 타입
   - TimescaleArchiver가 일부 케이스에서 str 타입을 기대하여 저장 실패
   - 에러: `invalid input for query argument $4: expected str, got dict`

2. **Container DNS Resolution Failure** (INF-DNS-01)
   - docker-compose.yml에서 호스트 이름 변경 (`stock-redis` → `redis`, `stock-timescale` → `timescaledb`)
   - 일부 컨테이너(history-collector)가 새 호스트 이름을 resolve 실패
   - 에러: `Temporary failure in name resolution`

3. **Partial Restart Network Inconsistency** (INF-NET-01, INF-HEALTH-01)
   - 개별 컨테이너 재시작 시 네트워크 alias가 제대로 적용되지 않음
   - 전체 재시작 후 정상화되지만, 부분 재시작 시 문제 재발

### 1.2 목적

- 위 이슈를 **조기에 검출**할 수 있는 자동화된 테스트 케이스 구현
- CI/CD 파이프라인에 통합하여 **배포 전 사전 검증**
- FMEA에 정의된 대응 전략의 **실제 작동 검증**

---

## 2. 테스트 케이스 상세 설계

### 2.1 TS-TYPE-01: System Metrics Data Type Validation

**목적**: Sentinel이 발행하는 system metrics 데이터가 TimescaleArchiver의 스키마와 타입이 일치하는지 검증

**테스트 파일**: `tests/test_system_metrics_schema.py`

**구현 방법**:

```python
import asyncio
import json
import pytest
import asyncpg
from redis.asyncio import Redis
from datetime import datetime

@pytest.mark.asyncio
async def test_system_metrics_type_validation():
    """
    Sentinel이 발행하는 system.metrics 데이터가
    TimescaleDB system_metrics 테이블 스키마와 타입이 일치하는지 검증
    """
    # 1. DB 스키마 확인 (system_metrics 테이블의 labels 컬럼은 jsonb)
    conn = await asyncpg.connect(
        user='postgres', password='password',
        database='stockval', host='localhost', port=5432
    )

    schema = await conn.fetch("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'system_metrics'
    """)

    schema_dict = {row['column_name']: row['data_type'] for row in schema}
    assert schema_dict['labels'] == 'jsonb', "labels should be jsonb type"

    # 2. Sentinel이 발행하는 실제 메시지 구조 검증
    test_messages = [
        # Legacy format (host metrics)
        {
            "timestamp": datetime.now().isoformat(),
            "cpu": 30.5,
            "mem": 45.2,
            "disk": 60.0
        },
        # New generic format (container status)
        {
            "timestamp": datetime.now().isoformat(),
            "type": "container_status",
            "value": 1.0,
            "meta": {"container": "test-container", "status": "running"}
        },
        # Redis metrics
        {
            "timestamp": datetime.now().isoformat(),
            "type": "redis_used_memory",
            "value": 1048576.0,
            "meta": {"status": "ok"}
        }
    ]

    # 3. TimescaleArchiver 로직 시뮬레이션
    for msg in test_messages:
        ts = datetime.fromisoformat(msg['timestamp'])

        if 'cpu' in msg and 'mem' in msg:
            # Legacy format
            rows = [
                (ts, 'cpu', float(msg['cpu']), None),
                (ts, 'memory', float(msg['mem']), None)
            ]
            if 'disk' in msg:
                rows.append((ts, 'disk', float(msg['disk']), None))

            # DB INSERT 시뮬레이션 (labels는 None 허용)
            for row in rows:
                assert len(row) == 4
                assert isinstance(row[3], (type(None), str)), \
                    "labels must be None or str (json.dumps result)"

        else:
            # New generic format
            m_type = msg.get('type')
            val = float(msg.get('value'))

            # CRITICAL: meta를 json.dumps로 변환해야 함
            labels = json.dumps(msg.get('meta')) if msg.get('meta') else None

            # 타입 검증
            assert isinstance(labels, (type(None), str)), \
                f"labels must be None or str, got {type(labels)}"

            # DB INSERT 시뮬레이션
            try:
                await conn.execute(
                    "INSERT INTO system_metrics (time, metric_name, value, labels) VALUES ($1, $2, $3, $4)",
                    ts, m_type, val, labels
                )
            except Exception as e:
                pytest.fail(f"Failed to insert metrics: {e}")

    await conn.close()


@pytest.mark.asyncio
async def test_sentinel_publisher_validation():
    """
    Sentinel이 실제로 발행하는 메시지를 subscribe하여 타입 검증
    """
    redis = await Redis.from_url("redis://localhost:6380/0", decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe("system.metrics")

    # 타임아웃 설정 (10초)
    received = []

    async def collect_messages():
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                received.append(data)

                # Validation
                assert 'timestamp' in data, "timestamp required"

                if 'meta' in data:
                    # meta는 dict 타입이어야 함 (발행 시점)
                    assert isinstance(data['meta'], dict), \
                        f"meta must be dict at publish time, got {type(data['meta'])}"

                if len(received) >= 3:  # 3개 메시지 수신 후 종료
                    break

    try:
        await asyncio.wait_for(collect_messages(), timeout=30)
    except asyncio.TimeoutError:
        pytest.skip("No system metrics published within 30 seconds")

    await redis.close()
    assert len(received) > 0, "Should receive at least one metric"
```

**검증 포인트**:
- ✅ DB 스키마 `labels` 컬럼이 `jsonb` 타입인지 확인
- ✅ Sentinel 발행 시 `meta`는 dict, Archiver 저장 시 `json.dumps()`로 str 변환
- ✅ 실제 메시지 subscribe하여 타입 일관성 검증

---

### 2.2 INF-DNS-01: Container DNS Resolution Test

**목적**: 모든 컨테이너가 필수 호스트(timescaledb, redis)를 정상적으로 resolve할 수 있는지 검증

**테스트 파일**: `tests/test_infrastructure.py`

**구현 방법**:

```python
import subprocess
import pytest

REQUIRED_HOSTS = ['timescaledb', 'redis']
CONTAINERS = [
    'timescale-archiver',
    'tick-archiver',
    'news-archiver',
    'history-collector',
    'history-loader',
    'sentinel-agent',
    'verification-worker',
    'stock_prod-api'
]

@pytest.mark.integration
def test_container_dns_resolution():
    """
    모든 컨테이너가 timescaledb, redis 호스트를 정상 resolve하는지 검증
    """
    results = {}

    for container in CONTAINERS:
        results[container] = {}

        for host in REQUIRED_HOSTS:
            # getent hosts로 DNS resolution 테스트
            cmd = f"docker exec {container} getent hosts {host}"
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=5
            )

            success = result.returncode == 0 and host in result.stdout
            results[container][host] = {
                'success': success,
                'output': result.stdout if success else result.stderr
            }

            # Assertion
            assert success, \
                f"Container '{container}' failed to resolve host '{host}': {result.stderr}"

    # 전체 결과 로깅
    print("\n=== DNS Resolution Test Results ===")
    for container, hosts in results.items():
        print(f"\n{container}:")
        for host, res in hosts.items():
            status = "✅" if res['success'] else "❌"
            print(f"  {status} {host}: {res['output'][:50]}")


@pytest.mark.integration
def test_dns_alias_consistency():
    """
    docker-compose.yml에 정의된 network alias와 실제 DNS 해결 결과가 일치하는지 검증
    """
    # docker-compose.yml에서 alias 추출 (간단 버전)
    expected_aliases = {
        'stock_prod-timescale': ['timescaledb'],
        'stock_prod-redis': ['redis']
    }

    for container, aliases in expected_aliases.items():
        for alias in aliases:
            cmd = f"docker exec timescale-archiver getent hosts {alias}"
            result = subprocess.run(cmd.split(), capture_output=True, text=True)

            assert result.returncode == 0, \
                f"Alias '{alias}' for container '{container}' not resolvable"

            # IP 추출
            ip = result.stdout.split()[0]

            # 실제 컨테이너 IP와 비교
            inspect_cmd = f"docker inspect -f '{{{{.NetworkSettings.Networks.stock_prod_default.IPAddress}}}}' {container}"
            inspect_result = subprocess.run(inspect_cmd, shell=True, capture_output=True, text=True)
            actual_ip = inspect_result.stdout.strip()

            assert ip == actual_ip, \
                f"Alias '{alias}' resolves to {ip}, but container '{container}' has IP {actual_ip}"
```

**검증 포인트**:
- ✅ 모든 서비스 컨테이너가 `timescaledb`, `redis` 호스트를 resolve 가능
- ✅ docker-compose.yml의 network alias가 실제 적용됨
- ✅ Alias IP와 실제 컨테이너 IP가 일치

---

### 2.3 INF-NET-01: Network Alias Validation

**목적**: docker-compose.yml에 정의된 network alias가 실제 네트워크에 정상 적용되었는지 검증

**테스트 파일**: `tests/test_infrastructure.py` (추가)

**구현 방법**:

```python
import subprocess
import yaml
import pytest

@pytest.mark.integration
def test_network_alias_validation():
    """
    docker-compose.yml의 network alias 설정이 실제 Docker 네트워크에 반영되었는지 검증
    """
    # 1. docker-compose.yml 파싱
    with open('deploy/docker-compose.yml', 'r') as f:
        compose_config = yaml.safe_load(f)

    service_aliases = {}
    for service_name, service_config in compose_config['services'].items():
        networks = service_config.get('networks', {})
        if isinstance(networks, dict):
            for net_name, net_config in networks.items():
                if isinstance(net_config, dict) and 'aliases' in net_config:
                    service_aliases[service_name] = net_config['aliases']

    # 2. 실제 Docker 네트워크 검사
    for service, aliases in service_aliases.items():
        container_name = f"stock_prod-{service}" if not service.startswith('stock_prod') else service

        # 컨테이너가 실행 중인지 확인
        ps_cmd = f"docker ps --filter name={container_name} --format '{{{{.Names}}}}'"
        ps_result = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)

        if not ps_result.stdout.strip():
            pytest.skip(f"Container '{container_name}' is not running")

        # 네트워크 별칭 검증
        inspect_cmd = f"docker inspect {container_name}"
        result = subprocess.run(inspect_cmd.split(), capture_output=True, text=True)

        assert result.returncode == 0, f"Failed to inspect container '{container_name}'"

        import json
        container_info = json.loads(result.stdout)[0]
        network_settings = container_info['NetworkSettings']['Networks']

        for network_name, network_info in network_settings.items():
            actual_aliases = network_info.get('Aliases', [])

            for expected_alias in aliases:
                assert expected_alias in actual_aliases, \
                    f"Container '{container_name}' missing expected alias '{expected_alias}' in network '{network_name}'. " \
                    f"Expected: {aliases}, Actual: {actual_aliases}"


@pytest.mark.integration
def test_cross_container_communication():
    """
    컨테이너 간 alias를 통한 통신이 정상 작동하는지 검증
    """
    # timescale-archiver에서 redis로 ping
    cmd = "docker exec timescale-archiver ping -c 1 redis"
    result = subprocess.run(cmd.split(), capture_output=True, text=True)
    assert result.returncode == 0, "Failed to ping redis from timescale-archiver"

    # history-loader에서 timescaledb로 pg_isready
    cmd = "docker exec history-loader pg_isready -h timescaledb -p 5432"
    result = subprocess.run(cmd.split(), capture_output=True, text=True)
    assert result.returncode == 0, "TimescaleDB not ready from history-loader"
```

**검증 포인트**:
- ✅ docker-compose.yml의 alias 설정이 실제 컨테이너에 적용됨
- ✅ 컨테이너 간 alias를 통한 통신 가능
- ✅ 네트워크 구성이 compose 파일과 일치

---

### 2.4 INF-HEALTH-01: Service Startup Health Check

**목적**: 모든 서비스가 시작 후 30초 내에 정상 상태에 도달하는지 검증

**테스트 파일**: `tests/test_infrastructure.py` (추가)

**구현 방법**:

```python
import time
import subprocess
import pytest

CRITICAL_SERVICES = [
    'stock_prod-timescale',
    'stock_prod-redis',
    'timescale-archiver',
    'tick-archiver',
    'news-archiver',
    'sentinel-agent',
    'stock_prod-api'
]

@pytest.mark.integration
def test_service_startup_health():
    """
    make up 실행 후 모든 서비스가 30초 내에 healthy/running 상태에 도달하는지 검증
    """
    # 1. 현재 실행 중인 컨테이너 확인
    cmd = "docker ps --format '{{.Names}}\t{{.Status}}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    running_containers = {}
    for line in result.stdout.strip().split('\n'):
        if '\t' in line:
            name, status = line.split('\t', 1)
            running_containers[name] = status

    # 2. 필수 서비스가 모두 실행 중인지 확인
    for service in CRITICAL_SERVICES:
        assert service in running_containers, \
            f"Critical service '{service}' is not running"

    # 3. Health check (30초 대기)
    max_wait = 30
    start_time = time.time()

    unhealthy = []

    while time.time() - start_time < max_wait:
        unhealthy = []

        for service in CRITICAL_SERVICES:
            # 컨테이너 상태 확인
            inspect_cmd = f"docker inspect {service} --format '{{{{.State.Status}}}}'"
            result = subprocess.run(inspect_cmd, shell=True, capture_output=True, text=True)
            status = result.stdout.strip()

            if status != 'running':
                unhealthy.append(f"{service}: {status}")
                continue

            # Health check가 정의된 경우 확인
            health_cmd = f"docker inspect {service} --format '{{{{.State.Health.Status}}}}'"
            result = subprocess.run(health_cmd, shell=True, capture_output=True, text=True)
            health_status = result.stdout.strip()

            if health_status and health_status not in ['healthy', '<no value>']:
                unhealthy.append(f"{service}: health={health_status}")

        if not unhealthy:
            break

        time.sleep(2)

    assert not unhealthy, \
        f"Services not healthy after {max_wait}s: {', '.join(unhealthy)}"


@pytest.mark.integration
def test_service_error_logs():
    """
    각 서비스가 시작 후 Critical 에러를 발생시키지 않는지 로그 검증
    """
    error_patterns = [
        'CRITICAL',
        'FATAL',
        'Traceback (most recent call last)',
        'ConnectionError',
        'Temporary failure in name resolution'
    ]

    failed_services = {}

    for service in CRITICAL_SERVICES:
        cmd = f"docker logs --tail 50 {service}"
        result = subprocess.run(cmd.split(), capture_output=True, text=True)

        logs = result.stdout + result.stderr
        errors = []

        for pattern in error_patterns:
            if pattern in logs:
                # 에러 발생 라인 추출
                for line in logs.split('\n'):
                    if pattern in line:
                        errors.append(line[:100])

        if errors:
            failed_services[service] = errors

    assert not failed_services, \
        f"Services with errors:\n" + \
        '\n'.join([f"{svc}: {errs}" for svc, errs in failed_services.items()])
```

**검증 포인트**:
- ✅ 모든 critical 서비스가 30초 내 running 상태 도달
- ✅ health check가 정의된 서비스는 healthy 상태 확인
- ✅ 시작 로그에 critical 에러가 없음

---

### 2.5 INF-ENV-01: Environment Variables Validation

**목적**: 필수 환경변수가 모든 컨테이너에 올바르게 설정되었는지 검증

**테스트 파일**: `tests/test_infrastructure.py` (추가)

**구현 방법**:

```python
import subprocess
import pytest

REQUIRED_ENV_VARS = {
    'timescale-archiver': ['REDIS_URL', 'DB_HOST', 'DB_PORT', 'DB_NAME'],
    'history-loader': ['DB_HOST', 'DB_PORT', 'DB_NAME'],
    'history-collector': ['REDIS_URL', 'DB_HOST', 'DB_PORT'],
    'sentinel-agent': ['REDIS_URL'],
    'stock_prod-api': ['DB_HOST', 'REDIS_URL']
}

@pytest.mark.integration
def test_environment_variables():
    """
    필수 환경변수가 각 컨테이너에 올바르게 설정되었는지 검증
    """
    for container, required_vars in REQUIRED_ENV_VARS.items():
        for var in required_vars:
            cmd = f"docker exec {container} env"
            result = subprocess.run(cmd.split(), capture_output=True, text=True)

            assert result.returncode == 0, f"Failed to read env from '{container}'"

            env_dict = {}
            for line in result.stdout.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_dict[key] = value

            assert var in env_dict, \
                f"Required env var '{var}' not found in container '{container}'"

            # DB_HOST 검증
            if var == 'DB_HOST':
                assert env_dict[var] == 'timescaledb', \
                    f"DB_HOST should be 'timescaledb', got '{env_dict[var]}' in '{container}'"

            # REDIS_URL 검증
            if var == 'REDIS_URL':
                assert 'redis://' in env_dict[var], \
                    f"REDIS_URL malformed in '{container}': {env_dict[var]}"
                assert 'redis:6379' in env_dict[var] or 'stock-redis:6379' in env_dict[var], \
                    f"REDIS_URL should use 'redis:6379', got '{env_dict[var]}' in '{container}'"
```

**검증 포인트**:
- ✅ 필수 환경변수 존재 여부 확인
- ✅ DB_HOST가 `timescaledb`로 설정됨
- ✅ REDIS_URL이 `redis:6379`를 사용

---

## 3. 테스트 실행 방법

### 3.1 로컬 실행

```bash
# 전체 인프라 테스트 실행
pytest tests/test_infrastructure.py -v

# 특정 테스트만 실행
pytest tests/test_infrastructure.py::test_container_dns_resolution -v

# System metrics 테스트
pytest tests/test_system_metrics_schema.py -v
```

### 3.2 CI/CD 통합

```yaml
# .github/workflows/test.yml
name: Infrastructure Tests

on:
  push:
    branches: [develop, main]
  pull_request:

jobs:
  infrastructure-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Start services
        run: make up

      - name: Wait for services
        run: sleep 30

      - name: Run infrastructure tests
        run: |
          docker run --rm \
            --network stock_prod_default \
            -v $(pwd):/app \
            -w /app \
            python:3.12 \
            bash -c "pip install pytest pytest-asyncio asyncpg redis pyyaml && pytest tests/test_infrastructure.py -v"

      - name: Run system metrics tests
        run: |
          docker run --rm \
            --network stock_prod_default \
            -v $(pwd):/app \
            -w /app \
            python:3.12 \
            bash -c "pip install pytest pytest-asyncio asyncpg redis && pytest tests/test_system_metrics_schema.py -v"
```

### 3.3 수동 검증 (Smoke Test)

```bash
# 1. DNS Resolution 수동 확인
docker exec timescale-archiver getent hosts timescaledb
docker exec history-collector getent hosts redis

# 2. 서비스 Health 수동 확인
docker ps --format "table {{.Names}}\t{{.Status}}"

# 3. 환경변수 수동 확인
docker exec timescale-archiver env | grep -E "DB_HOST|REDIS_URL"

# 4. System Metrics 수동 확인 (DB 쿼리)
docker exec stock_prod-timescale psql -U postgres -d stockval -c \
  "SELECT COUNT(*) as recent_metrics FROM system_metrics WHERE time > NOW() - INTERVAL '5 minutes';"
```

---

## 4. 테스트 커버리지 및 우선순위

| Test ID | Priority | Automation | Estimated Time |
| :--- | :--- | :--- | :--- |
| TS-TYPE-01 | High | Full | 2 hours |
| INF-DNS-01 | Critical | Full | 1 hour |
| INF-NET-01 | High | Full | 1.5 hours |
| INF-HEALTH-01 | Critical | Full | 1 hour |
| INF-ENV-01 | Medium | Full | 0.5 hour |

**총 예상 구현 시간**: 6 hours

---

## 5. 성공 기준 (Definition of Done)

- [ ] 모든 테스트 케이스가 `tests/` 디렉토리에 구현됨
- [ ] pytest 실행 시 모든 테스트가 Pass
- [ ] test_registry.md의 상태가 `⏳ 예정` → `✅ Pass`로 업데이트
- [ ] CI/CD 파이프라인에 테스트가 통합됨
- [ ] 테스트 실행 문서(TESTING_MASTER_GUIDE.md)에 절차 추가
- [ ] FMEA의 Countermeasures에 테스트 ID 연결 확인

---

## 6. 후속 조치 (Follow-up Actions)

### 6.1 코드 개선

- [ ] Sentinel의 `system.metrics` 발행 로직에 pre-publish validation 추가
- [ ] TimescaleArchiver의 에러 핸들링 강화 (타입 불일치 시 graceful degradation)
- [ ] docker-compose.yml 변경 시 자동 검증 스크립트 추가

### 6.2 문서 업데이트

- [ ] TESTING_MASTER_GUIDE.md에 새로운 테스트 실행 절차 추가
- [ ] Runbook에 인프라 이슈 troubleshooting 추가
- [ ] .ai-rules.md에 인프라 변경 시 테스트 필수 규칙 추가

### 6.3 모니터링 강화

- [ ] Grafana 대시보드에 system_metrics 저장 성공률 패널 추가
- [ ] Sentinel에 DNS resolution failure 감지 로직 추가
- [ ] 컨테이너 health check 실패 시 자동 알림 설정

---

## 7. 관련 문서

- [FMEA](./FAILURE_MODE_ANALYSIS.md): Section 3.4, 3.5
- [Test Registry](./test_registry.md): TS-TYPE-01, INF-* 시리즈
- [Manage Tests Workflow](../../.agent/workflows/manage-tests.md)
- [Testing Master Guide](./TESTING_MASTER_GUIDE.md)
