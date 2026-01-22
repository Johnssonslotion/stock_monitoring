"""
Test Suite: Infrastructure & Environment Validation

테스트 ID:
- INF-DNS-01: Container DNS Resolution
- INF-NET-01: Network Alias Validation
- INF-HEALTH-01: Service Startup Health Check
- INF-ENV-01: Environment Variables Validation

관련 문서:
- FMEA: Section 3.5
- Test Registry: INF-DNS-01, INF-NET-01, INF-HEALTH-01, INF-ENV-01
- Implementation Plan: TEST_IMPLEMENTATION_PLAN.md
"""

import subprocess
import time
import json
import pytest
import os

# 필수 호스트 (docker-compose.yml의 network alias)
REQUIRED_HOSTS = ['timescaledb', 'redis']

# 테스트 대상 컨테이너
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

# Critical 서비스 (반드시 실행 중이어야 함)
CRITICAL_SERVICES = [
    'stock_prod-timescale',
    'stock_prod-redis',
    'timescale-archiver',
    'tick-archiver',
    'news-archiver',
    'sentinel-agent',
    'stock_prod-api'
]

# 컨테이너별 필수 환경변수
REQUIRED_ENV_VARS = {
    'timescale-archiver': ['REDIS_URL', 'DB_HOST', 'DB_PORT', 'DB_NAME'],
    'history-loader': ['DB_HOST', 'DB_PORT', 'DB_NAME'],
    'history-collector': ['REDIS_URL', 'DB_HOST', 'DB_PORT'],
    'sentinel-agent': ['REDIS_URL'],
    'stock_prod-api': ['DB_HOST', 'REDIS_URL']
}


def run_command(cmd, timeout=5, shell=False):
    """
    Helper function to run shell command
    """
    try:
        if isinstance(cmd, str) and not shell:
            cmd = cmd.split()

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=shell
        )
        return result
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        print(f"Command failed: {e}")
        return None


def is_container_running(container_name):
    """
    Check if container is running
    """
    result = run_command(f"docker ps --filter name={container_name} --format '{{{{.Names}}}}'", shell=True)
    return result and container_name in result.stdout


# ==================== INF-DNS-01: Container DNS Resolution ====================

@pytest.mark.integration
def test_container_dns_resolution():
    """
    INF-DNS-01: 모든 컨테이너가 timescaledb, redis 호스트를 정상 resolve하는지 검증

    검증 포인트:
    - 모든 서비스 컨테이너가 필수 호스트를 resolve 가능
    - DNS resolution이 올바른 IP로 매핑됨
    """
    results = {}
    failed = []

    print("\n" + "="*70)
    print("INF-DNS-01: Container DNS Resolution Test")
    print("="*70)

    for container in CONTAINERS:
        # 컨테이너 실행 확인
        if not is_container_running(container):
            print(f"⏭️  Skipping {container} (not running)")
            continue

        results[container] = {}

        for host in REQUIRED_HOSTS:
            # getent hosts로 DNS resolution 테스트
            cmd = f"docker exec {container} getent hosts {host}"
            result = run_command(cmd)

            if result is None:
                success = False
                output = "Timeout"
            else:
                success = result.returncode == 0 and host in result.stdout
                output = result.stdout.strip() if success else result.stderr.strip()

            results[container][host] = {
                'success': success,
                'output': output[:100] if output else "No output"
            }

            status = "✅" if success else "❌"
            print(f"{status} {container:30} -> {host:15} : {output[:50]}")

            if not success:
                failed.append(f"{container} -> {host}: {output}")

    # 결과 요약
    print("\n" + "-"*70)
    if failed:
        print(f"❌ DNS Resolution Failed ({len(failed)} failures):")
        for fail in failed:
            print(f"   - {fail}")
        pytest.fail(f"DNS resolution failed for {len(failed)} container-host pairs")
    else:
        print(f"✅ All containers can resolve required hosts")


