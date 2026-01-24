# RFC-009 & SSH-Worker Test Strategy

## 테스트 계층 구조 (Test Pyramid)

```
                    ┌─────────────────────┐
                    │  Container E2E      │  ← 실제 운영 환경 모사
                    │  (docker-compose)   │     (Chaos Testing)
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │  Integration Tests  │  ← Redis/DB/API 통합
                    │  (pytest-asyncio)   │     (Market Schedule)
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │   Unit Tests        │  ← 개별 함수/클래스
                    │   (pytest)          │     (RFC-009 Compliance)
                    └─────────────────────┘
```

## 디렉토리 구조

```
tests/
├── rfc009/                              # RFC-009 전용 테스트
│   ├── unit/                            # Unit Tests (빠른 실행)
│   │   ├── test_startup_health.py       # RFC-009 Startup Health Checker
│   │   ├── test_ground_truth_policy.py  # Ground Truth Priority 로직
│   │   ├── test_market_schedule.py      # Market Phase Detection
│   │   └── test_tiered_recovery.py      # 4단계 복구 로직
│   │
│   ├── integration/                     # Integration Tests (Redis/DB 필요)
│   │   ├── test_gap_recovery_engine.py  # Gap Detection + Recovery 통합
│   │   ├── test_api_hub_compliance.py   # APIHubClient Rate Limit 검증
│   │   └── test_schema_migration.py     # source_type 컬럼 검증
│   │
│   ├── e2e/                             # E2E Tests (Container 필요)
│   │   ├── test_ssh_worker_startup.py   # Container Startup Hook 검증
│   │   ├── test_market_aware_filter.py  # Market Phase별 동작 검증
│   │   └── test_chaos_recovery.py       # 카오스 테스트 (고의 장애)
│   │
│   └── fixtures/                        # 테스트 데이터
│       ├── mock_redis.py                # Redis Mock
│       ├── mock_db.py                   # TimescaleDB Mock
│       └── sample_gaps.json             # 샘플 Gap 데이터
│
├── conftest.py                          # Shared Fixtures
└── README.md                            # 이 파일
```

---

## Tier 1: Unit Tests

### 목표
- 개별 함수/클래스 동작 검증
- Mock/Stub 사용으로 빠른 실행 (< 1초)
- RFC-009 준수 로직 단위 검증

### 테스트 대상

#### 1.1 RFC-009 Startup Health Checker
**파일**: `tests/rfc009/unit/test_startup_health.py`

```python
import pytest
from src.core.startup_health import RFC009StartupChecker, HealthCheckResult

class TestRFC009StartupChecker:
    """RFC-009 Section 4.5: Self-Diagnosis & Fail-Fast"""
    
    @pytest.mark.asyncio
    async def test_all_checks_pass(self, mock_redis, mock_db):
        """정상 환경에서 모든 체크 통과"""
        checker = RFC009StartupChecker(worker_name="test-worker")
        result = await checker.check_all()
        
        assert result is True
        assert all(r.passed for r in checker.results)
    
    @pytest.mark.asyncio
    async def test_missing_env_var_fails(self, mock_redis, mock_db):
        """필수 환경변수 누락 시 Exit 1"""
        import os
        del os.environ["KIS_API_KEY"]
        
        checker = RFC009StartupChecker(worker_name="test-worker")
        
        with pytest.raises(SystemExit) as exc_info:
            await checker.check_all()
        
        assert exc_info.value.code == 1
    
    @pytest.mark.asyncio
    async def test_rate_limiter_config_validation(self, mock_redis):
        """RFC-009 Section 4.1: Rate Limiter 설정 검증"""
        checker = RFC009StartupChecker(worker_name="test-worker")
        result = await checker._check_rate_limiter_config()
        
        assert result.passed is True
        assert result.rfc_reference == "RFC-009 Section 4.1"
    
    @pytest.mark.asyncio
    async def test_ground_truth_schema_exists(self, mock_db):
        """RFC-009 Section 3.3: source_type 컬럼 존재 검증"""
        checker = RFC009StartupChecker(worker_name="test-worker")
        result = await checker._check_ground_truth_schema()
        
        assert result.passed is True
        assert "source_type" in result.check_name
```

