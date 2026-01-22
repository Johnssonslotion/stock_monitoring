# Backend Unit Test Strategy: Kiwoom & KIS Socket Verification

## 1. 개요 (Overview)
본 문서는 `KiwoomWSCollector` 및 `KISRealCollectorUS`의 소켓 연결 및 인증 로직에 대한 **단위 테스트(Unit Test) 전략**을 정의한다.
`docs/governance/development.md`의 **3.4 품질 게이트 1단계**를 준수하며, 특히 **[Backend Specification Sheet](../../specs/backend_specification.md)**에 정의된 프로토콜과 에러 처리 규정이 코드에 올바르게 구현되었는지 검증한다.

## 2. 규정 준수 및 정책 맵핑 (Compliance & Policy Mapping)
### 2.1 스펙 기반 검증 (Spec-Based Verification)
- **Source of Truth**: 모든 테스트 케이스(Input/Output)는 `docs/specs/backend_specification.md`의 스키마 정의를 따른다.
- **Verification Target**: 
    - WebSocket Request Packet 구조 (Header/Body).
    - WebSocket/REST Error Handling (`OPSP0002`, `IGW00221` 등).

### 2.2 테스트 레지스트리 맵핑 (Test Registry ID)
다음 테스트 ID를 신규 할당하여 관리한다:
| ID | 테스트명 | 대상 모듈 | 검증 목표 |
| :--- | :--- | :--- | :--- |
| **KWM-AUTH-01** | `test_kiwoom_ws_auth` | `KiwoomWSCollector` | 토큰 갱신 및 소켓 인증 패킷 구조 검증 |
| **KWM-PRS-01** | `test_kiwoom_parsing` | `KiwoomWSCollector` | 10호가/체결 데이터 파싱 및 Redis 모델링 검증 |
| **KIS-AUTH-01** | `test_kis_us_auth` | `KISRealCollectorUS` | 미국장 Approval Key 헤더 및 발급 로직 검증 |
| **SEC-ENV-01** | `test_env_security` | `SecurityConfig` | 환경변수 로딩 및 중요 키 마스킹 처리 검증 |

## 3. 테스트 시나리오 (Unit Test Cases)

### 3.1 공통 제약 (Common Constraints)
- **Zero-Network**: 테스트 실행 중 어떠한 실제 네트워크 패킷도 외부로 전송되어서는 안 된다.
- **Fast Feedback**: 전체 유닛 테스트는 2초 이내에 완료되어야 한다.

### 3.2 상세 시나리오 (Detail Scenarios)

#### Case 1: Kiwoom WebSocket Auth (KWM-AUTH-01)
- **Input**: `KIWOOM_APP_KEY="mock_key"`, `KIWOOM_APP_SECRET="mock_secret"`
- **Mock**: `aiohttp.ClientSession.post` (Token Response), `session.ws_connect` (Socket)
- **Verify**:
    1.  `_refresh_token()` 호출 시 REST API로 올바른 JSON Body 전송 여부.
    2.  WebSocket 연결 직후 `send_json`으로 전송되는 Payload에 `token`과 `tr_id`가 포함되는지.

#### Case 2: KIS US Approval Key (KIS-AUTH-01)
- **Input**: `KIS_APP_KEY="mock_key"`
- **Mock**: `aiohttp.ClientSession.post` (Approval Key Response)
- **Verify**:
    1.  `get_approval_key()`가 반환한 Key가 내부 변수에 정상 저장되는지.
    2.  API 응답 실패(Non-200) 시 적절한 예외(`Exception`)가 발생하는지.

#### Case 3: Data Parsing Logic (KWM-PRS-01, KIS-PRS-01)
- **Data**: 실제 수신된 JSON의 고정 샘플 (Fixture)
- **Action**: 파싱 메서드 호출 (`parse_us_tick`, `_handle_message`)
- **Verify**:
    1.  입력 JSON 필드(`price`, `symbol`, `timestamp`)가 Pydantic 모델로 정확히 매핑되는지.
    2.  잘못된 데이터(필드 누락, 타입 오류) 입력 시 Crash 없이 에러 처리(Logging) 되는지.

#### Case 4: Security Configuration (SEC-ENV-01)
- **Action**: `os.environ`을 조작하여 키 누락 상황 시뮬레이션.
- **Verify**: 필수 키(`KIS_APP_KEY` 등) 누락 시 프로그램 시작 단계에서 `ValueError` 등으로 즉시 실패(Fast Fail)하는지.

### 3.3 예외 시나리오: 실제 키 검증 (Tier 2 Integration - Conditional)
> **[EXCEPTION]** "외부 키가 유효한지" 검증하려면 실제 네트워크 요청이 필수적이다. 단, 운영 안정성을 위해 다음 **장외(Off-Market) 조건** 하에서만 제한적으로 수행한다.

#### Policy: 장외 검증 조건 (Off-Market Condition)
- **실행 시간**: **양대 시장 휴장 시간(Gap Time)**에만 실행한다.
    - KR 장중 (08:30 ~ 16:00) ❌ 실행 금지
    - US 장중 (22:30 ~ 05:30) ❌ 실행 금지 (Pre/Post 포함 시 17:00 ~ 08:00 권장)
    - **Safe Window**: 16:30 ~ 22:00 (저녁 틈새) 또는 06:00 ~ 08:00 (아침 틈새).
- **대상**:
    - `KIWOOM_APP_KEY`: KR 시장 종료 여부 확인 필수.
    - `KIS_APP_KEY`: **국내/미국 공용**이므로, **KR과 US 시장이 모두 종료된 상태**에서만 검증한다.
- **방법**: 단순 접속(Ping)이 아닌, **Token 발급(REST)** 또는 **현재가 조회(Snapshot)**를 1회 수행하여 응답 코드로 키 유효성 판단.

#### Case 5: Real Auth Check (KEY-VAL-REAL-01)
- **Condition**: `current_time` not in (Market Hours) AND `ENABLE_REAL_KEY_TEST=True`
- **Action**:
    1. Kiwoom: REST API (`/oauth2/token`) 요청 전송.
    2. KIS: REST API (`/oauth2/Approval`) 요청 전송.
- **Verify**: HTTP 200 OK 및 정상 Token/Key 반환 확인. (401/403 응답 시 "키 무효"로 판정하고 즉시 Alert)

## 4. 실행 계획 (Execution Plan)
1.  **Skeleton Code**: 테스트 파일 구조 생성 (`tests/unit/test_backend_auth.py` 등).
2.  **Implementation**: 각 시나리오별 Mocking 코드 및 Assertion 구현.
3.  **Validation**: `pytest` 실행 및 커버리지 리포트 생성.
4.  **Register**: `test_registry.md`에 신규 ID 등록 및 상태 업데이트.

## 5. 결론
이 전략은 기존 정책(`development.md`, `test_registry.md`)을 완벽히 계승하며, 안전하고 빠른 검증을 보장합니다.
승인 시 `tests/unit/` 디렉토리에 위 시나리오를 구현합니다.
