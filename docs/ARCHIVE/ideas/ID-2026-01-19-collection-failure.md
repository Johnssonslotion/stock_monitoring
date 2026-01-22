# IDEA: 2026-01-19 Data Collection Failure Analysis & Recovery Strategy

**Status**: 🌿 Sprouting (Drafting)  
**Priority**: P0 (Critical - Production Data Loss)  
**Created**: 2026-01-19T02:48:40Z  
**Category**: Infrastructure / Reliability

---

## 1. 개요 (Abstract)

### 문제 (Problem)
2026년 1월 19일, 장 시작 시점부터 실시간 데이터 수집이 완전히 실패했습니다. 복수의 핵심 collector 컨테이너가 부팅 실패 상태에 빠져 시장 개장 시간대의 **모든 틱/오더북 데이터가 손실**되었습니다.

### 영향 (Impact)
- ❌ **Kiwoom Collector**: 완전 장애 (ImportError로 무한 재시작)
- ⚠️ **KIS Collector**: 부분 장애 (WebSocket 연결 불안정, "no close frame" 에러 반복)
- ❌ **Recovery Worker**: 완전 장애 (Missing dependency)
- ❌ **Real Collector**: 종료됨 (Exit 137 - OOM Kill 의심)

**비즈니스 영향**:
- 장 초반 데이터 완전 손실 → 백테스트 데이터 품질 저하
- 실시간 전략 실행 불가
- 시스템 신뢰성 심각한 타격

---

## 2. 근본 원인 분석 (Root Cause Analysis)

### 2.1 Kiwoom Collector - Critical Import Error

**에러 메시지**:
```python
ImportError: cannot import name 'get_redis_connection' from 'src.core.config'
```

**원인**:
- `kiwoom_ws.py:9`에서 `get_redis_connection` import 시도
- **`src/core/config.py`에 해당 함수가 존재하지 않음** ✅ (파일 확인 완료)
- 이는 코드가 **Spec 없이 직접 develop 브랜치에 커밋**되어 발생한 전형적인 Governance 위반 사례

**근본 원인**:
1. **Specification-First Protocol 미준수**: Kiwoom Collector가 RFC/Spec 문서 없이 개발됨
2. **Pre-merge Test 누락**: develop 브랜치에서 CI 테스트가 실행되지 않음
3. **Dependency Injection 패턴 불일치**: 기존 KIS Collector와 다른 Redis 연결 방식 사용

**영향 범위**:
- 🔴 **Collector 완전 불능** (부팅 자체 실패)
- 🔴 **Kiwoom 전용 심볼 수집 불가** (ETF 레버리지/인버스 상품군)

---

### 2.2 KIS Collector - WebSocket Stability Issue

**에러 패턴**:
```
ERROR:src.data_ingestion.price.common.websocket_dual:⚠️ [ORDERBOOK] Error: no close frame received or sent
INFO:src.data_ingestion.price.common.websocket_dual:🔌 [ORDERBOOK] Connecting to ws://ops.koreainvestment.com:21000/H0STCNT0...
INFO:src.data_ingestion.price.common.websocket_dual:✅ [ORDERBOOK] Connected.
INFO:src.data_ingestion.price.common.websocket_dual:🔄 [ORDERBOOK] Re-subscribing to 1 active markets...
ERROR:src.data_ingestion.price.common.websocket_dual:⚠️ [ORDERBOOK] Error: no close frame received or sent
```

**분석**:
- 연결은 성공하나 **3-5초마다 끊김과 재연결 반복**
- Orderbook 데이터는 publish되고 있으나, 연결 불안정으로 데이터 유실 가능
- `websocket_dual.py`의 재연결 로직은 작동하나, **루트 원인이 해결되지 않음**

**가능한 원인**:
1. **KIS API 서버 측 이슈** (서버 점검/불안정)
2. **Heartbeat/Ping 미구현** → 서버가 idle connection 으로 판단하여 강제 종료
3. **네트워크 불안정** (Container → KIS 서버 구간)
4. **구독 패킷 과부하** (너무 많은 심볼을 한 번에 구독)

**영향 범위**:
- 🟡 **Partial Data Loss** (연결이 끊기는 시점의 틱 데이터 손실)
- 🟡 **Orderbook 품질 저하** (10-depth 데이터 불완전)

