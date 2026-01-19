# IDEA: 통합 데이터 레이크 및 외부 수집기 위임 (Decoupled Data Lake)
**Status**: 💡 Seed (Idea)
**Priority**: P2 (Long-term)

## 1. 개요 (Abstract)
현재 모놀리식으로 구성된 프로젝트에서 수집(Collector)과 저장(Storage)의 책임을 완전히 외부로 위임(Externalize)하여, 백테스트 엔진(Client)는 오직 정제된 데이터만 소비하는 **Data Lake Architecture**로 전환합니다. 이는 AWS/Cloud 전환의 전초 단계가 됩니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: 수집 및 저장소를 로컬 개발 환경에서 물리적으로 분리(별도 서버 또는 VPC)하면, 로컬 PC의 리소스 제약과 네트워크 불안정성에서 완전히 해방될 수 있다.
- **기대 효과**:
    - **Stability**: 백테스트 부하가 수집기에 전혀 영향을 주지 않음.
    - **Scalability**: 수집기 노드를 별도 VPS 등으로 수평 확장 용이.
    - **Security**: API Key가 개발자 로컬 머신에 존재할 필요가 없어짐 (원격 서버에서만 관리).

## 3. 구체화 세션 (Elaboration)
- **Architect (Decoupled Design)**:
    - **Phase 1 (Logical Split)**: 현재 `docker-compose.yml`에서 DB와 Collector를 떼어내어 별도 레포지토리(`stock_data_platform`)로 분리.
    - **Phase 2 (Physical Split)**: 해당 스택을 AWS EC2나 별도 홈 서버(NAS)에 배포.
    - **Interface**: Client(Backtest)는 오직 TimescaleDB 포트(5432)와 Redis 포트(6379)로만 원격 접속.
- **Data Engineer**: 
    - "데이터는 물과 같아서(Lake), 수집하는 곳과 마시는 곳이 분리되어야 맑게 유지됩니다."
    - **Storage**: TimescaleDB를 'Master Data Node'로 승격시키고, 로컬에서는 `read-only` 계정으로 접근 권장.

## 4. 로드맵 연동 시나리오
- **Pillar**: Pillar 1 (Infra Stability) -> Pillar X (Cloud Migration)
- **Target Component**: `docker-compose.yml`, External Database

## 5. 제안하는 다음 단계
1. **Repository Split**: `stock_backtest` (엔진) vs `stock_collector` (수집기) 레포 분리.
2. **External DB Connection**: 로컬 환경설정에서 DB 호스트를 `localhost`가 아닌 외부 IP로 변경하는 테스트 수행.
