# IDEA: 데이터 수집 무결성 보장 및 자동 복구 시스템 (Data Collection Resilience \u0026 Self-Healing)

**Status**: 💡 Seed (Idea)  
**Priority**: P0  
**Created**: 2026-01-19T03:50:00Z  
**Category**: Infrastructure / Data Quality / Reliability

---

## 1. 개요 (Abstract)

### 문제 (Problem)
금일(2026-01-19) 발생한 KIS/Kiwoom 수집기 장애에서 드러났듯이, 실시간 데이터 수집 시스템은 장애 발생 시 **인적 개입 없이는 복구가 불가능**하며, 누락된 데이터는 **영구 손실**되어 백테스트 신뢰도를 저하시킵니다.

### 제안 (Proposal)
- **장 시작 전 사전 점검** (Pre-flight Check): API 키, 네트워크, 컨테이너 상태 자동 검증
- **장애 시 즉각 전환** (Circuit Breaker): 실패한 소스를 자동으로 우회하여 데이터 손실 방지
- **장 종료 후 보충** (Gap-Filler): REST API로 누락 구간 자동 복구
- **실시간 감시** (Watchdog): 5분간 데이터 없으면 컨테이너 재시작 또는 알림

---

## 2. 가설 및 기대 효과 (Hypothesis \u0026 Impact)

### 가설
"장 시작 전 사전 점검(Pre-flight) + 장애 발생 시 즉각적인 백업 전환(Circuit Breaker) + 장 종료 후 데이터 누락 검수(Audit) + 자동 보충(Gap-Fill)"이 체계화된다면, **인적 개입 없이도 99.9% 이상의 데이터 무결성**을 유지할 수 있다.

### 기대 효과
- ✅ **백테스트 신뢰도 향상**: 데이터 갭으로 인한 왜곡 방지 → 전략 성능 정확도 개선
- ✅ **운영 부담 감소**: 실시간 모니터링 및 수동 재시작 최소화
- ✅ **다중 브로커 효율성**: KIS + Kiwoom 자원의 최적 배분 (Active-Standby or Sharded Collection)
- ✅ **SLA 달성**: 목표 데이터 가용성 99.9%+ 달성

---

## 3. 구체화 세션 (Elaboration)

### 🏗️ System Architect (Atlas)
\u003e **"Sentinel을 Watchdog으로 강화하라"**
- 단순 메트릭 수집에서 벗어나 **능동적 복구** 역할 부여
- 5분간 데이터 유입 없으면:
  - 컨테이너 재시작 (`docker restart`)
  - 또는 Slack/Discord 알림 발송
- **Circuit Breaker 패턴 도입**:
  - KIS WebSocket 실패 → 즉시 키움 WebSocket 전환
  - 또는 KIS REST API로 폴백
  
