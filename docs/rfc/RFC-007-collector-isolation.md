# RFC-007: Collector Isolation & Hybrid Data Topology
**Status**: 🏗️ Draft (Proposed)
**Date**: 2026-01-19
**Author**: Assistant
**Issues**: IDEA-003

## 1. 개요 (Summary)
단일 컨테이너(`real-collector`)에 집중된 수집 부하를 브로커별(KIS, Kiwoom)로 물리적으로 격리(Isolation)하고, 데이터 특성에 맞춘 이원화된 수집 토폴로지(Topology)를 적용하여 시스템의 안정성과 데이터 무결성을 보장합니다.

## 2. 배경 (Motivation)
- **Single Point of Failure**: 현재 KIS나 키움 중 하나만 연결이 끊겨도 수집기 전체를 재시작해야 함.
- **Resource Contention**: 단일 파이썬 프로세스 내에서 다중 소켓 처리 시 GIL(Global Interpreter Lock) 및 메모리 누수 위험 증가.
- **Data Integrity**: 호가(Orderbook)는 사후 복구가 불가능하므로 장중 무중단 수집이 필수적임.

## 3. 아키텍처 (Architecture)

### 3.1. Container Isolation (Cell-Based)
`docker-compose.yml`에서 수집 서비스를 브로커 단위로 분리합니다.

| Service Name | Source | Role | Channel Prefix |
|:---:|:---:|:---:|:---:|
| `kis-service` | KIS WebSocket | **Main Orderbook & Ticks** | `ticker.kr.kis`, `orderbook.kr.kis` |
| `kiwoom-service` | Kiwoom Open API | **Redundant Orderbook** & **Sharded Ticks** | `ticker.kr.kiwoom`, `orderbook.kr.kiwoom` |
| `us-service` | KIS US WebSocket | **US Market Data** | `ticker.us`, `orderbook.us` |

### 3.2. Hybrid Data Topology

#### A. Orderbook (호가): Active-Active (Redundancy) 🛡️
호가 데이터는 사후 복구가 불가능하므로, **"중복이 발생하더라도 유실은 없어야 한다"**는 원칙을 따릅니다.
- **Strategy**: KIS와 Kiwoom이 **동일한 핵심 종목(Universe)**을 동시에 구독.
- **Flow**:
  1. `kis-service` -> Redis `orderbook.kr.kis`
  2. `kiwoom-service` -> Redis `orderbook.kr.kiwoom`
- **Consumption**:
  - **Archiver**: 두 채널 모두 구독하여 DB에 중복 저장 (Source 컬럼으로 구분). 추후 분석 시 교차 검증 가능.
  - **Live UI**: 클라이언트가 선택적으로 구독하거나, 백엔드가 `Merged Stream`을 제공.

#### B. Tick (체결): Sharding + Recovery (Efficiency) ⚡
틱 데이터는 양이 방대하므로 실시간 부하 분산을 우선하고, 누락분은 장 마감 후 복구합니다.
- **Strategy**: 전체 종목 유니버스를 그룹핑하여 분담 수집.
  - **Group A (High Vol)**: KIS 전담
  - **Group B (Low Vol)**: Kiwoom 전담(가능 시) 또는 KIS 단독 수행
- **Failover**:
  - KIS 장애 발생 시 -> Kiwoom으로 즉시 구독 전환 (Manual/Auto).
- **Recovery (Gap-Filling)**:
  - 장 마감 후 `GapFinder`가 시계열 누락을 감지.
  - 누락 구간에 대해 **Kiwoom `opt10079` (주식체결)** API를 호출하여 정밀 복구.

## 4. 구현 계획 (Implementation)

### 4.1. Config Restructuring
종목 설정(`symbols.yaml`)을 브로커별로 분할하거나, 태그(`source: kis/kiwoom`)를 지원하도록 확장.

### 4.2. Code Refactoring
- **Existing**: `unified_collector.py` (Monolithic)
- **New**:
  - `src/data_ingestion/instances/kis_main.py`
  - `src/data_ingestion/instances/kiwoom_sub.py`

### 4.3. Deployment Safety (Operations) 🛑
배포 사고 방지를 위한 2단계 안전장치를 적용합니다.

1.  **Time Lock (Pre-flight)**:
    - `scripts/preflight_check.sh`에서 `MarketAwareGuard`를 호출.
    - 장중(KR/US Market Open)에는 배포 스크립트가 강제 종료됨 (`exit 1`).
2.  **Process Lock (CD Trigger)**:
    - `cd-deploy.yml`의 트리거를 `push`에서 `workflow_dispatch` (수동)로 변경.
    - 우발적인 코드 푸시가 배포로 이어지는 것을 원천 차단.

## 5. 기대 효과
- **Fault Tolerance**: 키움이 죽어도 KIS는 살아있고, KIS가 죽어도 호가는 키움이 살린다.
- **Perfect History**: 틱 데이터의 장중 누락을 키움 API로 100% 메울 수 있다.
