# IDEA: Stateful Self-Healing Worker (SSH-Worker)

**Status**: 🌿 Sprouting (Drafting)
**Priority**: P1
**Category**: Infrastructure / Data / Resilience
**Source**: User / Architect
**Related**: [RFC-008 (Tick Completeness)](../governance/rfc/RFC-008-tick-completeness-qa.md), [RFC-009 (Ground Truth & API Control)](../governance/rfc/RFC-009-ground-truth-api-control.md)

## 1. 개요 (Abstract)

현재 구현 중인 'Startup Hook'은 컨테이너가 뜬 시점에 즉시 작업을 수행하는 기초적인 수준입니다. **SSH-Worker**는 여기서 한 단계 더 나아가, 컨테이너가 꺼져있던 시점(Downtime)을 계산하고, 해당 공백 기간 동안 누락된 데이터나 검증 작업을 **자동으로 오케스트레이션**하여 복구하는 지능형 자가 치유 시스템을 지향합니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)

- **[가설]**: 워커가 자신의 '마지막 활동 시간'과 '현재 재시작 시간'을 비교하여 공백을 인지하고, 이를 기반으로 적응형 복구 전략(Raw Logs -> API Hub)을 즉시 실행한다면, 운영자의 수동 개입 없이도 99.9% 이상의 데이터 완결성을 유지할 수 있을 것이다.
- **[기대 효과]**:
    - 장애 복구 자동화 (수동 backfill 명령 불필요)
    - 장 중 순단 발생 시 데이터 유실 최소화
    - 시스템의 회복탄력성(Resilience) 극대화

## 3. 구체화 세션 (Elaboration)

### 👔 PM
> "장애가 발생해도 '그냥 두면 알아서 고쳐지는 시스템'은 운영 비용 절감에 엄청난 기여를 할 것이다. 비즈니스 가치가 매우 높다."

### 🏛️ Architect
> "Redis에 각 워커별 `last_heartbeat` 또는 `last_active_timestamp`를 저장하는 'State Persistence' 레이어가 필요하다. 재시작 시 이 값을 읽어 공백(Gap)을 계산하는 엔진을 `MarketSchedule`에 통합해야 한다."

### 🔧 Infra
> "Docker의 `restart: always` 정책과 SSH-Worker가 결합되면 진정한 불사조(Phoenix) 아키텍처가 완성된다. 부하 분산을 위한 Jitter 로직은 필수다."

## 4. 로드맵 연동 시나리오

이 아이디어는 로드맵의 **[Pillar 3: Resilient Infrastructure]** 및 **[Pillar 4: Intelligent Recovery]**의 핵심 기술로 포함될 것입니다. 특히 `ISSUE-031`(Hybrid Recovery)을 실시간 운영 레벨로 끌어올리는 역할을 합니다.

## 5. 핵심 메커니즘 (Key Mechanisms)

1. **State Injection**: 워커 종료 또는 주기적 활동 시 Redis에 타임스탬프 기록.
2. **Gap Calculator & RFC-009 Compliance**: 
    - Startup 시 현재 시간과 기록된 타임스탬프 사이의 '시장 거래 시간'만 추출하여 복구 대상 리스트 생성.
    - 모든 복구 요청은 **RFC-009**에 따라 `APIHubClient`를 통해서만 수행되어 Rate Limit을 엄격히 준수.
3. **Tiered Recovery (Adaptive)**: 
    - 1단계: 로컬 JSONL 로그에서 손실 없는 데이터 인출 (Zero Cost).
    - 2단계: 로그 부재 시 API Hub를 통해 **Ground Truth(REST API 분봉)** 데이터 보충.
4. **Self-Diagnosis Gate**: 
    - 컨테이너 시작 시 필수 환경 변수 및 Redis/DB 연결 상태를 즉시 검증 (RFC-009 v4.5 준수).
    - 검증 실패 시 즉시 종료(`Exit 1`)하여 '침묵의 실패(Silent Failure)' 방지.
5. **Predictive Priming**: 장 시작 직전(08:55~) 재시작 시, 즉시 복구 대신 '장 시작 준비(Token & Connection)' 모드로 자동 전환.

## 6. 테스트 전략 (Testing Strategy)

SSH-Worker의 핵심 가치인 '자가 치유'를 검증하기 위해 다음과 같은 다층적 테스트를 수행합니다.

### 6.1. Downtime Emulation (공백 시뮬레이션)
- **방법**: Redis의 `last_active_timestamp`를 과거 시간(예: 30분 전)으로 강제 조작한 후 워커 재시작.
- **검증**: 워커가 재시작 즉시 30분간의 공백을 정확히 계산하고 복구 태스크를 생성하는지 확인.

