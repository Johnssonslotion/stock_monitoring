# KIS Integration Guide (한국투자증권)

## 1. 개요 (Overview)
본 문서는 한국투자증권(KIS) Open API의 연동 아키텍처, 주요 이슈(Anomalies), 그리고 검증 정책을 통합 관리하는 가이드입니다.
기존의 `kis_endpoint_map.md`와 `kis_api_check_guide.md`를 포함하며, 운영 중 발생하는 특이사항을 중점으로 다룹니다.

## 2. 연동 아키텍처 (Architecture)

### 2.1 Hybrid Model
- **Real-time (Push)**: WebSocket을 통해 실시간 체결가(`H0STCNT0`) 및 호가(`H0STASP0`) 수신.
- **REST (Pull)**:
    - **Token Management**: `oauth2/token` (Access Token 발급/갱신).
    - **Backup/Validation**: 장외 시간 대 키 유효성 검증(`oauth2/Approval`) 및 누락 데이터 보정.

### 2.2 Dual Socket Strategy
국내(KR)와 해외(US) 시장의 운영 시간 및 프로토콜 차이를 극복하기 위해 **Dual Socket** 구조를 채택했습니다.
- **Socket A (KR)**: 08:30 ~ 16:30 운영. `H0STCNT0` (KR Tick) 전용.
- **Socket B (US)**: 16:30 ~ 08:30 운영. `HDFSCNT0` (US Tick) 전용.
> **Note**: 시장 전환 시점에 `switch_url()`을 통해 동적으로 엔드포인트를 변경합니다.

---

## 3. 트러블슈팅 및 에러 코드 (Troubleshooting & Error Codes) [UPDATED]

KIS API는 프로토콜별로 상이한 에러 스키마를 따릅니다. 본 섹션은 발생 가능한 주요 에러와 해결책을 정의합니다.

### 3.1 Error Code Schema

#### A. WebSocket Schema
웹소켓 응답 패킷의 Body 내 `msg1` 또는 `msg_cd` 필드를 통해 상태를 전달합니다.
- **Format**: `{"header": {...}, "body": {"msg1": "MESSAGE CONTENT", "msg_cd": "CODE", ...}}`
- **Detection**: `body` 키가 존재하고, 그 안에 `msg1` 키가 존재할 경우 에러/알림 패킷으로 간주.

#### B. REST API Schema
HTTP 응답 Body 내 `rt_cd` (Return Code)와 `msg_cd` (Message Code)를 확인합니다.
- **Format**: `{"rt_cd": "1", "msg_cd": "E1234", "msg1": "Error Description"}`
- **Standard**: `rt_cd`가 **"0"**이면 성공, 그 외(**"1"**)는 실패.

### 3.2 Common Error Codes Table

| Type | Code / Pattern | Severity | Meaning | Resolution |
| :--- | :--- | :--- | :--- | :--- |
| **WS** | `OPSP0000` / `SUBSCRIBE SUCCESS` | Info | 구독 성공 (정상) | N/A |
| **WS** | `OPSP0002` / `ALREADY IN SUBSCRIBE` | **Critical** | 이미 구독된 종목 중복 요청 | 재연결 전 `unsubscribe` 호출 필수. (Grace Period 3s) |
| **WS** | `OPSP0003` / `MANDATORY INPUT MISSING` | High | 필수 필드(`tr_key` 등) 누락 | Payload 구조 검증. (Symbol List가 비었는지 확인) |
| **REST** | `IGW00221` | High | Authentication Failed (키 오류/만료) | Token 유효기간 확인 및 재발급. (장외 테스트에서 주로 발견) |
| **REST** | `IGW00100` | Medium | Invalid Query/Parameter | `mksc_shrn_iscd` 등 입력 파라미터 표준(6자리) 준수 여부 확인. |

---

## 4. 주요 감지된 이상치 (Detected Anomalies & Logs)

로그 분석 및 운영 경험을 통해 식별된 주요 이상 패턴과 해결책입니다.

### 4.1 `ALREADY IN SUBSCRIBE` (Critical)
- **Schema**: `WebSocket` Response
- **Error Pattern**: `{"body": {"msg1": "ALREADY IN SUBSCRIBE", "msg_cd": "OPSP0002"}}`
- **Cause**: 비정상 종료 시 KIS 서버 측에서 세션이 정리되지 않아, 새 소켓에서 중복 구독으로 인식됨.
- **Resolution Strategy**:
    1.  `Disconnect` 이벤트 감지.
    2.  `reconnect()` 진입 전, **메모리에 저장된 모든 종목에 대해 `UNSUBSCRIBE` 패킷 전송**.
    3.  3초 대기(Grace Period) 후 소켓 종료 및 재접속.

### 4.2 WebSocket 10-Minute Disconnect (High)
- **Symptom**: 정확히 10분 또는 30분 주기로 소켓 연결이 끊김 (`ConnectionClosedError`).
- **Cause**: L4 스위치 또는 방화벽의 Idle Timeout. 프로토콜 레벨의 Ping이 아닌 Application Data 부재로 간주됨.
- **Resolution**:
    - App Level Ping(`PINGPONG`)을 30초 주기로 전송하여 트래픽 발생.
    - Code: `ws.send_json({"header": {"tr_id": "PINGPONG"}})`

### 4.3 Token Expiry Race Condition (Medium)
- **Schema**: `REST` Response (`rt_cd`="1", `msg_cd`="IGW00221")
- **Symptom**: 토큰 만료 임박 시, 여러 스레드/프로세스가 동시에 갱신을 시도하여 `400 Bad Request` 유발.
- **Resolution**:
    - **Redis Lock**: `redis.lock("token_refresh", timeout=10)` 사용.
    - 한 프로세스만 갱신하고, 나머지는 갱신된 토큰을 Redis에서 읽어가도록 변경.

---

## 5. 검증 정책 (Verification Policy) [STRICT]

### 5.1 장외 실제 키 검증 (Off-Market Real Key Test)
운영 안정성을 위해 실제 API 키 유효성 검증은 **양대 시장이 모두 닫힌 시간(Gap Time)**에만 수행합니다.

| 조건 | 시간대 (KST) | 검증 가능 여부 | 비고 |
| :--- | :--- | :--- | :--- |
| **KR Market** | 08:30 ~ 16:30 | ❌ 금지 | 트래픽 간섭 방지 |
| **US Market** | 22:30 ~ 05:30 | ❌ 금지 | 트래픽 간섭 방지 |
| **Evening Gap** | **17:00 ~ 22:00** | ✅ **허용** | KR 마감 후 ~ US 개장 전 |
| **Morning Gap** | **06:00 ~ 08:00** | ✅ **허용** | US 마감 후 ~ KR 개장 전 |

> **실행 로직**:
> ```python
> if not (is_kr_market_open() or is_us_market_open()):
>     run_real_key_validation()
> else:
>     skip_test("Market is Open")
> ```

---

## 6. 참고 문서 (References)
- [KIS Endpoint Map](../specs/api_reference/kis_endpoint_map.md): API 엔드포인트 상세.
- [Known Issues](../issues/KNOWN_ISSUES.md): 해결된 주요 이슈 히스토리.
- [Backend Test Strategy](testing/backend_unit_test_strategy.md): 상세 테스트 시나리오.