#### 1.2 Ground Truth Policy
**파일**: `tests/rfc009/unit/test_ground_truth_policy.py`

```python
import pytest
from src.core.ground_truth import GroundTruthPolicy, DataSource

class TestGroundTruthPolicy:
    """RFC-009 Section 3.1: 참값 우선순위 검증"""
    
    def test_priority_hierarchy(self):
        """우선순위: REST API > Verified Ticks > Unverified"""
        assert GroundTruthPolicy.get_priority(DataSource.REST_API_KIS) == 1
        assert GroundTruthPolicy.get_priority(DataSource.TICK_AGGREGATION_VERIFIED) == 2
        assert GroundTruthPolicy.get_priority(DataSource.TICK_AGGREGATION_UNVERIFIED) == 3
    
    def test_should_use_for_backtesting(self):
        """백테스팅은 REST API만 사용"""
        assert GroundTruthPolicy.should_use_for_backtesting(DataSource.REST_API_KIS) is True
        assert GroundTruthPolicy.should_use_for_backtesting(DataSource.TICK_AGGREGATION_VERIFIED) is False
    
    def test_should_use_for_realtime(self):
        """실시간 알고리즘은 검증된 틱도 사용 가능"""
        assert GroundTruthPolicy.should_use_for_realtime(DataSource.REST_API_KIS) is True
        assert GroundTruthPolicy.should_use_for_realtime(DataSource.TICK_AGGREGATION_VERIFIED) is True
        assert GroundTruthPolicy.should_use_for_realtime(DataSource.TICK_AGGREGATION_UNVERIFIED) is False
```

#### 1.3 Market Schedule
**파일**: `tests/rfc009/unit/test_market_schedule.py`

```python
import pytest
from datetime import datetime, time
from src.core.market_schedule import MarketSchedule, MarketPhase

class TestMarketSchedule:
    """SSH-Worker Section 5.5 & RFC-009 Section 6.2: Market-Aware Logic"""
    
    def test_pre_market_detection(self):
        """08:30 KST는 PRE_MARKET"""
        test_time = datetime(2026, 1, 27, 8, 30, 0)  # Monday 08:30 KST
        phase = MarketSchedule.get_phase_at(test_time)
        assert phase == MarketPhase.PRE_MARKET
    
    def test_trading_hours_detection(self):
        """10:00 KST는 TRADING"""
        test_time = datetime(2026, 1, 27, 10, 0, 0)
        phase = MarketSchedule.get_phase_at(test_time)
        assert phase == MarketPhase.TRADING
    
    def test_weekend_detection(self):
        """토요일은 WEEKEND"""
        test_time = datetime(2026, 1, 25, 10, 0, 0)  # Saturday
        phase = MarketSchedule.get_phase_at(test_time)
        assert phase == MarketPhase.WEEKEND
    
    def test_should_not_recover_during_pre_market(self):
        """PRE_MARKET에는 복구 연기 (SSH-Worker Predictive Priming)"""
        assert MarketSchedule.should_trigger_recovery(MarketPhase.PRE_MARKET) is False
    
    def test_should_recover_during_trading(self):
        """TRADING 중에는 즉시 복구"""
        assert MarketSchedule.should_trigger_recovery(MarketPhase.TRADING) is True
    
    def test_recovery_priority_high_during_trading(self):
        """장 중에는 high priority"""
        priority = MarketSchedule.get_recovery_priority(MarketPhase.TRADING)
        assert priority == "high"
```

#### 1.4 Tiered Recovery Logic
**파일**: `tests/rfc009/unit/test_tiered_recovery.py`

