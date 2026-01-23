# IDEA: REST API 기반 틱 수집 대역 가시화 및 자동 복구 고도화 (v1.0)
**Status**: 🌿 Sprouting
**Priority**: P1

## 1. 개요 (Abstract)
현재 수집 중인 실시간 틱 데이터와 KIS REST API(/inquire-time-itemconclusion)를 통해 조회한 틱 데이터를 비교하여, **수집 대역(Coverage)과 누락 구간을 시각화**하고 이를 기반으로 자동화된 복구 프로세스를 확립한다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: 실시간 웹소켓 수집 대역과 REST API 조회 대역을 1분 단위 Heatmap으로 가시화하면, 특정 시간대나 특정 종목의 수집 취약점을 즉각적으로 파악할 수 있을 것이다.
- **기대 효과**:
    - **가시성 확보**: 데이터가 "잘 들어오고 있다"는 막연한 로그 대신 숫자로 된 수집율(Cover Ratio) 확보.
    - **복구 신뢰도**: 복구 작업 전/후의 데이터 밀도 변화를 시각적으로 확인하여 복구 무결성 검증.
    - **인프라 튜닝**: 빈번한 누락 구간을 분석하여 웹소켓 세션 유지 정책이나 네트워크 설정 최적화.

## 3. 구체화 세션 (Elaboration)

### 3.1. REST API 가시화 방안 (Visualization)
- **Heatmap Grid**: 
    - X축: 시간 (09:00 ~ 15:30, 1분 단위)
    - Y축: 종목 (Top 40 + @)
    - Cell Color: 
        - 🟢 초록: 웹소켓 수집 완료
        - 🟡 노랑: 실시간 누락되었으나 REST API로 보강됨
        - 🔴 빨강: 양쪽 모두 데이터 없음 (조회 불가 구간)
- **API Call Density**: REST API 호출 횟수 대비 복구된 틱 수 비율을 가시화하여 API 효율성 관리.

### 3.2. 자동 복구 완결성 (Complete Automation)
- **Trigger**: 장 마감(14:00 이후 등) 후 또는 매 시 정각에 `RecoveryOrchestrator` 자동 호출.
- **Worker**: 현재 `sleep infinity`인 `recovery-worker`에 실제 주기적 실행 로직 탑재.
- **Feedback Loop**: 복구 완료 후 `Dashboard`에 최종 수집 성공 리포트 자동 생성.

## 4. 로드맵 연동 시나리오
- **Pillar 2: Data Integrity**: 수집 퀄리티 평가(QA) 시스템의 핵심 모듈로 편입.
- **ISSUE-035 (예정)**: `recovery-worker` 활성화 및 가시화 스크립트 개발.

## 5. 페르소나 의견
- **Data (Lia)**: "웹소켓 데이터와 REST 데이터의 단순 건수 비교가 아니라, 타임스탬프 갭을 시각화하는 것이 중요합니다."
- **Infra (Kai)**: "REST API 호출 제한(TPS)을 고려하여 가시화 배치 주기를 설계해야 시스템에 무리가 없습니다."
