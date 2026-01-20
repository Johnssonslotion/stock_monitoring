# CHANGELOG

## [Hotfix] 2026-01-19 - Market Data Collection Recovery

### Critical Fixes

#### 1. Fixed Kiwoom Collector ImportError
- **Problem**: `ImportError: cannot import name 'get_redis_connection' from 'src.core.config'`
- **Root Cause**: Missing function in config module
- **Solution**: Added `async def get_redis_connection()` to `src/core/config.py`
- **Impact**: Kiwoom collector can now boot successfully
- **Files Changed**: 
  - `src/core/config.py` (added get_redis_connection function)

#### 2. Fixed Recovery Worker Dependency
- **Problem**: `ModuleNotFoundError: No module named 'httpx'`
- **Root Cause**: Dependency already in pyproject.toml but Docker image rebuild needed
- **Solution**: Confirmed httpx in dependencies, rebuild Docker image
- **Impact**: Recovery worker can execute data gap recovery
- **Files Changed**: None (dependency already present)

#### 3. Enhanced KIS WebSocket Stability
- **Problem**: WebSocket disconnects every 3-5 seconds with "no close frame received or sent"
- **Root Cause**: Missing heartbeat/ping mechanism
- **Solution**: Enhanced websocket connection parameters:
  - `ping_interval=30` (30s heartbeat)
  - `ping_timeout=10` (10s pong wait)
  - `close_timeout=10` (10s graceful close)
  - `max_size=10_000_000` (10MB message limit)
  - `compression=None` (disabled for lower latency)
- **Impact**: More stable WebSocket connections, reduced reconnection frequency
- **Files Changed**:
  - `src/data_ingestion/price/common/websocket_dual.py`

#### 4. Increased Collector Memory Limits
- **Problem**: Real Collector killed by OOM (Exit 137)
- **Root Cause**: Insufficient memory allocation, potential memory leak
- **Solution**: Added resource limits to docker-compose.yml:
  - KIS Service: 512MB reservation, 2GB limit
  - Kiwoom Service: 512MB reservation, 2GB limit
  - Recovery Worker: 256MB reservation, 1GB limit
- **Impact**: Prevents OOM kills, allows sustained operation
- **Files Changed**:
  - `deploy/docker-compose.yml`

### Preventive Measures

#### 1. Pre-flight Health Check Script
- **Purpose**: Automated system verification before market open
- **Features**:
  - Python dependency validation
  - Redis connectivity test
  - TimescaleDB connectivity test
  - Docker container status check
  - Disk space monitoring
  - Critical file existence validation
- **Usage**: `python scripts/preflight_check.py` (run at 08:30 KST)
- **Files Added**:
  - `scripts/preflight_check.py`

#### 2. CI/CD Smoke Test
- **Purpose**: Verify all collector containers can boot successfully
- **Features**:
  - Build verification
  - Container startup test
  - 10-second initialization wait
  - Automatic cleanup
- **Files Added**:
  - `.github/workflows/smoke_test.sh`

### Documentation

#### 1. Failure Analysis Document
- **Purpose**: Comprehensive root cause analysis of 2026-01-19 failures
- **Contents**:
  - Detailed error analysis for all 4 critical failures
  - Root cause identification
  - Recovery action plans
  - Long-term improvement strategy
  - Roadmap integration proposals
- **Files Added**:
  - `docs/ideas/stock_monitoring/ID-2026-01-19-collection-failure.md`

### Branch Information
- **Branch**: `hotfix/2026-01-19-market-data-recovery`
- **Base**: `develop`
- **Related Issues**: ISSUE-004-market-open-failure

### Testing Checklist
- [x] Kiwoom collector imports without errors
- [x] KIS WebSocket heartbeat configuration
- [x] Memory limits configured in docker-compose
- [x] Pre-flight check script created
- [x] CI/CD smoke test script created
- [ ] All containers boot successfully
- [ ] Pre-flight check passes
- [ ] Full system restart test
- [ ] 24-hour stability test

### Known Issues
- Orderbook data from 2026-01-19 market open is **irrecoverable** (real-time only)
- Tick data may be recoverable using REST API post-market

### Deployment Instructions
1. Merge hotfix branch to develop
2. Build Docker images: `docker compose -f deploy/docker-compose.yml build`
3. Run pre-flight check: `python scripts/preflight_check.py`
4. Deploy with profile: `docker compose --profile real up -d`
5. Monitor logs for 1 hour
6. Schedule cron for daily pre-flight check: `30 8 * * * cd /path/to/project && python scripts/preflight_check.py`

### Rollback Plan
If issues persist:
1. Stop all collectors: `docker compose down`
2. Checkout previous stable commit
3. Rebuild: `docker compose build`
4. Deploy: `docker compose --profile real up -d`

---

**Date**: 2026-01-19T02:56:00Z  
**Author**: Antigravity Agent  
**Severity**: P0 - Critical Production Fix
