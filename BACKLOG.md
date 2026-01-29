# 📋 Unified Project Backlog

본 백로그는 모든 환경(Oracle Cloud, Local, Mac)에서 공통으로 관리되는 프로젝트의 **단일 진실 공급원(SSoT)**입니다. `docs/issues/` 하위의 개별 이슈 파일(File-based) 상태를 기준으로 동기화됩니다.

---

## 1. 진행 중 (In-Progress)

| 태스크 | 담당 페르소나 | 우선순위 | 상태 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| *(현재 진행 중인 태스크 없음)* | - | - | - | - |
| **HOTFIX-2026-01-29: Verification Worker Crash** | Developer | - | **Resolved** | NameError & TaskType mismatch fixed |

---

## 2. 대기 중 (Todo)

### 🔴 P0 (긴급)
| 태스크 | 담당 페르소나 | 의존성 | 비고 |
| :--- | :--- | :--- | :--- |
| *(현재 P0 태스크 없음)* | - | - | - |

### 🟠 P1 (높음)
| 태스크 | 담당 페르소나 | 의존성 | 비고 |
| :--- | :--- | :--- | :--- |
| **ISSUE-051: Short Selling Collector (Pillar 8)** | Developer | ISSUE-049 | 공매도 수집기 구현 |
| **ISSUE-052: Program Trading Collector (Pillar 8)** | Developer | ISSUE-049 | 프로그램매매 수집기 구현 |
| **ISSUE-002: Virtual Investment Platform - Frontend UI** | Frontend Developer | ISSUE-001 | 화면 구현 대기 |
| **ISSUE-003: API Error Handling & Logging** | Developer | - | WebSocket 재연결, 타임아웃 개선 |
| **ISSUE-008: OrderBook Streaming** | Backend | ISSUE-007 | Delta 기반 호가 스트리밍 |
| **ISSUE-009: Execution Streaming** | Backend | - | Whale 거래 감지 및 플래깅 |
| **ISSUE-013: Virtual Trading Audit** | Architect | - | 가상 거래 시스템 정밀 점검 |
| ~~ISSUE-038: Sentinel & Global Logging Standard~~ | Developer | - | ✅ 완료 |
| **ISSUE-042: Docker Network Isolation Fix** | DevOps | - | Redis 연결 오류 수정 (Stock Prod vs Deploy) |
| **ISSUE-043: RealtimeVerifier OHLCV Upgrade** | Developer | ISSUE-042 | 거래량 검증 → OHLCV 완전 검증 고도화 |
| ~~ISSUE-044: TimescaleDB Tick-to-Candle Automation~~ | Developer | ISSUE-043 | ✅ 완료 (2026-01-28) |
| ~~ISSUE-047: Unified Verification Architecture~~ | Developer | RFC-005 | ✅ 완료 (2026-01-29) |

### 🟡 P2 (보통)
| 태스크 | 담당 페르소나 | 의존성 | 비고 |
| :--- | :--- | :--- | :--- |
| **ISSUE-005: 캔들 데이터 서비스** | Backend | - | `GET /api/candles` 다중 타임프레임 |
| **ISSUE-006: 시장 섹터 서비스** | Data Engineer | - | 섹터별 성과 집계 배치 작업 |
| **ISSUE-034: TimescaleDB Storage Efficiency** | Developer | - | 저장 공간 최적화 |

### 🔵 P3 (낮음)
| 태스크 | 담당 페르소나 | 의존성 | 비고 |
| :--- | :--- | :--- | :--- |
| **ISSUE-010: Correlation Engine** | Quant Developer | - | 자산 상관관계 분석 (Pearson) |
| **ISSUE-011: Whale Alert System** | Backend | ISSUE-009 | Slack/Discord 외부 알림 |

---

## 3. 완료 (Done)

