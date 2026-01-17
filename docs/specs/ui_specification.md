# UI Specification & Frontend Protocol (v1.0)

## 1. 개요 (Overview)
본 문서는 사용자 인터페이스(Frontend)와 API 서버(Backend) 간의 통신 규약 및 데이터 교환 스키마를 정의합니다.
`StreamManager.ts` 및 `Dashboard/config.js` 등 모든 클라이언트 코드는 이 명세를 준수해야 합니다.

## 2. 연결 정보 (Connection Protocol)

### 2.1 Endpoint Strategy
- **Base URL**: `http://{HOST}:{PORT}`
- **WebSocket URL**: `ws://{HOST}:{PORT}/ws`
- **Default Port**: `8000` (FastAPI Default)
- **Host Resolution**:
    - `window.location.hostname` (Browser Default)
    - `VITE_API_HOST` (Environment Override)

### 2.2 Reconnection Policy
- **Backoff**: Fixed 3000ms delay.
- **Max Retries**: Infinite (Dashboard should stay alive).

## 3. 메시지 스키마 (Message Schema)

> [!IMPORTANT]
> **Schema Enforcement**: 클라이언트는 데이터의 필드 유무(`if price...`)로 타입을 추론해서는 안 되며, 반드시 `type` 필드를 확인해야 한다.

### 3.1 Packet Structure (Standard)
```json
{
  "type": "TICK" | "ORDERBOOK" | "SYSTEM" | "ALERT",
  "data": { ... },
  "timestamp": "ISO8601 String"
}
```

### 3.2 Market Tick (`type="TICK"`)
```json
{
  "type": "TICK",
  "symbol": "005930",
  "price": 75000.0,
  "volume": 1050.0,
  "change": -500.0,
  "source": "KIS"
}
```

### 3.3 System Alert (`type="ALERT"`)
```json
{
  "type": "ALERT",
  "level": "CRITICAL",
  "message": "Zero Data Detected > 5min"
}
```

## 4. 환경 변수 (Environment Variables)
Frontend 빌드 및 실행 시 다음 환경 변수를 지원해야 한다.
- `VITE_API_HOST`: API 서버 호스트 (기본값: window.location.hostname)
- `VITE_API_PORT`: API 서버 포트 (기본값: 8000)

## 5. 알려진 위반 사항 (Known Violations)
> [!WARNING]
> 현재 `StreamManager.ts`는 `type` 필드를 검사하지 않고 필드 존재 여부로 휴리스틱 파싱을 수행 중임. -> **Refactor Required**.