```python
import pytest
from src.core.gap_recovery import GapRecoveryEngine, RecoveryTier, GapInterval
from datetime import datetime

class TestTieredRecovery:
    """SSH-Worker Section 5.3 + RFC-009 Section 3.1: 4단계 복구"""
    
    @pytest.mark.asyncio
    async def test_tier0_local_log_recovery(self, mock_local_logs):
        """TIER-0: 로컬 로그 복구 (Zero Cost)"""
        engine = GapRecoveryEngine(worker_id="test-worker")
        gap = GapInterval(
            symbol="005930",
            start_time=datetime(2026, 1, 27, 10, 0, 0),
            end_time=datetime(2026, 1, 27, 10, 1, 0)
        )
        
        tier = await engine._recover_gap_tiered(gap)
        
        assert tier == RecoveryTier.TIER_0_LOCAL_LOGS
        assert mock_local_logs.read_called is True
    
    @pytest.mark.asyncio
    async def test_tier1_rest_api_recovery(self, mock_api_hub):
        """TIER-1: REST API 복구 (Ground Truth)"""
        engine = GapRecoveryEngine(worker_id="test-worker")
        gap = GapInterval(
            symbol="005930",
            start_time=datetime(2026, 1, 27, 10, 0, 0),
            end_time=datetime(2026, 1, 27, 10, 1, 0)
        )
        
        # 로컬 로그 없음
        tier = await engine._recover_gap_tiered(gap)
        
        assert tier == RecoveryTier.TIER_1_REST_API
        assert mock_api_hub.request_called is True
        assert mock_api_hub.last_tr_id == "FHKST03010200"
    
    @pytest.mark.asyncio
    async def test_recovery_stats_tracking(self):
        """복구 통계 추적 (RFC-009 준수율 계산)"""
        engine = GapRecoveryEngine(worker_id="test-worker")
        stats = {
            "tier_0_local": 50,
            "tier_1_rest_api": 30,
            "tier_2_verified_ticks": 15,
            "tier_3_manual": 5,
        }
        
        compliance_rate = engine._calculate_compliance_rate(stats)
        
        # TIER-0 + TIER-1 = 80 / 100 = 80%
        assert compliance_rate == 80.0
```

### 실행 방법
```bash
# 전체 Unit 테스트 실행
pytest tests/rfc009/unit/ -v

# 특정 테스트만 실행
pytest tests/rfc009/unit/test_startup_health.py::TestRFC009StartupChecker::test_missing_env_var_fails -v

# Coverage 측정
pytest tests/rfc009/unit/ --cov=src/core --cov-report=html
```

---

## Tier 2: Integration Tests

### 목표
- 실제 Redis/DB/API 연동 검증
- E2E보다 빠르지만 실제 인프라 필요 (< 10초)
- RFC-009 전체 플로우 검증

### 테스트 대상

#### 2.1 Gap Recovery Engine (통합)
**파일**: `tests/rfc009/integration/test_gap_recovery_engine.py`

```python
import pytest
from src.core.gap_recovery import GapRecoveryEngine
from datetime import datetime, timedelta

@pytest.mark.integration
class TestGapRecoveryEngineIntegration:
    """SSH-Worker + RFC-009 통합 복구 엔진"""
    
    @pytest.mark.asyncio
    async def test_detect_gaps_from_redis(self, redis_client, db_pool):
        """Redis last_heartbeat 기반 Gap 탐지"""
        # Setup: 30분 전 heartbeat 기록
        await redis_client.set(
            "worker:realtime-worker:last_heartbeat",
            (datetime.now() - timedelta(minutes=30)).isoformat()
        )
        
        engine = GapRecoveryEngine(
            worker_id="realtime-worker",
            redis_url="redis://localhost:6379/1"
        )
        
        gaps = await engine._detect_gaps()
        
        assert len(gaps) > 0
        assert gaps[0].duration_minutes == 30
    
    @pytest.mark.asyncio
    async def test_end_to_end_recovery_flow(self, redis_client, db_pool, api_hub):
        """Gap 탐지 → 복구 → DB 저장 전체 플로우"""
        # Setup: 10분 전 heartbeat
        await redis_client.set(
            "worker:test-worker:last_heartbeat",
            (datetime.now() - timedelta(minutes=10)).isoformat()
        )
        
        engine = GapRecoveryEngine(worker_id="test-worker")
        stats = await engine.detect_and_recover()
        
        assert stats["gaps"] > 0
        assert stats["recovered"] > 0
        
        # DB 검증: source_type = 'REST_API_KIS'
        async with db_pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT COUNT(*) FROM market_candles
                WHERE source_type = 'REST_API_KIS'
                AND created_at >= NOW() - INTERVAL '1 minute'
            """)
            assert result > 0
```

