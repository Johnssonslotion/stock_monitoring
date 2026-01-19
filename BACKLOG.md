# 📋 Unified Project Backlog

본 백로그는 모든 환경(Oracle Cloud, Local, Mac)에서 공통으로 관리되는 프로젝트의 **단일 진실 공급원(SSoT)**입니다. 

## 1. 진행 중 (In-Progress)
| 태스크 | 담당 페르소나 | 우선순위 | 상태 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1 Week 2: Chaos Test** | QA + Developer | **P0** | [/] | 타임랙, Failover 시뮬레이션 |
| **ISSUE-015: 수집기 외부 모니터링** | Developer | P1 | [/] | [ISSUE-015](./docs/issues/ISSUE-015.md) (Netlify+Northflank) |
| **수집단(Collector) 독립화** | Developer | P1 | [/] | 미래/키움 RE 연동 (독립 모듈화 진행) |
| 실험 레지스트리 구축 | Data Scientist | P1 | [/] | `experiments/` 구조화 |
| **ISSUE-016: 데이터 누락 자동 보완** | Developer | P1 | [/] | [ISSUE-016](./docs/issues/ISSUE-016.md) 키움 TR 복구 |

## 2. 대기 중 (Todo)
| 태스크 | 담당 페르소나 | 우선순위 | 의존성 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **🚨 KIS 중복 구독 에러 해결** | Developer + Infra | **P0** | - | 11,965건/1h, 373220 종목 집중 |
| **ISSUE-014: 가상 거래 시스템 점검** | Architect + Backend | **P1** | - | [IDEA-005](../docs/ideas/stock_backtest/ID-virtual-trading-v2.md) 연동 |
| 미래에셋 OAuth2 연동 | Developer | P1 | - | API 키 대기 중 |
| 키움 RE 화면번호 풀링 | Architect | P1 | - | REST API 사양 기준 |
| 상법개정 앵커 백테스트 | Data Scientist | P2 | 수집단 개편 | 2/26 기준 데이터 |
| Failure Mode 자동 복구 | QA | P2 | 수집단 구현 | Doomsday Check 연동 |

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
2. **Commit with TaskID**: 모든 커밋은 가급적 백로그의 태스크와 연계되도록 기술한다.
3. **Review**: 주 단위 또는 마일스톤 종료 시 PM 페르소나가 백로그의 DoD를 점검한다.
4. **Deferred Work**: RFC 승인 후 구현이 이연된 작업은 [Deferred Work Registry](docs/governance/deferred_work.md)에 별도 관리한다.

