# 📋 Unified Project Backlog

본 백로그는 모든 환경(Oracle Cloud, Local, Mac)에서 공통으로 관리되는 프로젝트의 **단일 진실 공급원(SSoT)**입니다.

---

## 1. 진행 중 (In-Progress)

| 태스크 | 담당 페르소나 | 우선순위 | 상태 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **ISSUE-004: 마켓 오픈 실패 수정** | Developer | **P0** | [/] | Kiwoom NameError, KIS Protocol 수정 |
| **ISSUE-012: KIS WebSocket Approval Key 미적용** | Developer | **P0** | [/] | 데이터 수집 완전 중단 (0 ticks) |
| **ISSUE-015: 데이터 누락 자동 보완** | Developer | **P0** | [/] | 1/16~1/19 누락 데이터 복구 & 자동화 |
| **수집단(Collector) 독립화** | Developer | P1 | [/] | kis-service/kiwoom-service 컨테이너 분리 완료 |

---

## 2. 대기 중 (Todo)

### 🔴 P0 (긴급)
| 태스크 | 담당 페르소나 | 의존성 | 비고 |
| :--- | :--- | :--- | :--- |
| **ISSUE-012: KIS WebSocket Approval Key 미적용** | Developer | - | 데이터 수집 완전 중단 (0 ticks) |

### 🟠 P1 (높음)
| 태스크 | 담당 페르소나 | 의존성 | 비고 |
| :--- | :--- | :--- | :--- |
| **ISSUE-003: API Error Handling & Logging** | Developer | - | WebSocket 재연결, 타임아웃 개선 |
| **ISSUE-007: WebSocket 연결 관리자** | Backend | - | Single-Key 정책 대응, 구독 다중화 |
| **ISSUE-008: OrderBook Streaming** | Backend | ISSUE-007 | Delta 기반 호가 스트리밍 |
| **ISSUE-009: Execution Streaming** | Backend | - | Whale 거래 감지 및 플래깅 |
| 미래에셋 OAuth2 연동 | Developer | - | API 키 대기 중 |
| 키움 RE 화면번호 풀링 | Architect | - | REST API 사양 기준 |

### 🟡 P2 (보통)
| 태스크 | 담당 페르소나 | 의존성 | 비고 |
| :--- | :--- | :--- | :--- |
| **ISSUE-005: 캔들 데이터 서비스** | Backend | - | `GET /api/candles` 다중 타임프레임 |
| **ISSUE-006: 시장 섹터 서비스** | Data Engineer | - | 섹터별 성과 집계 배치 작업 |
| 상법개정 앵커 백테스트 | Data Scientist | 수집단 개편 | 2/26 기준 데이터 |
| Failure Mode 자동 복구 | QA | 수집단 구현 | Doomsday Check 연동 |

### 🔵 P3 (낮음)
| 태스크 | 담당 페르소나 | 의존성 | 비고 |
| :--- | :--- | :--- | :--- |
| **ISSUE-010: Correlation Engine** | Quant Developer | - | 자산 상관관계 분석 (Pearson) |
| **ISSUE-011: Whale Alert System** | Backend | ISSUE-009 | Slack/Discord 외부 알림 |

---

## 3. 완료 (Done)

### Phase 1 Week 1 (2026-01-16)
- [x] TimestampManager 유틸리티 구현 (12 tests)
- [x] Collection Strategy YAML 설정 (3-Tier 분류)
- [x] DB 스키마 업데이트 (타임스탬프 계층, 중복 방지)
- [x] Orchestrator Failover 로직 (8 tests)
- [x] **Governance v2: 헌법 개정 및 10대 워크플로우 구축**
- [x] **Git Sync: 거버넌스 및 명세서 문서 저장소 이관**
- [x] **ISSUE-045: CPU 모니터링 수정 & 실시간 WS API (ISSUE-044) 전환**

### 가상 투자 시뮬레이션 (2026-01-19)
- [x] **ISSUE-001: 가상 투자 Backend (REST/WS API, VirtualExchange, DB)**
- [x] **ISSUE-002: 가상 투자 Frontend UI (React Components, Mock/Real Sync)**

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
5. **Deferred Work**: RFC 승인 후 구현이 이연된 작업은 [Deferred Work Registry](docs/governance/deferred_work.md)에 별도 관리한다.

---

## 📌 활성 이슈 현황 (Active Issues)

| 번호 | 제목 | 우선순위 | 상태 | 담당 |
| :--- | :--- | :--- | :--- | :--- |
| [ISSUE-003](docs/issues/ISSUE-003.md) | API Error Handling & Logging | P1 | Open | Developer |
| [ISSUE-004](docs/issues/ISSUE-004.md) | Fix Market Open Failure | P0 | In Progress | Developer |
| [ISSUE-005](docs/issues/ISSUE-005.md) | 캔들 데이터 서비스 | P2 | Open | Backend |
| [ISSUE-006](docs/issues/ISSUE-006.md) | 시장 섹터 서비스 | P2 | Open | Data Engineer |
| [ISSUE-007](docs/issues/ISSUE-007.md) | WebSocket 연결 관리자 | P1 | Open | Backend |
| [ISSUE-008](docs/issues/ISSUE-008.md) | OrderBook Streaming | P1 | Open | Backend |
| [ISSUE-009](docs/issues/ISSUE-009.md) | Execution Streaming | P1 | Open | Backend |
| [ISSUE-010](docs/issues/ISSUE-010.md) | Correlation Engine | P3 | Open | Quant |
| [ISSUE-011](docs/issues/ISSUE-011.md) | Whale Alert System | P3 | Open | Backend |
| [ISSUE-012](docs/issues/ISSUE-012.md) | KIS WebSocket Approval Key | P0 | Open | Developer |
| [ISSUE-015](docs/issues/ISSUE-015.md) | 데이터 누락 자동 보완 | P0 | In Progress | Developer |
