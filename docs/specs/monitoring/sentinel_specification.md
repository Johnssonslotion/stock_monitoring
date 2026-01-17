# Sentinel Specification (Monitoring & Failover)

## 1. 개요 (Overview)
Sentinel은 시스템의 무결성, 리소스 가용성, 그리고 시장 데이터 흐름을 실시간으로 감시하는 수호자(Sentinel) 컴포넌트입니다. 
장애 발생 시 자동으로 복구 모드를 가동하거나 관리자에게 경보를 발송하는 핵심 기능을 수행합니다.

## 2. 주요 모니터링 컴포넌트
### 2.1 리소스 모니터링 (Resource Monitor)
- **대상**: 호스트 CPU, Memory, Disk 및 실행 중인 Docker 컨테이너 상태.
- **주기**: 5초 (기본값, `sentinel_config.yaml`에서 설정 가능).
- **형식**: `system.metrics` 채널에 JSON 형식으로 Publish.
- **임계값**: CPU > 80%, Memory > 85% 시 경고(WARNING) 발생.

### 2.2 시장 데이터 하트비트 (Market Data Heartbeat)
- **대상**: KR/US 시장별 Ticker 및 주문서(Orderbook) 수신 간격.
- **동작**: 
  - 각 시장의 운영 시간(KST 기준)을 인지하여 동작.
  - 60초 이상 데이터가 수신되지 않을 경우 **Doomsday Protocol** 가동.

### 2.3 거버넌스 준수 감시 (Governance Monitor)
- **내용**: 시스템 구성 요소의 거버넌스 준수 점검 (인간의 감사 결과 연동).
- **주기**: 5분.

## 3. Doomsday Protocol (자가 복구 로직)
장애 탐지 시 단계적으로 복구를 시도합니다.

| 단계 | 트리거 조건 | 조치 내용 |
| :--- | :--- | :--- |
| **Level 1** | 60초간 데이터 정지 | Suicide Packet 발행으로 서비스 강제 재시작 유도 |
| **Level 2** | Level 1 시도 후 5분 내 재발 | Dual Socket 모드 해제 및 단일 소켓 모드로 전환 (Stability Priority) |
| **Circuit Breaker** | 1시간 내 재시작 횟수 초과 | 모든 자동 복구 중단 및 시스템 HALT (관리자 개입 대기) |

## 4. 인터페이스 (Interfaces)
- **Pub/Sub (Outbound)**:
  - `system.metrics`: 실시간 리소스 및 거버넌스 데이터.
  - `system_alerts`: 이상 징후 및 자동 복구 시도 로그.
  - `system:control`: 재시작 등의 시스템 제어 명령.
- **Pub/Sub (Inbound)**:
  - `ticker.*`: 시장 데이터 유입 확인용.
  - `market_orderbook`: 주문서 유입 확인용.

## 5. 설정 (Configuration)
`configs/sentinel_config.yaml`을 통해 다음 항목을 조정할 수 있습니다:
- 리소스 경고 임계값.
- Doomsday 가동 조건 (Silence Threshold).
- 써킷 브레이커 제한 횟수 (Max Restarts).