#### 2.2 API Hub Compliance
**파일**: `tests/rfc009/integration/test_api_hub_compliance.py`

```python
import pytest
from src.api_gateway.hub.client import APIHubClient

@pytest.mark.integration
class TestAPIHubCompliance:
    """RFC-009 Section 4.2: 모든 REST API는 APIHubClient 경유"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, redis_client):
        """Rate Limit 초과 시 대기"""
        client = APIHubClient(redis_url="redis://localhost:6379/15")
        
        # 60개 요청 (Rate Limit: 30 req/s)
        start_time = datetime.now()
        
        for i in range(60):
            await client.request(
                provider="KIS",
                tr_id="FHKST03010200",
                params={"FID_INPUT_ISCD": "005930"}
            )
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # 최소 2초 이상 걸려야 함 (60 req / 30 req/s = 2s)
        assert elapsed >= 2.0
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, redis_client):
        """Timeout 발생 시 graceful degradation"""
        client = APIHubClient(redis_url="redis://localhost:6379/15")
        
        # Rate Limit 소진
        for _ in range(100):
            await client.request(
                provider="KIS",
                tr_id="FHKST03010200",
                params={"FID_INPUT_ISCD": "005930"},
                timeout=0.1  # 짧은 timeout
            )
        
        # Timeout 발생해도 예외 없이 None 반환
        result = await client.request(
            provider="KIS",
            tr_id="FHKST03010200",
            params={"FID_INPUT_ISCD": "005930"},
            timeout=0.1
        )
        
        assert result is None or "timeout" in str(result).lower()
```

---

## Tier 3: Container E2E Tests

### 목표
- 실제 운영 환경 모사
- Docker Compose 기반 전체 시스템 검증
- Chaos Engineering (고의 장애 주입)

### 테스트 대상

#### 3.1 SSH-Worker Startup Hook
**파일**: `tests/rfc009/e2e/test_ssh_worker_startup.py`