### Latest (2026-01-23)
- [x] **ISSUE-041: API Hub v2 Phase 3-B - Container Unification (P0)** - verification-worker & history-collector 완전 마이그레이션, 직접 API 호출 제거, 중앙화된 Token/Rate Limit 관리, 코드 감소 ~350 lines
- [x] **ISSUE-040: API Hub v2 Phase 2 - Real API Integration (P0)** - TokenManager Redlock, BaseAPIClient 통합, Rate Limiter Ground Truth 준수, BackfillManager Queue 전환, 22 new tests, Gap Analysis PASS
- [x] **ISSUE-037: Unified API Hub v2 - Phase 1 Mock Mode (P0)** - Worker 구현, 29/29 테스트 통과, Docker 배포 검증 완료
- [x] **ISSUE-037-A: BaseAPIClient 설계 문서 (P0)** - Phase 2 선행 작업 1/5 완료 (300+ lines)
- [x] **ISSUE-037-B: API 응답 Fixture 수집 (P0)** - Phase 2 선행 작업 2/5 완료 (KIS + Kiwoom)
- [x] **ISSUE-037-C: Token Manager 설계 (P0)** - Phase 2 선행 작업 3/5 완료 (Redis SSoT)
- [x] **ISSUE-037-D: Rate Limiter 통합 계획 (P0)** - Phase 2 선행 작업 4/5 완료 (Gatekeeper)
- [x] **ISSUE-037-E: Phase 2 테스트 계획 (P0)** - Phase 2 선행 작업 5/5 완료 (Mock-only)
- [x] **ISSUE-039: TickArchiver Redis 연결 불안정 (P1)** - `asyncio.to_thread()` 적용, 블로킹 해제
- [x] **ISSUE-038: Sentinel & Global Logging Standard (P1)** - 이미 적용 확인, development.md 가이드 추가
- [x] **SSoT: Unified Backlog Management System (v2.18)** - `deferred_work.md` 통합 및 거버넌스 개정
- [x] **ISSUE-033: TimescaleArchiver Schema Mismatch (P0)** - 494,505 ticks/1h 검증 완료

### 2026-01-28
- [x] **ISSUE-044: TimescaleDB Tick-to-Candle Automation (P1)** - `market_candles_1m_view` 등 연속 집계 뷰 생성, Flat Strategy 적용, VerificationConsumer 통합 완료. Gap Analysis PASS.

### 2026-01-29
- [x] **ISSUE-044: Completed Verification & Merge** - Verified Continuous Aggregates with `test_continuous_aggregates_backfill`. Gap Analysis & Tests Passed.
- [x] **ISSUE-047: Unified Verification Architecture (RFC-005)** - Verification + Realtime 통합 완료, Redis Queue 기반 비동기 처리, 전 종목(98개) 동적 로딩 및 교차 검증 구현 완료.
- [x] **RFC-006: Automated Deployment Verification** - `verify_deployment_logs.py`를 통한 배포 자동 검증 프로세스 구축 및 `/deploy-production` 워크플로우 통합.
- [x] **HOTFIX-2026-01-29**: `verification-worker` NameError 및 task_type 불일치 긴급 수정 완료.
- [x] **RFC-010: Market Intelligence & Rotation Analysis (Pillar 8)** - 투자자 수급, 공매도, 프로그램매매 분석 아키텍처 설계
- [x] **ISSUE-050: Investor Trends Collector (Pillar 8)** - `FHKST01010900` TR ID 검증 완료, InvestorTrendsCollector 구현

### 2026-01-22
- [x] **RFC-009: Ground Truth & API Control Policy Implementation**
  - ✅ `BackfillManager`: gatekeeper 통합 및 Self-Diagnosis 로직 추가
  - ✅ `impute_final_candles.py`: Ground Truth 우선순위 로직 적용
  - ✅ `docker-compose.yml`: recovery-worker Healthcheck 추가
  - ✅ `smoke_test.sh`: CI Negative Test (Chaos-Env) 시나리오 추가
  - ✅ DB Migration: `006_add_source_type_to_candles.sql` 작성
  - ✅ 거버넌스: Constitution v2.17 (No Review, No Work) 신설
  - ✅ **Redis 물리적 분리**: `redis-gatekeeper` 전용 컨테이너 (Council 2차 결정)
- [x] **수집단(Collector) 독립화 [RFC-007]**
  - ✅ kis-service: KIS API 전용 컨테이너 분리
  - ✅ kiwoom-service: Kiwoom API 전용 컨테이너 분리
  - ✅ Profile 기반 격리 및 리소스 제한 (512M~2G)

