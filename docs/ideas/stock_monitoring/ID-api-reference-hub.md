# IDEA: API Documentation Hub (Centralized Reference)
**Status**: 🌿 Sprouting
**Priority**: P2

## 1. 개요 (Abstract)
현재 여러 디렉토리(`docs/specs/`, `docs/infrastructure/` 등)에 산재된 API 명세서들을 하나의 **진입점(Index)**으로 통합하여, 개발자와 운영자가 필요한 명세를 즉시 찾을 수 있도록 **API Reference Hub**를 구축한다. 특히 Kiwoom REST API(`ka10079`)와 같이 새롭게 발굴된 스펙을 표준화하여 관리한다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **Problem**: API 명세가 기능별로 흩어져 있어(`virtual_investment`, `kiwoom-chart`, `backend`), 전체 그림을 파악하거나 특정 TR 코드를 찾기 어렵다.
- **Solution**: `docs/specs/README.md`를 **API Reference Hub**로 격상시키고, 모든 내부/외부 API에 대한 목차와 링크, 프로토콜 요약 정보를 제공한다.
- **Impact**:
    - 온보딩 시간 단축.
    - "성공 구성(Known Good Config)"의 중앙 저장소 역할.
    - REST vs WebSocket 혼용에 따른 오해 감소.

## 3. 구체화 세션 (Elaboration)
- **Structure**:
    - **Internal APIs**: 백엔드 간 통신 (Sentinels, Collectors).
    - **Vendor APIs (External)**:
        - **Kiwoom**:
             - WebSocket (`real_joo`, `real_hoga`)
             - REST (`ka10079` - Tick Chart) **[NEW]**
        - **KIS**:
             - WebSocket (`H0STCNT0`)
             - REST (`FHKST01010300`)
    - **Virtual Trading**: 모의 투자 시스템.

## 4. 로드맵 연동 시나리오
- **Pillar**: Documentation & Governance
- **Action Items**:
    1. `docs/specs/README.md` 생성 및 허브화.
    2. 각 Spec 파일 헤더에 `nav_order` 등 메타데이터 추가 (향후 정적 사이트 생성 대비).
    3. `kiwoom-chart-api.md` 등 최신 스펙 업데이트.