```python
import pytest
import subprocess
import time
from datetime import datetime, timedelta

@pytest.mark.e2e
class TestSSHWorkerStartup:
    """SSH-Worker Section 5.1-5.5: Startup Hook 전체 검증"""
    
    def test_startup_with_gap_triggers_recovery(self):
        """컨테이너 재시작 시 Gap 탐지 및 자동 복구"""
        
        # 1. Redis에 과거 heartbeat 설정 (30분 전)
        subprocess.run([
            "docker", "exec", "deploy-redis", "redis-cli", "-n", "1",
            "SET", "worker:realtime-worker:last_heartbeat",
            (datetime.now() - timedelta(minutes=30)).isoformat()
        ])
        
        # 2. 컨테이너 재시작
        subprocess.run(["docker", "restart", "realtime-worker"])
        time.sleep(15)
        
        # 3. 로그 검증: "Gap detected" 메시지 확인
        logs = subprocess.check_output([
            "docker", "logs", "realtime-worker", "--since", "20s"
        ]).decode()
        
        assert "Gap detected" in logs
        assert "Recovery triggered" in logs
        assert "RFC-009" in logs  # RFC 준수 로깅
    
    def test_startup_without_gap_skips_recovery(self):
        """최근 heartbeat가 있으면 복구 스킵"""
        
        # 1. Redis에 최근 heartbeat 설정 (1분 전)
        subprocess.run([
            "docker", "exec", "deploy-redis", "redis-cli", "-n", "1",
            "SET", "worker:realtime-worker:last_heartbeat",
            (datetime.now() - timedelta(minutes=1)).isoformat()
        ])
        
        # 2. 컨테이너 재시작
        subprocess.run(["docker", "restart", "realtime-worker"])
        time.sleep(10)
        
        # 3. 로그 검증: "No gaps detected" 확인
        logs = subprocess.check_output([
            "docker", "logs", "realtime-worker", "--since", "15s"
        ]).decode()
        
        assert "No gaps detected" in logs or "Recovery skipped" in logs
    
    def test_fail_fast_on_missing_env_var(self):
        """RFC-009 Section 4.5: 필수 환경변수 누락 시 Exit 1"""
        
        # 1. KIS_API_KEY 제거하고 컨테이너 시작
        subprocess.run([
            "docker", "run", "--rm", "-d",
            "--name", "test-worker-fail",
            "--network", "stock_prod_default",
            "-e", "REDIS_URL=redis://redis:6379/1",
            # KIS_API_KEY 의도적 누락
            "stock-monitoring:latest",
            "python", "-m", "src.data_ingestion.realtime.worker"
        ])
        
        time.sleep(5)
        
        # 2. 컨테이너 상태 확인
        result = subprocess.run([
            "docker", "ps", "-a", "--filter", "name=test-worker-fail",
            "--format", "{{.Status}}"
        ], capture_output=True, text=True)
        
        # Exit 1로 종료되었는지 확인
        assert "Exited (1)" in result.stdout
        
        # Cleanup
        subprocess.run(["docker", "rm", "-f", "test-worker-fail"], stderr=subprocess.DEVNULL)
```

#### 3.2 Market-Aware Filter
**파일**: `tests/rfc009/e2e/test_market_aware_filter.py`

```python
import pytest
import subprocess
import time
from datetime import datetime

@pytest.mark.e2e
class TestMarketAwareFilter:
    """RFC-009 Section 6.2 + SSH-Worker Section 5.5: Market Phase별 동작"""
    
    def test_pre_market_enters_preparation_mode(self):
        """PRE_MARKET (08:00-09:00)에는 준비 모드"""
        
        # 1. 시스템 시간을 08:30 KST로 설정 (Mock)
        # Note: 실제로는 환경변수나 Mock으로 처리
        subprocess.run([
            "docker", "exec", "realtime-worker",
            "python", "-c",
            "from src.core.market_schedule import MarketSchedule; "
            "print(MarketSchedule.get_current_phase())"
        ])
        
        # 2. 컨테이너 재시작
        subprocess.run(["docker", "restart", "realtime-worker"])
        time.sleep(10)
        
        # 3. 로그 검증
        logs = subprocess.check_output([
            "docker", "logs", "realtime-worker", "--since", "15s"
        ]).decode()
        
        assert "PRE-MARKET detected" in logs
        assert "Entering preparation mode" in logs
        assert "Recovery triggered" not in logs  # 복구 스킵
    
    def test_weekend_skips_recovery(self):
        """주말에는 복구 불필요"""
        
        # Mock: 현재 시간을 토요일로 설정
        # (실제 구현에서는 테스트용 환경변수 사용)
        
        subprocess.run(["docker", "restart", "realtime-worker"])
        time.sleep(10)
        
        logs = subprocess.check_output([
            "docker", "logs", "realtime-worker", "--since", "15s"
        ]).decode()
        
        # 주말이면 "WEEKEND detected" 또는 "Recovery skipped"
        assert "WEEKEND" in logs or "Recovery skipped" in logs
```

#### 3.3 Chaos Recovery Test
**파일**: `tests/rfc009/e2e/test_chaos_recovery.py`

