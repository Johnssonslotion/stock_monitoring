# IDEA: 중앙 집중식 데이터 허브 및 분산 수집 에지 (Centralized Data Hub & Edge Collectors)
**Status**: 🌿 Sprouting (Drafting)
**Priority**: P1 (Infrastructure Architecture)

## 1. 개요 (Abstract)
하드웨어 사양이 가장 좋은 **오라클 클라우드(OCI) A1** 인스턴스를 **중앙 데이터 허브(Centralized Data Hub)**로 설정하여 데이터베이스(TimescaleDB)와 메인 엔진을 상주시키고, **구글 클라우드(GCP)** 및 **Northflank** 등의 외부 무료 자원을 **수집 에지(Edge Collectors)**로 활용하여 데이터를 인입시키는 **Hub-and-Spoke** 아키텍처로 전환합니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: 데이터베이스와 분석 엔진을 고사양 노드(OCI A1)에 집중시키고, 지리적으로 분산된 경량 노드들에서 수집 업무만 수행하게 하면 데이터 관리의 단순함과 시스템 고가용성을 동시에 달성할 수 있다.
- **기대 효과**:
    - **Performance Optimization**: OCI A1의 24GB RAM을 데이터베이스 캐싱 및 병렬 백테스트에 온전히 활용.
    - **Simplified Data Management**: 여러 노드에 흩어진 데이터를 동기화할 필요 없이 하나의 중앙 DB에 실시간 적재.
    - **Fault Tolerance**: 특정 수집 노드(GCP, Northflank)가 다운되어도 중앙 허브와 다른 수집 노드들은 영향을 받지 않음.
    - **Zero Cost Compliance**: 모든 구성 요소를 각 벤더의 상시 무료 티어 내에서 운용하여 비용 '0'원 유지.

## 3. 구체화 세션 (Council of Six Deliberation)

> ### 👔 PM (Project Manager)
> "전략의 수익률보다 중요한 것이 데이터의 무결성입니다. 수집기를 지금 즉시 넘기는 것은 'Zero Cost' 측면에서 매력적이나, 만약 원격지 전송 중 데이터 유실이 발생한다면 우리 프로젝트의 근간이 흔들립니다. 따라서 '속도'보다는 '검증'에 무게를 둔 단계적 이전을 지지합니다."

> ### 🏛️ Architect
> "이전 시점은 '명세와 검증'이 끝난 직후여야 합니다. 원격 DB로의 Direct Write는 네트워크 지연과 커넥션 풀 관리가 로컬과 완전히 다릅니다. 먼저 로컬에서 원격 DB로 쏘는 테스트를 통해 지연 시간(Latency)을 측정하고, 수용 가능한 범위 내일 때만 다음 단계로 넘어가야 합니다."

> ### 🔬 Data Scientist
> "데이터 연속성이 끊기는 것은 연구자에게 재앙입니다. 이전 과정 중에도 데이터 수집은 계속되어야 합니다. 로컬 수집기와 외부 수집기를 동시에 가동하는 '듀얼 수집' 기간을 최소 일주일은 가져가서, 두 경로로 들어오는 데이터가 100% 일치하는지 확인해야 합니다."

> ### 🔧 Infrastructure Engineer
> "네트워크 대역폭(Bandwidth)은 큰 걱정 마십시오. 100개 종목의 틱과 10호가 데이터를 다 합쳐도 초당 수 Mbps 수준이며, 이는 Tailscale(WireGuard) 전용망에서 가뿐히 소화합니다. 진짜 복병은 '패킷 유실'입니다. 수집 노드(에지)에서 짧은 시간의 데이터를 버퍼링할 수 있는 'Circuit Breaker' 모듈을 강화하여, 네트워크 불안정 시에도 중앙 DB로의 전송을 보장하겠습니다."

> ### 👨‍💻 Developer
> "헌법 제2.2조(KIS 단일 소켓 유지)가 가장 중요한 제약 사항입니다. 동일 계정으로 로컬과 클라우드에서 중복 접속하면 기존 세션이 끊깁니다. 따라서 2단계(Dual Collection)에서는 KIS는 클라우드에서, Kiwoom은 로컬에서 수집하여 'Cross-Broker Parity Check'를 수행하는 방식으로 소켓 충돌 리스크를 원천 차단하겠습니다."

> ### 🧪 QA Engineer
> "테스트 없는 이전은 없습니다. 'Local -> Staging(로컬에서 원격DB 접속) -> Cloud'의 3단계 프로세스를 제안합니다. 특히 소켓 트래픽이 몰리는 개장 직후(09:00, 22:30 KST)에 원격 DB의 CPU I/O Wait이 임계치를 넘지 않는지 'Stress Test'를 선행하겠습니다."

