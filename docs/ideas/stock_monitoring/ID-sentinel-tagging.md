# IDEA: Sentinel Event Tagging & Metadata Injection
**Status**: 💡 Seed (Idea)
**Priority**: P1

## 1. 개요 (Abstract)
- **문제**: 현재 시스템 메트릭(CPU, RAM, Lag 등)은 숫자 위주로 수집되어, 특정 시점에 "무슨 일이 있었는지" (예: 장 개장, 서버 재시작, 파이프라인 수동 개입)에 대한 맥락(Context)을 파악하기 어려움.
- **기회**: 운영상의 주요 지점(Event)을 '태그' 형태로 메트릭 스트림에 주입하면, Grafana 대시보드에서 Annotation으로 활용하거나 이상 탐지 시 원인 분석(Causality Analysis)을 비약적으로 가속화할 수 있음.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: "숫자 메트릭 + 의미적 태그(Semantic Tags)"가 결합되면 운영 장애 발생 시 원인 파악 시간(MTTR)을 50% 이상 단축할 수 있다.
- **기대 효과**:
    - 장 개장/종료 등 정기적 이벤트의 노이즈 제거.
    - `hotfix` 배포 또는 `docker prune` 같은 수동 작업의 영향도 가시화.
    - AI 에이전트가 과거 로그를 분석할 때 '맥락' 있는 데이터 제공.

## 3. 구체화 세션 (Elaboration)
- **PM**: "사후 보고서 작성 시 '이때 왜 튀었죠?'라는 질문에 즉답할 수 있는 근거가 됩니다."
- **Architect**: "`SystemMetrics` 스키마에 `event_type` 필드를 추가하거나, 별도의 `SystemEvent` 채널을 구축하여 Redis Pub/Sub으로 공유하는 아키텍처가 적합합니다."
- **Infra**: "빌드 번호나 컨테이너 ID를 태그에 포함하면 추적성이 훨씬 좋아질 것입니다."

## 4. 로드맵 연동 시나리오
- **Pillar**: Monitoring & Resilience Expansion
- **Action**: `sentinel-agent` 내에 `/tag` API 또는 Redis Control 명령어를 통한 수동/자동 태그 주입 기능 구현.

## 5. 단계별 추진 계획
1. **[PoC]**: Redis에 `system:tags` 채널 생성 및 약식 수동 주입 테스트.
2. **[Integration]**: `TimescaleArchiver`가 태그 정보를 별도의 `system_events` 테이블에 저장하도록 확장.
3. **[Auto-Tagging]**: 장 개장/종료, 서비스 재시작 시 Sentinel이 자동으로 태그를 발행하도록 구현.