```python
import pytest
import subprocess
import time
import random

@pytest.mark.e2e
@pytest.mark.chaos
class TestChaosRecovery:
    """SSH-Worker Section 6.4: Chaos Engineering"""
    
    def test_multiple_worker_restart_with_jitter(self):
        """10개 워커 동시 재시작 시 Jitter 동작"""
        
        # 1. 10개 워커 컨테이너 동시 Kill
        worker_names = [f"test-worker-{i}" for i in range(10)]
        
        for name in worker_names:
            subprocess.run([
                "docker", "run", "-d", "--rm",
                "--name", name,
                "--network", "stock_prod_default",
                "-e", "REDIS_URL=redis://redis:6379/1",
                "-e", "WORKER_JITTER_MAX=5",  # 최대 5초 Jitter
                "stock-monitoring:latest"
            ])
        
        time.sleep(2)
        
        # 2. 동시 Kill
        for name in worker_names:
            subprocess.run(["docker", "kill", name], stderr=subprocess.DEVNULL)
        
        # 3. 동시 재시작
        for name in worker_names:
            subprocess.run([
                "docker", "start", name
            ], stderr=subprocess.DEVNULL)
        
        time.sleep(10)
        
        # 4. API Hub 로그 확인: Rate Limit 초과 없음
        logs = subprocess.check_output([
            "docker", "logs", "deploy-gateway-worker-real", "--since", "15s"
        ]).decode()
        
        assert "429" not in logs  # Rate Limit 초과 없음
        assert "Rate limit exceeded" not in logs
        
        # Cleanup
        for name in worker_names:
            subprocess.run(["docker", "rm", "-f", name], stderr=subprocess.DEVNULL)
    
    def test_container_network_failure_recovery(self):
        """네트워크 단절 후 복구"""
        
        # 1. 컨테이너를 네트워크에서 분리
        subprocess.run([
            "docker", "network", "disconnect", "stock_prod_default", "realtime-worker"
        ])
        
        time.sleep(10)
        
        # 2. 네트워크 재연결
        subprocess.run([
            "docker", "network", "connect", "stock_prod_default", "realtime-worker"
        ])
        
        time.sleep(10)
        
        # 3. 로그 검증: 자동 복구 확인
        logs = subprocess.check_output([
            "docker", "logs", "realtime-worker", "--since", "25s"
        ]).decode()
        
        assert "Network reconnected" in logs or "Recovery triggered" in logs
    
    def test_redis_failure_causes_fail_fast(self):
        """Redis 연결 실패 시 Fail-Fast"""
        
        # 1. Redis 컨테이너 중지
        subprocess.run(["docker", "stop", "deploy-redis"])
        
        # 2. 워커 재시작 시도
        result = subprocess.run([
            "docker", "restart", "realtime-worker"
        ])
        
        time.sleep(5)
        
        # 3. 컨테이너 상태 확인: Exit 1
        status = subprocess.check_output([
            "docker", "ps", "-a", "--filter", "name=realtime-worker",
            "--format", "{{.Status}}"
        ]).decode()
        
        assert "Exited (1)" in status
        
        # Cleanup: Redis 재시작
        subprocess.run(["docker", "start", "deploy-redis"])
        time.sleep(5)
        subprocess.run(["docker", "restart", "realtime-worker"])
```

### 실행 방법

