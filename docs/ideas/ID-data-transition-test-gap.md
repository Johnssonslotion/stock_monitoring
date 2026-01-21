# IDEA: Data Transition Test Completeness Re-evaluation
**Status**: 🌿 Sprouting (Drafting)
**Priority**: P0
**Source**: User / Antigravity
**Category**: Data / Strategy

## 1. 개요 (Abstract)
현재의 데이터 파이프라인(KIS/Kiwoom → Collector → Redis → Archiver → DB) 상에서 데이터가 한 단계에서 다음 단계로 전이될 때 발생하는 **유실(Loss)**, **왜곡(Corruption)**, **지연(Latency)** 시나리오에 대한 테스트 케이스가 누락되어 있습니다. 특히 Zero Cost 환경의 불안정성을 고려할 때, 데이터 전이의 안정성은 시스템 신뢰도의 핵심입니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: 각 전이 지점에 Chaos/Edge Case 테스트를 강제하면, 전체 파이프라인의 데이터 유실률을 0.01% 이하로 유지할 수 있다.
- **기대 효과**:
  - 인메모리 배치 유실(최대 99건) 위험 제거.
  - 네트워크 지터 및 API 특이 사항에 대한 회복력 확보.
  - 발행 건수와 저장 건수의 1:1 검증을 통한 Deep Verification 달성.

## 3. 구체화 세션 (Elaboration - Council Opinions)

### 👔 PM
> "배포 연기의 결정적 근거였던 데이터 유실 시나리오가 드디어 구체화되었습니다. 특히 '비즈니스 데이터 무결성'은 우리 로드맵의 최상위 가치입니다. 전이 지점별 테스트 케이스를 Phase 1 핵심 게이트로 설정해야 합니다."

### 🏛️ Architect
> "인메모리 배치의 휘발성은 설계적 결함입니다. 전이 지점 테스트는 단순히 코드를 검증하는 것이 아니라, 설계가 'Durable'한지 증명하는 과정이어야 합니다. Redis Durable Queue로의 마이그레이션이 테스트 결과에 따라 앞당겨질 수 있습니다."

### 🔬 Data Scientist
> "Deep Verification의 핵심은 '전이 결과의 일치'입니다. 발행(Redis)과 저장(DB) 사이의 Delta를 실시간으로 측정하는 테스트가 구현된다면, 데이터 신뢰도가 비약적으로 상승할 것입니다."

### 🔧 Infra Engineer
> "Redis Persistence(AOF/Snapshot) 설정 누락은 전이 단계의 가장 큰 보안 구멍입니다. 컨테이너 재시작 시의 전이 상태 보존(State Persistence) 테스트가 반드시 포함되어야 합니다."

### 👨‍💻 Developer
> "Exception Handling 로직의 Silent Failure가 무섭습니다. 전이 실패 시 Sentinel Alert 발송 및 Fallback(Disk 저장) 로직을 테스트 케이스로 강제하여 방어적 프로그래밍을 완성하겠습니다."

### 🧪 QA Engineer
> "Manual Verification으로 남겨진 11개 항목 중 전이와 관련된 '구독 확인', '연결 대기' 등의 자동화가 시급합니다. Chaos Monkey 수준의 전이 중단 테스트를 CI에 이식하겠습니다."

## 4. 데이터 전이 지점별 상세 테스트 시나리오 (Gap Analysis)

| 전이 구간 | 테스트 케이스 (Edge/Chaos) | 기대 결과 |
| :--- | :--- | :--- |
| **API → Collector** | Fragmented WebSocket Frame 수신 실패 테스트 | 부분 메시지 조합 및 정상 파싱 |
| **Collector → Redis** | Unbounded Queue 메모리 임계값 도달 테스트 | Backpressure 작동 및 메모리 안정 유지 |
| **Redis → Archiver** | Redis 재시작 시 미처리 메시지 복구 테스트 | Persistence 설정을 통한 데이터 보존 확인 |
| **Archiver → Batch** | **[P0]** Batch 99건 상태에서 SIGTERM 수신 테스트 | 종료 전 강제 Flush 및 유실 0건 |
| **Batch → DB** | DB 타임아웃/연결 끊김 발생 시 Fallback 테스트 | 로컬 디스크(failed_batches/) 저장 확인 |

## 5. 로드맵 연동 시나리오
- 이 아이디어는 `master_roadmap.md`의 **Pillar 1: Robust Data Pipeline**에 직결됩니다.
- Sprint 1의 'P0: Data Loss Prevention' 작업의 근거 문서로 활용됩니다.