### 6.2. Market-Aware Filter Test
- **방법**: 장 종료 후(예: 16:00) 또는 주말에 워커를 재시작.
- **검증**: `MarketSchedule`이 현재 시간을 비거래 시간으로 인지하여 불필요한 API 호출이나 복구 시도를 차단하는지 확인.

### 6.3. Tiered Recovery Logic Testing
- **방법**: 로컬 로그 파일이 있는 구간과 없는 구간을 섞어서 공백 발생.
- **검증**: 
    - 로그가 있는 구간: `LogRecoveryManager`가 작동하여 Zero Cost 복구 수행.
    - 로그가 없는 구간: `APIHubClient`를 통해 KIS/Kiwoom 서버에서 데이터 보충.

### 6.4. Jitter & Load Balancing Test
- **방법**: 10개 이상의 워커 컨테이너를 동시에 SIGKILL 후 재시작.
- **검증**: 각 워커가 설정된 Jitter 범위 내에서 시차를 두고 API Hub에 접근하여 순간적인 트래픽 폭증(Thundering Herd Problem)을 방지하는지 확인.

## 7. Council of Six - 페르소나 협의 (RFC 교차 검증 결과 포함)

### 👔 PM (Project Manager)
> "SSH-Worker는 장애 대응의 패러다임을 '수동 복구'에서 '상시 자가 복구'로 바꾸는 혁신적인 아이디어다. **RFC-009**와의 교차 검증을 통해 '참값(Ground Truth)' 기반의 복구 체계가 더욱 명확해졌다. 비즈니스 연속성 측면에서 이보다 강력한 가드는 없을 것이다. 즉시 **🌿 Sprouting** 상태로 격상하여 구현 준비에 착수하라."

### 🏛️ Architect
> "가장 우려했던 부분은 RFC와의 충돌이었으나, 오히려 SSH-Worker가 **RFC-009**의 '중앙 집중식 API 통제'를 실질적으로 실현하는 도구가 될 것임을 확인했다. 'Self-Diagnosis Gate'를 추가한 것은 탁월한 선택이다. 아키텍처적으로 '관측 가능성(Observability)'과 '자가 치유(Self-healing)'가 결합된 완성도 높은 설계다."

### 🔬 Data Scientist
> "데이터 정합성 측면에서 **RFC-008**의 분봉 교차 검증 로직이 SSH-Worker의 Startup Hook에 녹아들어 기쁘다. 이제 장 중 어떤 시점에 장애가 발생해도, 데이터 사이언티스트들은 '깨끗한 데이터'를 보장받을 수 있다. 특히 Tiered Recovery가 Ground Truth 우선순위를 철저히 따르고 있다는 점이 신뢰를 준다."

### 🔧 Infrastructure Engineer
> "인프라 관점에서 RFC-009의 Fail-Fast 원칙이 SSH-Worker에 완벽히 이식되었다. Jitter 로직과 자가 진단 기능이 결합되어 컨테이너 오케스트레이션의 안정성이 한 차원 높아졌다. 리소스 낭비 없는 효율적인 복구 체계(Zero Cost Recovery)가 인상적이다."

### 👨‍💻 Developer
> "개발자로서 RFC의 엄격한 규칙들을 코드로 직접 구현하는 부담이 있었으나, SSH-Worker의 통합된 Startup Hook이 이를 자동화해주어 개발 생산성이 향상될 것으로 기대한다. `MarketSchedule` 유틸리티의 재사용성이 극대화되었으며, 테스트 전략에 RFC 준수 여부를 검증하는 항목이 추가되어 안정적인 배포가 가능해졌다."

### 🧪 QA Engineer
> "QA 관점에서 SSH-Worker는 '검증 불가능한 시나리오'를 없애주는 마법 같은 도구다. RFC-008에서 정의한 품질 메트릭(Coverage, Consistency)을 SSH-Worker가 실시간으로 달성하려 노력하기 때문이다. 이제 우리는 카오스 테스트를 통해 고의로 장애를 내더라도 시스템이 스스로 RFC 기준을 회복하는지 더 공격적으로 검증할 수 있다."

### 📝 Doc Specialist
> "본 문서는 이제 단순한 아이디어를 넘어 **RFC-008/009의 실행 지침서** 역할을 하게 되었다. 'Self-Healing Log Format'에 RFC 준수 태그를 추가하여 운영 보고서가 자동화되도록 지원할 것이다. 문서의 정합성이 완벽하며, 프로젝트의 핵심 자산으로 기록될 준비가 끝났다."

## 8. PM의 최종 결정
> "Council 전원의 만장일치 찬성 및 RFC 교차 검증 완료를 바탕으로, **SSH-Worker** 아이디어를 **🌿 Sprouting** 상태로 공식 격상한다. 이는 시스템의 Resilience를 완성하는 중추적 설계다. 즉시 구현 계획에 반영하고, RFC-009의 Enforcement Rule로 내재화하라."