```bash
# E2E 테스트 실행 (Docker 필요)
pytest tests/rfc009/e2e/ -v -m e2e

# Chaos 테스트 실행
pytest tests/rfc009/e2e/test_chaos_recovery.py -v -m chaos

# 특정 시나리오만 실행
pytest tests/rfc009/e2e/test_ssh_worker_startup.py::TestSSHWorkerStartup::test_fail_fast_on_missing_env_var -v
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/rfc009-tests.yml

name: RFC-009 Test Suite

on:
  push:
    branches: [main, feat/*, fix/*]
  pull_request:

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      
      - name: Run Unit Tests
        run: pytest tests/rfc009/unit/ -v --cov=src/core --cov-report=xml
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
      postgres:
        image: timescale/timescaledb:latest-pg15
        env:
          POSTGRES_PASSWORD: password
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run Integration Tests
        run: pytest tests/rfc009/integration/ -v -m integration
        env:
          REDIS_URL: redis://localhost:6379/1
          DB_HOST: localhost
          DB_PORT: 5432

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker Images
        run: docker-compose -f docker-compose.test.yml build
      
      - name: Start Services
        run: docker-compose -f docker-compose.test.yml up -d
      
      - name: Wait for Services
        run: sleep 30
      
      - name: Run E2E Tests
        run: |
          docker-compose -f docker-compose.test.yml run --rm test-runner \
            pytest tests/rfc009/e2e/ -v -m e2e
      
      - name: Run Chaos Tests
        run: |
          docker-compose -f docker-compose.test.yml run --rm test-runner \
            pytest tests/rfc009/e2e/test_chaos_recovery.py -v -m chaos
      
      - name: Collect Logs
        if: failure()
        run: |
          docker-compose -f docker-compose.test.yml logs > test-logs.txt
      
      - name: Upload Logs
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: test-logs
          path: test-logs.txt
      
      - name: Cleanup
        if: always()
        run: docker-compose -f docker-compose.test.yml down -v
```

---

## Test Coverage Goals

| Category | Target Coverage | Current | Status |
|----------|----------------|---------|--------|
| Unit Tests | 90% | - | 🔴 Not Started |
| Integration Tests | 80% | - | 🔴 Not Started |
| E2E Tests | Critical Paths | - | 🔴 Not Started |

### Critical Paths
1. ✅ Startup Health Check (RFC-009 Section 4.5)
2. ✅ Gap Detection + Recovery (SSH-Worker Section 5)
3. ✅ Market-Aware Filter (RFC-009 Section 6.2)
4. ✅ Rate Limit Enforcement (RFC-009 Section 4.2)
5. ✅ Fail-Fast on Configuration Error

---

## Quick Start

### 로컬 개발 환경

```bash
# 1. 의존성 설치
pip install -r requirements-dev.txt

# 2. Unit 테스트 실행
pytest tests/rfc009/unit/ -v

# 3. Integration 테스트 실행 (Redis/DB 필요)
docker-compose -f docker-compose.test.yml up -d redis timescaledb
pytest tests/rfc009/integration/ -v -m integration

# 4. E2E 테스트 실행
docker-compose -f docker-compose.test.yml up -d
pytest tests/rfc009/e2e/ -v -m e2e

# 5. 전체 테스트 실행
pytest tests/rfc009/ -v
```

### CI 환경

```bash
# GitHub Actions에서 자동 실행
git push origin feat/rfc009-testing

# 또는 로컬에서 CI 시뮬레이션
act -j unit-tests
act -j integration-tests
act -j e2e-tests
```

---

## Maintenance

### 테스트 추가 시

1. 적절한 계층 선택 (Unit/Integration/E2E)
2. RFC-009 Section 번호 명시
3. 의미 있는 테스트 이름 사용
4. Docstring에 검증 목표 명시

### 테스트 실패 시

1. 로그 확인: `docker-compose logs`
2. 컨테이너 상태: `docker ps -a`
3. Redis 상태: `docker exec deploy-redis redis-cli -n 1 PING`
4. DB 연결: `docker exec stock_prod-timescale psql -U postgres -d stockval -c "SELECT 1"`

---

## References

- [RFC-009: Ground Truth & API Control](../../docs/governance/rfc/RFC-009-ground-truth-api-control.md)
- [SSH-Worker Idea](../../docs/ideas/stock_monitoring/ID-stateful-self-healing-worker.md)
- [Council Review Workflow](../../.agent/workflows/council-review.md)
