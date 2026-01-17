# Backend Specification Sheet (v1.0)

## 1. 개요 (Overview)
본 문서는 `Stock Monitoring System`의 백엔드(데이터 수집, 인증, 처리)가 준수해야 할 **기술적 명세(Specification)**를 정의합니다.
모든 구현 코드와 유닛 테스트는 이 명세를 기준으로 작성되고 검증되어야 합니다.

## 2. 보안 및 인증 (Security & Authentication)

### 2.1 Credential Management
- **Rule**: 모든 민감 정보는 환경 변수(`os.environ`)를 통해서만 주입된다.
- **Reference**: `.env.example`
- **Keys**:
    - `KIS_APP_KEY`, `KIS_APP_SECRET`: 한국투자증권 (Main)
    - `KIWOOM_APP_KEY`: 키움증권 (Sub/Backup)
    - `VITE_API_KEY`: 내부 API 접근용

### 2.2 Token Lifecycle
- **KIS (REST/WS)**:
    - OAuth2 Bearer Token 사용. 유효기간 24시간.
    - 만료 30분 전 자동 갱신 (Redis Lock 필수).
- **Kiwoom (WS)**:
    - 일부 환경에서 Session Token 필요. (Mock 환경은 비인증 허용 가능하나 Prod는 필수)

---

## 3. 통신 프로토콜 (Communication Protocols)

### 3.1 Data Ingestion (Single Socket)
- **Constraint**: `ai-rules.md` (Law #2) 및 `RFC-001`에 의거하여 **Single Socket** 연결만 허용된다.
- **Failover**: 미국/한국 시장 데이터 수신 채널을 단일화하며, Socket 연결 끊김 시 재접속(Reconnect) 외의 이중화(Dual Socket) 시도는 금지된다.

| Channel | Function | Protocol | Endpoint | Coverage |
| :--- | :--- | :--- | :--- | :--- |
| **Primary** | KR/US Tick/Orderbook | WebSocket | `ws://ops.koreainvestment.com:21000` | Global Market |

### 3.2 Keep-Alive Policy
- **Application Ping**: 30초 주기. Packet: `{"header": {"tr_id": "PINGPONG"}}`
- **Pong Expectation**: Server may reflect the packet or ignore. Client resets "Last Heartbeat" timer upon sending.

---

## 4. 데이터 및 메시지 스키마 (Data & Message Schemas)

### 4.1 WebSocket Packets
**Request (Subscription)**:
```json
{
  "header": {
    "approval_key": "${APPROVAL_KEY}",
    "custtype": "P",
    "tr_type": "1",
    "content-type": "utf-8"
  },
  "body": {
    "input": {
      "tr_id": "${TR_ID}",
      "tr_key": "${SYMBOL}" 
    }
  }
}
```

**Response (Success/Data)**:
- **Header**: `tr_id`, `datetime` 등 메타데이터.
- **Body**: 파이프(`|`)로 구분된 텍스트 데이터.

### 4.2 Error Schemas
**WebSocket Error Body**:
```json
{
  "body": {
     "msg1": "MESSAGE CONTENT",
     "msg_cd": "ERROR_CODE"
  }
}
```

**REST API Error Body**:
```json
{
  "rt_cd": "1",
  "msg_cd": "ERROR_CODE",
  "msg1": "Description"
}
```

---

## 5. 예외 처리 규정 (Error Handling Policy)

| Error Code | Meaning | Required Behavior |
| :--- | :--- | :--- |
| **OPSP0002** | Already Subscribed | **FORCE UNSUBSCRIBE** target symbol -> Retry Subscribe |
| **IGW00221** | Auth Failed | **FORCE TOKEN REFRESH** -> Retry Request |
| **Timeout** | Socket Idle > 10m | **RECONNECT SOCKET** (Close -> Open) |

---

## 6. 테스트 준수 사항 (Test Compliance)
- **Unit Tests**: 위 명세에 정의된 Packet Structure와 Error Handling 로직을 Mocking을 통해 검증해야 함.
- **Deviation**: 구현 코드가 본 명세와 다를 경우, 코드가 아닌 **명세를 먼저 수정(업데이트)**하고 코드를 맞춰야 함.
