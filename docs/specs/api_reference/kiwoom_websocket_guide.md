# Kiwoom REST API WebSocket 연동 가이드

## 개요
- **운영 도메인**: `wss://api.kiwoom.com:10000`
- **모의투자 도메인**: `wss://mockapi.kiwoom.com:10000` (KRX만 지원)
- **Endpoint**: `/api/dostk/websocket`
- **Format**: JSON
- **Content-Type**: `application/json;charset=UTF-8`

## 1. 인증 플로우

### 1.1 Token 발급 (REST API)

**Endpoint**: `POST https://api.kiwoom.com/oauth2/token`

**Request**:
```json
{
  "grant_type": "client_credentials",
  "appkey": "YOUR_APP_KEY",
  "secretkey": "YOUR_SECRET_KEY"
}
```

**Headers**:
```json
{
  "Content-Type": "application/json; charset=UTF-8",
  "User-Agent": "Mozilla/5.0"
}
```

**Response** (성공):
```json
{
  "expires_dt": "20260117213932",
  "return_msg": "정상적으로 처리되었습니다",
  "token_type": "Bearer",
  "return_code": 0,
  "token": "oBvZgYe1TFV0aIXMcObQhfuYbS2WNSWWOHAwq7uBUnMAmHvpGzSq6W7-RfieTE5rOxvwIHcOHnq2kJNoLREqMg"
}
```

### 1.2 WebSocket 연결

**라이브러리**: `websockets` (Python) - ⚠️ `aiohttp`는 400 에러 발생

```python
import websockets

async with websockets.connect("wss://api.kiwoom.com:10000/api/dostk/websocket") as ws:
    # ...
```

### 1.3 LOGIN (접속허용요청)

**⚠️ 중요**: WebSocket 연결 후 **첫 번째 메시지**는 반드시 LOGIN이어야 함

**Request**:
```json
{
  "trnm": "LOGIN",
  "token": "YOUR_ACCESS_TOKEN"
}
```

**Response** (성공):
```json
{
  "trnm": "LOGIN",
  "return_code": 0,
  "return_msg": "",
  "sor_yn": "Y"
}
```

## 2. 실시간 데이터 등록 (REG)

### 2.1 등록 (REG)

**Request**:
```json
{
  "trnm": "REG",
  "grp_no": "0001",
  "refresh": "1",
  "data": [
    {
      "item": ["005930", "000660"],
      "type": ["0B"]
    }
  ]
}
```

**필드 설명**:
- `trnm`: `"REG"` (등록) / `"REMOVE"` (해지)
- `grp_no`: 그룹번호 (4자리 문자열, 예: "0001")
- `refresh`: 기존 등록 유지 여부
  - `"0"`: 기존 유지 안함
  - `"1"`: 기존 유지 (Default)
- `data[].item`: 종목코드 배열 (최대 100개)
- `data[].type`: TR 타입 배열 (예: `["0B"]`)

**Response**:
```json
{
  "trnm": "REG",
  "return_code": 0,
  "return_msg": ""
}
```

### 2.2 해지 (REMOVE)

**Request**:
```json
{
  "trnm": "REMOVE",
  "grp_no": "0001",
  "data": [
    {
      "item": ["005930"],
      "type": ["0B"]
    }
  ]
}
```

## 3. TR 타입 (실시간 데이터 종류)

| TR 코드 | 명칭 | 설명 | 검증 상태 |
|---------|------|------|-----------|
| `00` | 주문체결 | 주문 체결 정보 | - |
| `04` | 잔고 | 계좌 잔고 | - |
| `0A` | 주식기세 | 주식 기본 시세 | ✅ 성공 |
| `0B` | 주식체결 | 주식 체결 정보 | ✅ 성공 |
| `0C` | 주식우선호가 | 우선호가 정보 | ✅ 성공 |
| `0D` | 주식호가잔량 | 호가 잔량 | ✅ 성공 |
| `0E` | 주식시간외호가 | 시간외 호가 | - |
| `0F` | 주식당일거래원 | 당일 거래원 | - |
| `0G` | ETF NAV | ETF NAV 정보 | - |
| `0H` | 주식예상체결 | 예상 체결 | - |
| `0I` | 국제금환산가격 | 국제금 환산가격 | - |
| `0J` | 업종지수 | 업종 지수 | - |
| `0U` | 업종등락 | 업종 등락 | - |
| `0g` | 주식종목정보 | 종목 정보 | - |
| `0m` | ELW 이론가 | ELW 이론가 | - |
| `0s` | 장시작시간 | 장 시작 시간 | - |
| `0u` | ELW 지표 | ELW 지표 | - |
| `0w` | 종목프로그램매매 | 프로그램 매매 | - |
| `1h` | VI발동/해제 | 변동성완화장치 | - |