**구현 위치**: [`src/monitoring/sentinel.py`](file:///home/ubuntu/workspace/stock_monitoring/src/monitoring/sentinel.py)

---

### 📊 Data Scientist (Nova)
\u003e **"실시간 데이터가 빠져도 장 마감 후 복구하라"**
- **Daily Gap-Filler 워커 필수**:
  - 장 마감 후(15:30) 자동 실행
  - 브로커별 REST API 사용:
    - KIS: 분봉/틱 조회 TR
    - Kiwoom: `opt10079` (주식틱조회)
  - 누락된 시간 구간을 자동으로 특정하여 백필
  
**제약 사항**:
- ⚠️ **Orderbook 데이터는 복구 불가능** (Historical API 없음)
- ✅ **Tick 데이터는 당일 종가 후 복구 가능**

---

### 🧪 QA Engineer (Sentinel)
\u003e **"장 시작 전 Pre-flight Check로 문제를 사전 차단하라"**
- **08:30 자동 실행** (장 시작 30분 전):
  1. API 키 만료 여부 확인
  2. WebSocket 연결 가능 여부 (가상 종목 구독 테스트)
  3. Redis/TimescaleDB 연결 확인
  4. 컨테이너 메모리/CPU 상태 확인
  5. Docker 이미지 의존성 검증 (ImportError 사전 탐지)
  
**알림 메커니즘**:
- 문제 발견 시 **Slack/Discord Webhook 즉시 발송**
- 또는 Email Alert (백업)

**구현 위치**: [`scripts/operations/preflight_check.py`](file:///home/ubuntu/workspace/stock_monitoring/scripts/operations/)

---

## 4. 로드맵 연동 시나리오

### Target Pillar
**Pillar 1: Infrastructure Sustainability \u0026 Data Quality**
**Pillar 1: Infrastructure Sustainability & Data Quality**

### Target Components
1. **Unified Collector** ([`src/data_ingestion/price/unified_collector.py`](file:///home/ubuntu/workspace/stock_monitoring/src/data_ingestion/price/unified_collector.py))
   - Circuit Breaker 로직 추가
   
2. **Sentinel Service** ([`src/monitoring/sentinel.py`](file:///home/ubuntu/workspace/stock_monitoring/src/monitoring/sentinel.py))
   - Watchdog 기능 확장
   
3. **History Loader** ([`src/data_ingestion/history/loader.py`](file:///home/ubuntu/workspace/stock_monitoring/src/data_ingestion/history/loader.py))
   - Gap-Filler 로직 통합

---

## 5. 제안하는 다음 단계

### Phase 1: Emergency Improvements (Week 1-2, ~40h)
1. **ISSUE-020: Pre-flight Health Check 시스템** (16h)
   - Cron: 매일 08:30 실행
   - API 키, 연결성, 리소스 검증
   - Slack 알림 통합
   
2. **ISSUE-021: Sentinel Watchdog 기능** (12h)
   - 5분 Zero-Data 탐지
   - 컨테이너 자동 재시작
   - 알림 발송
   
3. **ISSUE-022: KIS Heartbeat 구현** (4h)
   - WebSocket Ping/Pong 추가
   - Connection stability 개선
   
4. **ISSUE-023: Memory Monitoring \u0026 Auto-scaling** (8h)
   - Prometheus metrics 추가
   - OOM 사전 탐지 및 알림

---

### Phase 2: Data Recovery Automation (Week 3-4, ~44h)
5. **ISSUE-024: Gap Detection \u0026 Auto Gap-Filler** (24h)
   - 장 마감 후(15:40) KIS/Kiwoom REST API로 누락 구간 복구.
   - 실시간 데이터와 백필 데이터의 중복 제거 및 병합 로직.
   
6. **ISSUE-025: Daily Data Auditor \u0026 Quality Report** (12h)
   - DB 적재 틱 수 vs 거래소 통계 데이터 비교 검증.
   - 이상치 및 데이터 갭 최종 리포트 생성.
   - 데일리 데이터셋 '완결성' 승인 프로세스.

7. **ISSUE-026: Multi-source Merge Algorithm** (8h)
   - KIS \u0026 Kiwoom 데이터 비교
   - 최적 틱 선택 로직 (타임스탬프, 가격 일관성 기반)

---

### Phase 3: Resilience Enhancement (Week 5-6, ~32h)
8. **RFC-009: Circuit Breaker Pattern for Collectors** (8h)
   - Hot-Standby 또는 Active-Active 전략 문서화
   
9. **SPEC-010: Unified Monitoring Dashboard** (16h)
   - Grafana 대시보드 구성
   - 실시간 연결 상태, 에러율, 복구 현황 표시
   
10. **ISSUE-027: Chaos Engineering Test Suite** (8h)
    - 컨테이너 강제 종료 시나리오
    - 네트워크 지연 시뮬레이션
    - 자동 복구 검증

---

**총 예상 시간**: ~116 hours (약 3 sprints)

---

## 6. Council of Six 초기 의견

### 🎯 Product Manager (Luna)
\u003e "P0 Critical. 데이터 무결성은 제품 신뢰도의 핵심. Gap-Filler만이라도 이번 주 내로 구현 필수."

### 🏗️ System Architect (Atlas)
\u003e "Circuit Breaker + Watchdog는 Self-Healing의 기본. Sentinel 개선이 최우선."

### 💻 Backend Engineer (Cipher)
\u003e "Gap Detection은 TimescaleDB의 Continuous Aggregate로 효율화 가능. 별도 스캔 프로세스 불필요."

### 📊 Data Scientist (Nova)
\u003e "Orderbook 손실은 치명적. Multi-source Merge로 KIS+Kiwoom 동시 수집하여 한쪽 실패해도 대응 가능하게."

### 🧪 QA Engineer (Sentinel)
\u003e "Pre-flight Check가 있었다면 금일 장애 방지 가능했음. 최우선 구현 대상."

### 🔒 Security \u0026 Ops (Vanguard)
\u003e "Memory/CPU limit + auto-restart는 기본 중 기본. Prometheus + Alertmanager 도입 시급."

---

## 7. 참고 문서 (References)

- [Idea: 2026-01-19 Collection Failure Analysis](file:///home/ubuntu/workspace/stock_monitoring/docs/ideas/stock_monitoring/ID-2026-01-19-collection-failure.md)
- [Kiwoom API Access Diagnosis](file:///home/ubuntu/workspace/stock_monitoring/docs/ideas/stock_monitoring/ID-2026-01-19-kiwoom-access-diagnosis.md)
- [Development Governance](file:///home/ubuntu/workspace/stock_monitoring/docs/governance/development.md)
- [Collector Failure Runbook](file:///home/ubuntu/workspace/stock_monitoring/docs/runbooks/collector-failures.md)

---

**마지막 업데이트**: 2026-01-19T03:50:00Z  
**담당자**: AI Agent  
**검토 필요**: Yes (User Review Required)