@pytest.mark.integration
def test_dns_alias_consistency():
    """
    INF-DNS-01 (Extended): docker-compose.yml에 정의된 network alias와
    실제 DNS 해결 결과가 일치하는지 검증
    """
    expected_aliases = {
        'stock_prod-timescale': ['timescaledb'],
        'stock_prod-redis': ['redis']
    }

    print("\n" + "="*70)
    print("INF-DNS-01 Extended: DNS Alias Consistency Test")
    print("="*70)

    failed = []

    for container, aliases in expected_aliases.items():
        if not is_container_running(container):
            print(f"⏭️  Skipping {container} (not running)")
            continue

        for alias in aliases:
            # timescale-archiver에서 alias 해결 테스트
            cmd = f"docker exec timescale-archiver getent hosts {alias}"
            result = run_command(cmd)

            if result is None or result.returncode != 0:
                failed.append(f"Alias '{alias}' for '{container}' not resolvable")
                print(f"❌ Alias '{alias}' -> Not resolvable")
                continue

            # Resolved IP 추출
            resolved_ip = result.stdout.split()[0]

            # 실제 컨테이너 IP 조회
            inspect_cmd = f"docker inspect -f '{{{{.NetworkSettings.Networks.stock_prod_default.IPAddress}}}}' {container}"
            inspect_result = run_command(inspect_cmd, shell=True)

            if inspect_result is None:
                failed.append(f"Failed to inspect container '{container}'")
                continue

            actual_ip = inspect_result.stdout.strip()

            if resolved_ip == actual_ip:
                print(f"✅ Alias '{alias}' -> {resolved_ip} (matches container '{container}')")
            else:
                failed.append(f"Alias '{alias}' resolves to {resolved_ip}, but container '{container}' has IP {actual_ip}")
                print(f"❌ Alias '{alias}' -> {resolved_ip} (expected {actual_ip})")

    print("-"*70)
    if failed:
        pytest.fail(f"DNS alias inconsistency detected:\n" + "\n".join(f"  - {f}" for f in failed))
    else:
        print("✅ All network aliases are consistent")


# ==================== INF-NET-01: Network Alias Validation ====================

@pytest.mark.integration
def test_network_alias_validation():
    """
    INF-NET-01: docker-compose.yml의 network alias 설정이
    실제 Docker 네트워크에 반영되었는지 검증

    검증 포인트:
    - docker-compose.yml에 정의된 alias가 컨테이너에 적용됨
    - 네트워크 구성이 compose 파일과 일치
    """
    print("\n" + "="*70)
    print("INF-NET-01: Network Alias Validation Test")
    print("="*70)

    # docker-compose.yml에 정의된 alias (하드코딩)
    # 실제로는 yaml 파싱이 필요하지만, 현재 구조에서는 하드코딩
    expected_service_aliases = {
        'timescaledb': ['timescaledb'],  # service name: timescaledb
        'redis': ['redis']  # service name: redis
    }

    failed = []

    # 컨테이너별로 network alias 확인
    for service_name, expected_aliases in expected_service_aliases.items():
        # 컨테이너 이름 매핑
        if service_name == 'timescaledb':
            container_name = 'stock_prod-timescale'
        elif service_name == 'redis':
            container_name = 'stock_prod-redis'
        else:
            container_name = service_name

        if not is_container_running(container_name):
            print(f"⏭️  Skipping {container_name} (not running)")
            continue

        # 컨테이너 inspect로 실제 alias 조회
        inspect_cmd = f"docker inspect {container_name}"
        result = run_command(inspect_cmd)

        if result is None or result.returncode != 0:
            failed.append(f"Failed to inspect container '{container_name}'")
            print(f"❌ Failed to inspect '{container_name}'")
            continue

        try:
            container_info = json.loads(result.stdout)[0]
            network_settings = container_info['NetworkSettings']['Networks']

            # stock_prod_default 네트워크의 alias 확인
            if 'stock_prod_default' in network_settings:
                actual_aliases = network_settings['stock_prod_default'].get('Aliases', [])

                print(f"\n{container_name}:")
                print(f"  Expected: {expected_aliases}")
                print(f"  Actual:   {actual_aliases}")

                # 기대하는 alias가 모두 포함되어 있는지 확인
                for expected_alias in expected_aliases:
                    if expected_alias in actual_aliases:
                        print(f"  ✅ Alias '{expected_alias}' found")
                    else:
                        failed.append(f"Container '{container_name}' missing alias '{expected_alias}'")
                        print(f"  ❌ Alias '{expected_alias}' NOT found")
            else:
                failed.append(f"Container '{container_name}' not connected to stock_prod_default network")
                print(f"❌ {container_name} not in stock_prod_default network")

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            failed.append(f"Failed to parse container info for '{container_name}': {e}")
            print(f"❌ Parse error for '{container_name}': {e}")

    print("-"*70)
    if failed:
        pytest.fail(f"Network alias validation failed:\n" + "\n".join(f"  - {f}" for f in failed))
    else:
        print("✅ All network aliases are correctly configured")