---

### 2.3 Recovery Worker - Missing Dependency

**에러 메시지**:
```python
ModuleNotFoundError: No module named 'httpx'
```

**원인**:
- `scripts/recovery/validate_and_recover.py:14`에서 `httpx` import 시도
- Docker image에 `httpx`가 설치되지 않음
- `pyproject.toml`에 `httpx` 의존성 누락 또는 Docker 빌드 시 미설치

**근본 원인**:
1. **Dependency Management 불일치**: 로컬 환경에서만 동작하고 Docker에서 미검증
2. **Docker Multi-stage Build 이슈**: 의존성 설치 단계에서 누락
3. **Test Coverage 부족**: Recovery Worker에 대한 Integration Test 없음

**영향 범위**:
- 🔴 **데이터 Gap Recovery 불가능** (과거 누락 데이터 복구 메커니즘 마비)
- 🔴 **오늘 손실된 데이터 영구 손실 위험**

---

### 2.4 Real Collector - OOM Kill (Exit 137)

**상태**:
```
1f81c8c9b7e3   3be092b44ebd   Exited (137) 2 hours ago
```

**분석**:
- Exit Code 137 = `SIGKILL` (OOM Killer)
- **메모리 부족으로 커널이 프로세스 강제 종료**

**가능한 원인**:
1. **메모리 누수** (Memory Leak) - WebSocket 메시지 버퍼 해제 누락
2. **과도한 심볼 구독** (너무 많은 실시간 스트림)
3. **Container 메모리 제한** (docker-compose.yml에서 memory limit 과도하게 낮음)
4. **Raw Logger 버퍼 오버플로우** (Disk I/O 지연으로 로그 메모리 적재)

**영향 범위**:
- 🔴 **Unified Real Collector 완전 정지** (KIS + Kiwoom 통합 수집기)
- 🔴 **모든 실시간 데이터 스트림 중단**

---

## 3. 긴급 복구 조치 (Immediate Recovery Actions)

### 3.1 Kiwoom Collector Fix (P0)

**해결 방법**:
1. `src/core/config.py`에 `get_redis_connection` 함수 추가
2. 또는 `kiwoom_ws.py`를 기존 KIS Collector와 동일한 Redis 연결 패턴으로 수정

**권장 사항**:
```python
# Option 1: Add to src/core/config.py
async def get_redis_connection():
    """Get async Redis connection"""
    import redis.asyncio as redis
    return await redis.from_url(settings.data.redis_url)

# Option 2: Modify kiwoom_ws.py (align with KIS pattern)
import redis.asyncio as redis
# In __init__ or start():
self.redis = await redis.from_url(os.getenv("REDIS_URL"))
```

**검증 방법**:
```bash
docker-compose up -d kiwoom-service
docker logs -f kiwoom-service  # Should NOT see ImportError
```

---

### 3.2 Recovery Worker Fix (P0)

**해결 방법**:
```bash
# Add to pyproject.toml [tool.poetry.dependencies]
httpx = "^0.25.0"

# Rebuild Docker image
docker-compose build recovery-worker
docker-compose up -d recovery-worker
```

**검증**:
```bash
docker logs recovery-worker  # Should NOT see ModuleNotFoundError
```

---

### 3.3 KIS WebSocket Stability (P1)

**단기 조치**:
1. **Ping/Pong 구현** (Heartbeat)
   ```python
   # In websocket_dual.py connection loop
   asyncio.create_task(self._heartbeat())
   
   async def _heartbeat(self):
       while self.ws and not self.ws.closed:
           await self.ws.ping()
           await asyncio.sleep(30)  # Every 30 seconds
   ```

2. **구독 심볼 수 제한/분산**
   - 현재: 모든 심볼을 한 번에 구독
   - 개선: 100개 단위로 분할 구독

3. **Exponential Backoff 재연결**
   ```python
   retry_delay = min(2 ** attempt, 60)  # Max 60 seconds
   ```

---

### 3.4 Real Collector Memory Issue (P1)

**진단 명령**:
```bash
docker stats real-collector  # Check memory usage
docker inspect real-collector | grep -i memory
```