## 4. 실시간 데이터 수신

### 4.1 데이터 형식

**REAL 데이터**:
```json
{
  "trnm": "REAL",
  "data": [
    {
      "type": "0B",
      "name": "주식체결",
      "item": "005930",
      "values": {
        "10": "70500",
        "27": "70600",
        "28": "70500"
      }
    }
  ]
}
```

### 4.2 주식체결 (0B) 주요 필드

| FID | 필드명 | 타입 | 설명 |
|-----|--------|------|------|
| `10` | 현재가 | String | 현재가 |
| `27` | (최우선)매도호가 | String | 매도 1호가 |
| `28` | (최우선)매수호가 | String | 매수 1호가 |
| `910` | 체결가 | String | 체결가격 |
| `911` | 체결량 | String | 체결량 |

### 4.3 PING 메시지

서버가 주기적으로 전송하는 Keep-Alive 메시지:
```json
{
  "trnm": "PING"
}
```

⚠️ PONG 응답은 **불필요** (자동 처리됨)

## 5. 에러 코드

| return_code | return_msg | 설명 |
|-------------|------------|------|
| `0` | - | 성공 |
| `100002` | 필수 파라미터가 누락되어 있습니다 | `trnm` 누락 |
| `100013` | 로그인 인증이 들어오기 전에... | LOGIN 없이 다른 메시지 전송 |
| `105108` | 정의되어 있지 않는 TRNM입니다 | 잘못된 `trnm` 값 |
| `805002` | 인증을 체크하기 위한 Token 값이 없습니다 | Token 누락 |

## 6. 구현 예제

### 6.1 최소 구현

```python
import asyncio
import json
import websockets
import aiohttp

async def kiwoom_realtime():
    # 1. Get Token
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.kiwoom.com/oauth2/token",
            json={
                "grant_type": "client_credentials",
                "appkey": "YOUR_APP_KEY",
                "secretkey": "YOUR_SECRET_KEY"
            },
            headers={"Content-Type": "application/json"}
        ) as resp:
            token = (await resp.json())["token"]
    
    # 2. Connect WebSocket
    async with websockets.connect("wss://api.kiwoom.com:10000/api/dostk/websocket") as ws:
        # 3. LOGIN
        await ws.send(json.dumps({"trnm": "LOGIN", "token": token}))
        print(await ws.recv())
        
        # 4. REG
        await ws.send(json.dumps({
            "trnm": "REG",
            "grp_no": "0001",
            "refresh": "1",
            "data": [{"item": ["005930"], "type": ["0B"]}]
        }))
        print(await ws.recv())
        
        # 5. Receive Data
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            if data.get("trnm") == "REAL":
                print(f"실시간 데이터: {data}")

asyncio.run(kiwoom_realtime())
```

## 7. 주의사항

1. **`aiohttp`의 `ws_connect`는 400 에러** → `websockets` 라이브러리 사용 필수
2. **LOGIN은 항상 첫 메시지**여야 함
3. **`trnm`은 root 레벨**에 위치 (header 내부 X)
4. **실시간 데이터는 장 시간에만** 수신됨
5. **최대 100개 종목**까지 한 번에 등록 가능

## 8. 검증 완료 사항

- ✅ Token 발급 성공
- ✅ WebSocket 연결 성공 (`websockets` 라이브러리)
- ✅ LOGIN 성공
- ✅ REG 성공 (0B, 0D, 0A, 0C)
- ⏰ 실시간 데이터 수신 (장 시간 대기 중)

## 9. 참고 자료

- 공식 문서: `/docs/키움 REST API 문서.xlsx`
- 테스트 스크립트: `/scripts/kiwoom_official_spec.py`
- 발견 로그: `/kiwoom_login_test.log`