### 2026-01-21
- [x] **ISSUE-036: DB 스키마 정합성 복구 및 거버넌스(Law #10) 통합**
- [x] **ISSUE-028: Chart UI Controls Overlap (Stabilization)**
- [x] **ISSUE-035: 장 초반 적재 보장 (Zero-Tolerance Ingestion Guard)**
- [x] **ISSUE-004: Fix Market Open Failure (Kiwoom/KIS Protocol)**
- [x] **ISSUE-021: Critical KIS Auth Failure Remediation**

### 2026-01-19~20 (Hotfix Batch)
- [x] **ISSUE-016: 데이터 파이프라인 테스트 완벽성 강화 및 ZEVS 구축**
- [x] **ISSUE-012: KIS WebSocket Approval Key & Auth Fix (P0)**
- [x] **ISSUE-015: 데이터 누락 자동 보완 (Gap Filler & Backfill)**
- [x] **ISSUE-007: WebSocket 연결 관리자 (Dual/Unified Manager)**
- [x] **ISSUE-017: Implement DuckDBArchiver (Hybrid Architecture)**
- [x] **ISSUE-018: Implement KIS Tick Recovery (Backfill Manager)**
- [x] **ISSUE-019: API E2E Test Environment Fix**
- [x] **ISSUE-020: Dual Data Collection (70 Symbols)**
- [x] **ISSUE-022~030: Hotfix Batch** (타입 변환, 채널 표준화, 볼륨 경로 등)
- [x] **RFC-003 Enhancement: Environment Variable Standardization**

### Phase 1 Week 1 (2026-01-16)
- [x] TimestampManager 유틸리티 구현 (12 tests)
- [x] Collection Strategy YAML 설정 (3-Tier 분류)
- [x] DB 스키마 업데이트 (타임스탬프 계층, 중복 방지)
- [x] Orchestrator Failover 로직 (8 tests)
- [x] **Governance v2: 헌법 개정 및 10대 워크플로우 구축**

### 이전 작업
- [x] 브로커 소켓 제약사항 조사 (`socket_constraints.md`)
- [x] 가변적 워커 아키텍처 설계 (`worker_architecture.md`)
- [x] 지식 베이스(Knowledge Base) 구축 및 영구화 전략 수립

---

## 🛠️ 백로그 관리 원칙

1. **Sync First**: 새로운 피쳐 개발 전후로 본 백로그를 업데이트하여 환경 간 차이를 방지한다.
2. **ISSUE Tracking**: 모든 작업은 가급적 ISSUE 번호와 연계하여 추적성을 확보한다.
3. **Commit with TaskID**: 모든 커밋은 가급적 백로그의 태스크 또는 ISSUE와 연계되도록 기술한다.
4. **Review**: 주 단위 또는 마일스톤 종료 시 PM 페르소나가 백로그의 DoD를 점검한다.
5. **Deferred Work**: RFC 승인은 되었으나 구현이 이연된 작업은 하단의 `## 4. Deferred Work` 섹션에 통합 관리한다.

---

## 📌 활성 이슈 현황 (Active Issues)

> `docs/issues/` 디렉토리 기준. 완료된 이슈는 `docs/ARCHIVE/issues/`로 이동됨.

| 번호 | 제목 | 우선순위 | 상태 | 담당 |
| :--- | :--- | :--- | :--- | :--- |
| [ISSUE-002](docs/issues/ISSUE-002.md) | Virtual Investment Platform - Frontend UI | P1 | Todo | Frontend |
| [ISSUE-003](docs/issues/ISSUE-003.md) | API Error Handling & Logging | P1 | Open | Developer |
| [ISSUE-005](docs/issues/ISSUE-005.md) | 캔들 데이터 서비스 | P2 | Open | Backend |
| [ISSUE-006](docs/issues/ISSUE-006.md) | 시장 섹터 서비스 | P2 | Open | Data Engineer |
| [ISSUE-007](docs/issues/ISSUE-007.md) | WebSocket 연결 관리자 | P1 | Done | Backend |
| [ISSUE-008](docs/issues/ISSUE-008.md) | OrderBook Streaming | P1 | Open | Backend |
| [ISSUE-009](docs/issues/ISSUE-009.md) | Execution Streaming | P1 | Open | Backend |
| [ISSUE-010](docs/issues/ISSUE-010.md) | Correlation Engine | P3 | Open | Quant |
| [ISSUE-011](docs/issues/ISSUE-011.md) | Whale Alert System | P3 | Open | Backend |
| [ISSUE-013](docs/issues/ISSUE-013.md) | Virtual Trading Audit | P1 | Open | Architect |
| [ISSUE-015](docs/issues/ISSUE-015.md) | 데이터 누락 자동 보완 | P1 | Done | Developer |
| [ISSUE-017](docs/issues/ISSUE-017.md) | DuckDBArchiver (Hybrid Architecture) | P1 | Done | Developer |
| [ISSUE-018](docs/issues/ISSUE-018.md) | KIS Tick Recovery (Backfill Manager) | P1 | Done | Developer |
| [ISSUE-021](docs/issues/ISSUE-021.md) | Critical KIS Auth Failure Remediation | P0 | Done | Developer |
| [ISSUE-028](docs/issues/ISSUE-028.md) | Chart UI Controls Overlap | P1 | Done | Frontend |
| [ISSUE-034](docs/issues/ISSUE-034.md) | TimescaleDB Storage Efficiency | P1 | Open | Developer |
| [ISSUE-035](docs/issues/ISSUE-035.md) | 장 초반 적재 보장 | P0 | Done | Developer |
| [ISSUE-036](docs/issues/ISSUE-036.md) | DB 스키마 정합성 복구 | P0 | Done | Developer |
| [ISSUE-038](docs/issues/ISSUE-038.md) | Sentinel & Global Logging Standard | P1 | Done | Developer |
| [ISSUE-039](docs/issues/ISSUE-039.md) | TickArchiver Redis 연결 불안정 | P1 | Done | Developer |
| [ISSUE-040](docs/issues/ISSUE-040.md) | **API Hub v2 Phase 2 - Real API Integration** | **P0** | Done | Developer |
| [ISSUE-041](docs/issues/ISSUE-041.md) | **API Hub v2 Phase 3 - Production & Monitoring** | **P0** | **✅ Phase 3-B Done** | Developer |
| [ISSUE-049](docs/issues/ISSUE-049.md) | **KIS TR ID Discovery (Pillar 8)** | **P0** | **Partial** | Developer |
| [ISSUE-050](docs/issues/ISSUE-050.md) | **Investor Trends Collector (Pillar 8)** | **P1** | **Done** | Developer |
| [ISSUE-051](docs/issues/ISSUE-051.md) | **Short Selling Collector (Pillar 8)** | **P1** | Todo | Developer |
| [ISSUE-052](docs/issues/ISSUE-052.md) | **Program Trading Collector (Pillar 8)** | **P1** | Todo | Developer |

---

## 4. 이연 작업 (Deferred Work)

RFC/ADR 승인은 되었으나 특정 조건 충족 시 착수하기 위해 대기 중인 작업들입니다.

| ID | 태스크 (Task Name) | 우선순위 | 트리거 조건 (Trigger) | 관련 RFC/ISSUE |
| :--- | :--- | :--- | :--- | :--- |
| ~~DEF-API-HUB-001~~ | ~~Unified API Hub v2 (Centralized REST Worker)~~ | ~~P1~~ | ✅ **ACTIVATED** (2026-01-23) → ISSUE-040 | [Spec](docs/specs/api_hub_v2_overview.md) |
| **DEF-003-001** | 전략 파라미터 Config 분리 | **P1** | 사용자 일정 여유 확보 시 | [RFC-003](docs/governance/decisions/RFC-003_config_management_standard.md) |
| **DEF-034-001** | 틱 데이터 공백 복구 (Log + REST Hybrid) | **P1** | 시스템 안정화 후 일괄 복구 필요 시 | [RFC-008](docs/governance/rfc/RFC-008-tick-completeness-qa.md) |
| **DEF-034-002** | TimescaleDB Post-Market 최적화 자동화 | **P2** | 장 마감 후 자동 스케줄링(Cron) 적용 시 | [ISSUE-034](docs/issues/ISSUE-034.md) |

---

*Last Updated: 2026-01-29 (Pillar 8 Market Intelligence - ISSUE-051/052 추가)*