**조치**:
1. Memory Limit 상향 (docker-compose.yml)
   ```yaml
   deploy:
     resources:
       limits:
         memory: 2G  # 현재값 확인 필요, 2GB로 증설
   ```

2. Raw Logger 설정 조정
   ```python
   # Reduce retention
   RawWebSocketLogger(retention_hours=24)  # 48h → 24h
   
   # Add buffer flush
   async def flush_buffer_periodically(self):
       # Flush every 5 minutes
   ```

---

## 4. 장기 개선 전략 (Long-term Strategy)

### 4.1 Pre-flight Health Check (IDEA-001 구현)

**목표**: 장 시작 전 자동 시스템 점검

**컴포넌트**:
1. **Dependency Validator**
   - 모든 Python import 검증
   - Docker container 부팅 smoke test
   
2. **Connectivity Check**
   - KIS API reachability
   - Kiwoom API reachability
   - TimescaleDB connection
   - Redis connection

3. **Resource Monitor**
   - CPU/Memory 사용률 체크
   - Disk 여유 공간 확인
   - 메모리 누수 탐지

**구현 위치**: `scripts/preflight_check.py`

**Cron 스케줄**: 매일 08:30 (장 시작 30분 전)

**알림 메커니즘**:
- Slack Webhook (현재 미구현)
- 또는 Email Alert
- 또는 Discord Bot

---

### 4.2 CI/CD Governance 강화

**문제**: develop 브랜치에 직접 커밋 → 테스트 누락

**해결 방안**:
1. **GitHub Branch Protection**
   - develop 브랜치 직접 push 금지
   - PR 필수, 1명 이상 리뷰 필요
   - CI 통과 필수

2. **Pre-merge Tests**
   ```yaml
   # .github/workflows/ci.yml
   - name: Docker Build Test
     run: docker-compose build
   
   - name: Container Boot Test
     run: |
       docker-compose up -d
       sleep 10
       docker-compose ps | grep "Up"  # All containers should be Up
   
   - name: Import Test
     run: |
       docker-compose exec -T kis-service python -c "from src.data_ingestion.price.kr.kiwoom_ws import KiwoomWSCollector"
   ```

3. **Spec-First Workflow 엄격 적용**
   - 모든 새 Collector는 RFC 필수
   - ADR (Architecture Decision Record) 작성
   - API Spec (OpenAPI or JSON Schema) 정의

---

### 4.3 Observability 강화

**현재 상태**: 로그만 존재, 실시간 모니터링 부재

**개선 방안**:
1. **Metrics Collection**
   - Prometheus Exporter 추가
   - Metrics:
     - `collector_connection_status{broker="KIS|Kiwoom"}` (gauge)
     - `collector_messages_received_total{broker, symbol}` (counter)
     - `collector_reconnect_total{broker}` (counter)
     - `collector_error_total{broker, error_type}` (counter)

2. **Alerting Rules**
   ```yaml
   # Prometheus Alert
   - alert: CollectorDown
     expr: collector_connection_status == 0
     for: 1m
     labels:
       severity: critical
     annotations:
       summary: "Collector {{ $labels.broker }} is down"
   ```

3. **Dashboard**
   - Grafana 대시보드 구성
   - 실시간 연결 상태 표시
   - 에러율 그래프
   - 메모리/CPU 사용률

---

### 4.4 Data Recovery Automation

**목표**: 장애 발생 시 자동으로 누락 데이터 복구

**메커니즘**:
1. **Gap Detection**
   - TimescaleDB에 1분마다 데이터 존재 여부 체크
   - 연속 5분 이상 데이터 없으면 Gap으로 판정

2. **Auto Recovery Trigger**
   ```python
   # Detect gap
   if gap_detected:
       # Use KIS REST API for historical tick recovery
       await kis_rest.fetch_intraday_ticks(
           symbol=symbol,
           start_time=gap_start,
           end_time=gap_end
       )
   ```

3. **Kiwoom TR Fallback**
   - Kiwoom `opt10079` TR로 missing tick 보완
   - 단, Orderbook은 복구 불가 (실시간 전용)