## 4. 기술 분석: 가상 메쉬 네트워크 (Tailnet as Private VPC)
- **개념**: Tailscale을 사용하여 물리적으로 분리된 로컬, OCI, GCP, Northflank 노드들을 하나의 거대한 **가상 사설망(Tailnet)**으로 묶습니다. 이는 단일 클라우드 벤더의 VPC와 유사한 역할을 수행하지만, 여러 벤더와 로컬을 아우르는 **Global Mesh VPC**의 성격을 띱니다.
- **보안성**: 모든 노드는 공인 IP를 통한 노출 없이 Tailscale이 부여한 내부 IP(100.x.y.z)로만 통신합니다. 중앙 DB(A1)의 포트는 외부 인터넷이 아닌 오직 Tailgrid 내부망에만 개방됩니다.
- **연결성**: 수집 노드(Edge)에서 데이터베이스(Hub)로 접속할 때, 로컬 호스트에 접속하는 것과 동일한 방식으로 사설 IP를 사용합니다. NAT Traversal 기능을 통해 복잡한 방화벽 설정 없이도 서버 간 P2P 직접 연결(WireGuard)을 확립합니다.

## 5. 제안하는 단계적 이전 전략 (Phased Migration Strategy)
1. **Phase 1: Local-to-Remote Staging**  
   - 수집기는 로컬에서 구동하되, DB 연결만 OCI A1로 설정.  
   - 네트워크 레이턴시 및 원격 트랜잭션 안정성 검증.
2. **Phase 2: Dual Collection & Parity Check**  
   - 외부(GCP/Northflank)에 수집기를 배포하되, 로컬 수집기도 병행 가동.  
   - 두 경로의 데이터 정합성을 일 단위로 비교 및 검증.
3. **Phase 3: Full Cutover**  
   - 데이터 정합성이 99.9% 이상 확인되면 로컬 수집기 가동 중단.  
   - 외부 수집기 체제로 전면 전환 및 모니터링 강화.

## 4. 로드맵 연동 시나리오
- **Pillar**: Pillar 1 (Infrastructure Stability) & Pillar 2 (Data Ingestion)
- **Target Component**: `deploy/oci/`, `docker-compose.cloud.yml`, `src/core/config.py`

## 5. 제안하는 다음 단계 (Next Steps)
1. **Infrastructure Audit**: OCI 프리티어 계정 리소스 확인 및 Tailscale 노드 추가.
2. **Setup Script**: OCI ARM 및 Northflank(Docker) 환경을 위한 배포 스크립트 작성.
3. **Data Migration Plan**: 기존 로컬 DB 데이터를 OCI로 안전하게 이전하는 절차 수립.
4. **Latency Test**: 로컬 엔진에서 원격 OCI/CaaS 노드 간의 지연 시간 측정 및 최적화.

## 부록: Northflank Developer Sandbox 주요 스펙 (2026 기준)
- **Compute**: **Always-on** (24/7 상시 구동, Sleep 없음)
- **Services**: 최대 2개의 서비스 + 2개의 Cron Job + 1개의 Add-on(Database)
- **Requests**: 월 1,000,000건의 HTTP 요청 무료
- **Observability**: 월 10GB의 로그 및 10GB의 메트릭 저장소 제공
- **Network**: 초과 전송 시 GB당 $0.06 (매우 저렴한 수준)
- **특징**: 신용카드 인증이 필요하지만 상시 무료로 컨테이너 구동 가능

## 부록: 이전을 위한 베스트 프랙티스 (Strategic Migration Matrix)

어떤 서비스를 어디로 보낼지, 그리고 어떻게 구성할지에 대한 최적의 조합을 다음과 같이 제안합니다.

### 1. 서비스별 배치 전략 (Placement Matrix)
| 서비스 구분 | 추천 환경 | 이유 |
| :--- | :--- | :--- |
| **중앙 데이터베이스 (TimescaleDB)** | **OCI A1** | 24GB의 압도적인 RAM으로 시계열 데이터 캐싱 및 고속 쿼리 가능 |
| **핵심 수집기 (KIS, Kiwoom)** | **Northflank** | **Always-on** 보장 및 컨테이너 전용 환경으로 리소스 관리 효율성 극대화 |
| **경량 수집기 (News, Sentinel)** | **GCP e2-micro** | 인스턴스 안정성이 매우 높으며, 저사양 작업에 적합한 'Forever Free' |
| **백테스트 엔진/분석** | **OCI A1** | DB와 물리적으로 같은 노드에 위치시켜 데이터 전송 오버헤드 최소화 |

### 2. 기술적 운영 수칙 (How to Migrate)
- **Stateless Edge**: 모든 수집기(Collector)는 상태가 없는 **Disposable** 형태로 설계합니다. 컨테이너가 복구되어도 데이터 누락 없이 즉시 수집을 재개할 수 있어야 합니다.
- **Centralized Sink**: 모든 로그와 수집 데이터는 중앙(OCI A1)으로 즉시 스트리밍합니다. 에지 노드에는 데이터를 장기 보관하지 않습니다.
- **Tailnet Isolation**: 공인 IP 대신 오직 Tailscale 사설 IP(100.x.x.x)로만 통신하여 벤더 간 VPC 수준의 보안을 유지합니다.
- **Circuit Breaker**: 원격 DB와의 연결이 순간적으로 끊길 때를 대비하여, 수집 노드 메모리에 최소 1분 분량의 데이터를 버퍼링하는 로직을 필수 적용합니다.
