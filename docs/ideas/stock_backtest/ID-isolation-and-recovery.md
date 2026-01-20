# IDEA: 수집기 격리 및 완전 데이터 복구 전략 (Isolation & Recovery)
**Status**: 💡 Seed (Idea)
**Priority**: P1

## 1. 개요 (Abstract)
현재 단일 컨테이너(`real-collector`)에서 구동되는 KIS, Kiwoom, US 수집기를 물리적으로 격리하여 한 브로커의 장애가 전체 시스템에 전파되는 것을 차단합니다. 또한, KIS REST API의 틱 조회 제한(최근 30건)을 극복하고 장 마감 후 데이터를 온전히 복구하기 위한 현실적인 대안을 제시합니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설 1 (Isolation)**: 브로커별로 독립된 Docker 컨테이너(`kis-collector`, `kiwoom-collector`)를 운용하면, 프로세스 크래시나 메모리 누수 발생 시 영향 범위를 해당 컨테이너로 국한시킬 수 있다.
- **가설 2 (Hybrid Topology)**: 데이터 특성에 따라 수집 전략을 이원화한다.
    - **Orderbook (호가)**: 사후 복구가 불가능하므로, KIS와 Kiwoom이 **동일한 종목을 중복 구독(Active-Active)**하여 실시간 가용성을 100% 보장한다.
    - **Tick (체결)**: 사후 복구(Kiwoom API)가 가능하므로, **부하 분산(Sharding)**을 위해 종목을 나누어 수집하거나, 메인 브로커(KIS)에 집중하고 키움은 복구용으로만 대기시킨다.

## 3. 구체화 세션 (Elaboration)
- **Architect (Hybrid Topology Design)**: 
    - **Orderbook Layer (Safety First)**: 
        - Strategy: **Full Replication (Active-Active)**
        - 설명: KIS와 Kiwoom 컨테이너가 **"모든 타겟 종목"**의 호가를 동시에 구독.
        - 목적: 한 쪽이 죽어도 호가 스냅샷 흐름이 끊기지 않도록 함 (호가는 복구 불가하므로).
    - **Tick Layer (Efficiency & Recovery)**:
        - Strategy: **Partitioned (Sharding) + Recovery Fallback**
        - 설명: 실시간 체결은 **KIS(메인)와 Kiwoom(서브)에 종목을 분배(Sharding)**하여 소켓 부하를 줄임.
        - 안전장치: 틱 누락 발생 시, 장 마감 후 **Kiwoom `opt10079`**로 전수 복구.
    - **Container Architecture**:
        - `kis-service`: All Orderbooks + Ticks (Group A)
        - `kiwoom-service`: All Orderbooks + Ticks (Group B)
- **Data Scientist (High-Fidelity Mandate)**: 
    - **"Tick Recovery is Possible, Orderbook is Not"**: 
        - **Tick**: 키움 `opt10079`를 반복 호출(PrevNext=2)하여 장 마감 후 전수 다운로드 수행. (대량 거래 종목의 경우 수분이 소요될 수 있으나 무결성 확보 가능)
        - **Orderbook**: API 제공 기능이 없으므로, KIS와 키움 소켓을 동시에 띄워놓고 **"먼저 들어오는 쪽의 데이터를 저장"**하는 Active-Active 이중화 전략만이 유일한 해결책임.

## 4. 로드맵 연동 시나리오
- **Pillar**: Pillar 1 (Infra Stability) & Pillar 2 (Data Ingestion)
- **Target Component**: `docker-compose.yml`, `unified_collector.py` -> `kis_collector.py`, `kiwoom_collector.py`

## 5. 제안하는 다음 단계
1. **Collector Splitting (ISSUE-019)**: `unified_collector.py`를 브로커별 독립 프로세스로 분리.
2. **Recovery Strategy Decision**: '틱 복구'를 포기하고 '분봉 보완'으로 선회할지, 키움 전수 조회를 감행할지 의사결정 필요.