@pytest.mark.integration
def test_cross_container_communication():
    """
    INF-NET-01 (Extended): 컨테이너 간 alias를 통한 통신이 정상 작동하는지 검증
    """
    print("\n" + "="*70)
    print("INF-NET-01 Extended: Cross-Container Communication Test")
    print("="*70)

    tests = [
        {
            'from': 'timescale-archiver',
            'to': 'redis',
            'cmd': 'ping -c 1 -W 2 redis',
            'description': 'Ping redis from timescale-archiver'
        },
        {
            'from': 'history-loader',
            'to': 'timescaledb',
            'cmd': 'ping -c 1 -W 2 timescaledb',
            'description': 'Ping timescaledb from history-loader'
        }
    ]

    failed = []

    for test in tests:
        from_container = test['from']
        to_host = test['to']
        cmd = test['cmd']
        desc = test['description']

        if not is_container_running(from_container):
            print(f"⏭️  Skipping: {desc} (container not running)")
            continue

        full_cmd = f"docker exec {from_container} {cmd}"
        result = run_command(full_cmd, timeout=5)

        if result and result.returncode == 0:
            print(f"✅ {desc}: Success")
        else:
            error_msg = result.stderr if result else "Timeout"
            failed.append(f"{desc}: {error_msg}")
            print(f"❌ {desc}: Failed - {error_msg[:50]}")

    print("-"*70)
    if failed:
        pytest.fail(f"Cross-container communication failed:\n" + "\n".join(f"  - {f}" for f in failed))
    else:
        print("✅ Cross-container communication working")


# ==================== INF-HEALTH-01: Service Startup Health ====================

@pytest.mark.integration
def test_service_startup_health():
    """
    INF-HEALTH-01: 모든 서비스가 시작 후 정상 상태(healthy/running)에 도달하는지 검증

    검증 포인트:
    - 모든 critical 서비스가 running 상태
    - health check가 정의된 서비스는 healthy 상태
    """
    print("\n" + "="*70)
    print("INF-HEALTH-01: Service Startup Health Check")
    print("="*70)

    # 현재 실행 중인 컨테이너 상태 조회
    cmd = "docker ps --format '{{.Names}}\t{{.Status}}'"
    result = run_command(cmd, shell=True)

    if result is None or result.returncode != 0:
        pytest.fail("Failed to get container status")

    running_containers = {}
    for line in result.stdout.strip().split('\n'):
        if '\t' in line:
            name, status = line.split('\t', 1)
            running_containers[name] = status

    print("\nContainer Status:")
    for name, status in running_containers.items():
        print(f"  {name:40} : {status}")

    # Critical 서비스 확인
    missing_services = []
    unhealthy_services = []

    for service in CRITICAL_SERVICES:
        if service not in running_containers:
            missing_services.append(service)
            print(f"\n❌ Critical service '{service}' is NOT running")
            continue

        status = running_containers[service]

        # Running 상태 확인
        if 'Up' not in status and 'running' not in status.lower():
            unhealthy_services.append(f"{service}: {status}")
            print(f"❌ Service '{service}' is not in running state: {status}")
            continue

        # Health check 상태 확인 (정의된 경우)
        if 'health' in status.lower() or 'healthy' in status.lower():
            if '(healthy)' in status:
                print(f"✅ Service '{service}' is healthy")
            elif '(unhealthy)' in status or '(starting)' in status:
                unhealthy_services.append(f"{service}: {status}")
                print(f"⚠️  Service '{service}' health check not passed: {status}")
        else:
            print(f"✅ Service '{service}' is running (no health check)")

    print("\n" + "-"*70)

    if missing_services:
        pytest.fail(f"Critical services not running: {', '.join(missing_services)}")

    if unhealthy_services:
        pytest.fail(f"Services not healthy: {', '.join(unhealthy_services)}")

    print(f"✅ All {len(CRITICAL_SERVICES)} critical services are healthy")