**제약 사항**:
- ⚠️ **Orderbook 데이터는 복구 불가능** (Historical API 없음)
- ✅ **Tick 데이터는 복구 가능** (당일 종가 이후 복구 가능)

---

## 5. 로드맵 연동 시나리오

이 아이디어가 실현된다면 **Pillar 1: System Reliability & Resilience**에 포함됩니다.

### Roadmap Items 추가 제안

#### Week 3: Emergency Fixes (Current Sprint)
- [ ] Fix Kiwoom Collector ImportError (4h)
- [ ] Fix Recovery Worker dependency (2h)
- [ ] Implement KIS WebSocket heartbeat (4h)
- [ ] Increase Real Collector memory limit (1h)
- [ ] Manual data recovery for 2026-01-19 (8h)

#### Week 4-5: Resilience Enhancement
- [ ] Implement Pre-flight Health Check (16h)
- [ ] Add Prometheus metrics to all collectors (12h)
- [ ] Create Grafana monitoring dashboard (8h)
- [ ] Set up Alerting (Slack/Discord integration) (8h)

#### Week 6-8: Governance & Automation
- [ ] Enforce GitHub Branch Protection (2h)
- [ ] Add CI/CD Pre-merge tests (8h)
- [ ] Implement Auto Gap Detection (12h)
- [ ] Implement Auto Recovery Worker (16h)
- [ ] Write RFC for Unified Collector Architecture (8h)

**Total Estimate**: ~100 hours (2.5 sprints)

---

## 6. Council of Six 초기 의견 (간단히)

### 🎯 Product Manager (Luna)
> "P0 Critical. 고객 신뢰 직결. 장 초반 데이터 손실은 백테스트 품질에 치명타. 긴급 복구 후 재발 방지에 집중해야 함."

### 🏗️ System Architect (Atlas)
> "근본 원인은 Governance 부재. Spec 없이 코드 커밋하면 이런 일 반복됨. Pre-merge test + Branch protection 필수."

### 💻 Backend Engineer (Cipher)
> "`get_redis_connection` 같은 공통 함수는 shared utility로 빼야 함. Dependency Injection Container 패턴 도입 검토 필요."

### 📊 Data Scientist (Nova)
> "Orderbook 손실은 복구 불가능. 이런 데이터 품질 이슈는 모델 성능에 직접 영향. 모니터링으로 조기 탐지 필수."

### 🧪 QA Engineer (Sentinel)
> "Integration Test가 있었다면 방지 가능했음. Docker smoke test만이라도 CI에 추가해야 함."

### 🔒 Security & Ops (Vanguard)
> "OOM Kill은 리소스 모니터링 부재의 증거. Memory/CPU limit + alert 설정 시급. Chaos Engineering 도입 고려."

---

## 7. 다음 단계 (Next Steps)

### Immediate (Today)
1. ✅ Error Analysis 완료
2. 🔄 Fix Kiwoom ImportError → `/create-issue` 발행
3. 🔄 Fix Recovery Worker dependency → `/create-issue` 발행
4. 🔄 Investigate Real Collector OOM

### Short-term (This Week)
5. Implement KIS heartbeat
6. Manual data recovery attempt (당일 종가 후)
7. Add Memory monitoring to all collectors

### Long-term (Next Sprint)
8. `/create-rfc` for Unified Collector Architecture
9. `/create-spec` for Pre-flight Health Check System
10. Update `stock_monitoring_roadmap.md` with Resilience Pillar items

---

## 8. 참고 문서 (References)

- [IDEA-001: Pre-flight System Health Check](file:///Users/bbagsang-u/workspace/stock_monitoring/docs/ideas/stock_monitoring/IDEA-preflight-check.md) (if exists)
- [IDEA-003: Hybrid Topology for Collector Isolation](../../governance/development.md) (from conversation history)
- [Development Governance](file:///Users/bbagsang-u/workspace/stock_monitoring/docs/governance/development.md)
- [Master Roadmap](file:///Users/bbagsang-u/workspace/stock_monitoring/docs/roadmap/stock_monitoring_roadmap.md) (if exists)

---

**마지막 업데이트**: 2026-01-19T02:48:40Z  
**담당자**: AI Agent (Brainstorm Workflow)  
**검토 필요**: Yes (User Review Required)
