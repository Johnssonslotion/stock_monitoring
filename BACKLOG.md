# 📋 Unified Project Backlog

본 백로그는 모든 환경(Oracle Cloud, Local, Mac)에서 공통으로 관리되는 프로젝트의 **단일 진실 공급원(SSoT)**입니다. 

## 1. 진행 중 (In-Progress)
| 태스크 | 담당 페르소나 | 우선순위 | 상태 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1 Week 2: Chaos Test** | QA + Developer | **P0** | [/] | 타임랙, Failover 시뮬레이션 |
| 수집단(Collector) 개편 | Developer | P1 | [/] | 미래/키움 RE 연동 |
| 실험 레지스트리 구축 | Data Scientist | P1 | [/] | `experiments/` 구조화 |
| 거버넌스 문서 Git 동기화 | PM | P1 | [/] | 브레인 -> 저장소 이관 |

## 2. 대기 중 (Todo)
| 태스크 | 담당 페르소나 | 우선순위 | 의존성 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **🚨 KIS 중복 구독 에러 해결** | Developer + Infra | **P0** | - | 11,965건/1h, 373220 종목 집중 |
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

### 이전 작업
- [x] 브로커 소켓 제약사항 조사 (`socket_constraints.md`)
- [x] 가변적 워커 아키텍처 설계 (`worker_architecture.md`)
- [x] 지식 베이스(Knowledge Base) 구축 및 영구화 전략 수립

---

## 🛠️ 백로그 관리 원칙
1. **Sync First**: 새로운 피쳐 개발 전후로 본 백로그를 업데이트하여 환경 간 차이를 방지한다.
2. **Commit with TaskID**: 모든 커밋은 가급적 백로그의 태스크와 연계되도록 기술한다.
3. **Review**: 주 단위 또는 마일스톤 종료 시 PM 페르소나가 백로그의 DoD를 점검한다.