@pytest.mark.integration
def test_service_error_logs():
    """
    INF-HEALTH-01 (Extended): 각 서비스가 시작 후 Critical 에러를 발생시키지 않는지 로그 검증
    """
    print("\n" + "="*70)
    print("INF-HEALTH-01 Extended: Service Error Logs Check")
    print("="*70)

    error_patterns = [
        'CRITICAL',
        'FATAL',
        'Traceback (most recent call last)',
        'ConnectionError',
        'Temporary failure in name resolution'
    ]

    failed_services = {}

    for service in CRITICAL_SERVICES:
        if not is_container_running(service):
            print(f"⏭️  Skipping {service} (not running)")
            continue

        cmd = f"docker logs --tail 50 {service}"
        result = run_command(cmd, timeout=10)

        if result is None:
            print(f"⚠️  {service}: Log retrieval timeout")
            continue

        logs = result.stdout + result.stderr
        errors = []

        for pattern in error_patterns:
            if pattern in logs:
                # 에러 발생 라인 추출 (최대 3개)
                error_lines = [line for line in logs.split('\n') if pattern in line][:3]
                errors.extend([line[:100] for line in error_lines])

        if errors:
            failed_services[service] = errors
            print(f"\n❌ {service} has errors:")
            for err in errors:
                print(f"     {err}")
        else:
            print(f"✅ {service}: No critical errors")

    print("\n" + "-"*70)

    if failed_services:
        error_summary = "\n".join(
            [f"  {svc}:\n" + "\n".join([f"    - {err}" for err in errs])
             for svc, errs in failed_services.items()]
        )
        pytest.fail(f"Services with critical errors:\n{error_summary}")
    else:
        print(f"✅ No critical errors in service logs")


# ==================== INF-ENV-01: Environment Variables ====================

@pytest.mark.integration
def test_environment_variables():
    """
    INF-ENV-01: 필수 환경변수가 각 컨테이너에 올바르게 설정되었는지 검증

    검증 포인트:
    - 필수 환경변수 존재 여부
    - DB_HOST가 timescaledb로 설정됨
    - REDIS_URL이 redis:6379를 사용
    """
    print("\n" + "="*70)
    print("INF-ENV-01: Environment Variables Validation")
    print("="*70)

    failed = []

    for container, required_vars in REQUIRED_ENV_VARS.items():
        if not is_container_running(container):
            print(f"\n⏭️  Skipping {container} (not running)")
            continue

        print(f"\n{container}:")

        cmd = f"docker exec {container} env"
        result = run_command(cmd, timeout=5)

        if result is None or result.returncode != 0:
            failed.append(f"Failed to read env from '{container}'")
            print(f"  ❌ Failed to read environment variables")
            continue

        # 환경변수 파싱
        env_dict = {}
        for line in result.stdout.split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                env_dict[key] = value

        # 필수 변수 확인
        for var in required_vars:
            if var not in env_dict:
                failed.append(f"Required env var '{var}' not found in container '{container}'")
                print(f"  ❌ Missing: {var}")
                continue

            value = env_dict[var]

            # DB_HOST 검증
            if var == 'DB_HOST':
                if value == 'timescaledb':
                    print(f"  ✅ {var}={value}")
                else:
                    failed.append(f"DB_HOST should be 'timescaledb', got '{value}' in '{container}'")
                    print(f"  ❌ {var}={value} (expected: timescaledb)")

            # REDIS_URL 검증
            elif var == 'REDIS_URL':
                if 'redis://' in value and 'redis:6379' in value:
                    print(f"  ✅ {var}={value}")
                else:
                    # stock-redis도 허용 (이전 설정)
                    if 'redis://' in value and ':6379' in value:
                        print(f"  ⚠️  {var}={value} (consider using 'redis:6379')")
                    else:
                        failed.append(f"REDIS_URL malformed in '{container}': {value}")
                        print(f"  ❌ {var}={value} (invalid format)")

            # 기타 변수
            else:
                print(f"  ✅ {var}={value}")

    print("\n" + "-"*70)

    if failed:
        pytest.fail(f"Environment variable validation failed:\n" + "\n".join(f"  - {f}" for f in failed))
    else:
        print(f"✅ All environment variables are correctly configured")


if __name__ == "__main__":
    # 직접 실행 시 테스트 실행
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
