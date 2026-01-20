# Virtual Investment Platform - Backend API Specification

**Version**: 1.0.0  
**Date**: 2026-01-17  
**Related**: `ISSUE-001`, `src/broker/virtual.py`

---

## 1. Overview

가상 투자 플랫폼을 위한 REST API 및 WebSocket 이벤트 명세입니다. 실제 거래 없이 전략을 시뮬레이션할 수 있도록 계좌 관리, 주문 실행, PnL 조회 기능을 제공합니다.

**Base URL**: `/api/virtual`

---

## 2. REST API Endpoints

### 2.1 Account Management

#### GET `/api/virtual/account`
**Description**: 가상 계좌 정보 조회

**Request**:
```http
GET /api/virtual/account
Authorization: Bearer {api_key}
```

**Response** (200 OK):
```json
{
  "account_id": 1,
  "name": "Virtual Account 01",
  "balance": 100000000.00,
  "currency": "KRW",
  "created_at": "2026-01-17T00:00:00Z",
  "updated_at": "2026-01-17T08:00:00Z"
}
```

**Errors**:
- `404 Not Found`: Account does not exist

---

#### GET `/api/virtual/positions`
**Description**: 현재 보유 포지션 조회

**Query Parameters**:
- `symbol` (optional): 특정 종목 필터

**Response** (200 OK):
```json
{
  "positions": [
    {
      "symbol": "005930",
      "name": "삼성전자",
      "quantity": 10,
      "avg_price": 70000.00,
      "current_price": 72000.00,
      "unrealized_pnl": 20000.00,
      "unrealized_pnl_pct": 2.86
    }
  ],
  "total_value": 720000.00
}
```

---

### 2.2 Order Management

#### POST `/api/virtual/orders`
**Description**: 신규 주문 생성

**Request Body**:
```json
{
  "symbol": "005930",
  "side": "BUY",
  "type": "LIMIT",
  "quantity": 10,
  "price": 70000.00
}
```

**Field Constraints**:
- `side`: `"BUY"` | `"SELL"`
- `type`: `"LIMIT"` | `"MARKET"`
- `price`: Required for LIMIT orders, optional for MARKET (uses current market price)

**Response** (201 Created):
```json
{
  "status": "FILLED",
  "order_id": "550e8400-e29b-41d4-a716-446655440000",
  "symbol": "005930",
  "side": "BUY",
  "filled_price": 70000.00,
  "filled_quantity": 10,
  "commission": 105.00,
  "tax": 0.00,
  "timestamp": "2026-01-17T08:00:00Z"
}
```

**Response** (400 Bad Request - Rejected):
```json
{
  "status": "REJECTED",
  "reason": "Insufficient Funds",
  "required": 700105.00,
  "available": 500000.00
}
```

**Errors**:
- `400 Bad Request`: Invalid parameters or insufficient funds/position
- `404 Not Found`: Symbol not found

---

#### GET `/api/virtual/orders`
**Description**: 주문 내역 조회

**Query Parameters**:
- `limit` (default: 50): 조회할 주문 수
- `symbol` (optional): 종목 필터
- `status` (optional): `PENDING` | `FILLED` | `CANCELLED` | `REJECTED`

**Response** (200 OK):
```json
{
  "orders": [
    {
      "order_id": "550e8400-e29b-41d4-a716-446655440000",
      "symbol": "005930",
      "side": "BUY",
      "type": "LIMIT",
      "price": 70000.00,
      "quantity": 10,
      "status": "FILLED",
      "filled_price": 70000.00,
      "filled_quantity": 10,
      "fee": 105.00,
      "tax": 0.00,
      "created_at": "2026-01-17T07:59:00Z",
      "executed_at": "2026-01-17T08:00:00Z"
    }
  ],
  "total": 1
}
```

---

#### GET `/api/virtual/orders/{order_id}`
**Description**: 특정 주문 상세 조회

**Response** (200 OK):
```json
{
  "order_id": "550e8400-e29b-41d4-a716-446655440000",
  "symbol": "005930",
  "side": "BUY",
  "type": "LIMIT",
  "price": 70000.00,
  "quantity": 10,
  "status": "FILLED",
  "filled_price": 70000.00,
  "filled_quantity": 10,
  "commission": 105.00,
  "tax": 0.00,
  "created_at": "2026-01-17T07:59:00Z",
  "executed_at": "2026-01-17T08:00:00Z"
}
```

**Errors**:
- `404 Not Found`: Order not found

---

### 2.3 Analytics

#### GET `/api/virtual/pnl`
**Description**: Profit & Loss 조회

**Query Parameters**:
- `period` (optional): `day` | `week` | `month` | `all` (default: `all`)

**Response** (200 OK):
```json
{
  "realized_pnl": 50000.00,
  "unrealized_pnl": 20000.00,
  "total_pnl": 70000.00,
  "total_pnl_pct": 0.07,
  "total_trades": 5,
  "win_rate": 0.6,
  "period_start": "2026-01-17T00:00:00Z",
  "period_end": "2026-01-17T08:00:00Z"
}
```

---

## 3. WebSocket Events

### 3.1 Connection

**Endpoint**: `ws://{host}/ws/virtual`

**Authentication**: Query parameter `?api_key={key}`

**Example**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/virtual?api_key=xxx');
```

---

### 3.2 Event Types

#### Event: `virtual.execution`
**Trigger**: 주문 체결 시

**Payload**:
```json
{
  "type": "EXECUTION",
  "data": {
    "status": "FILLED",
    "order_id": "550e8400-e29b-41d4-a716-446655440000",
    "filled_price": 70000.00,
    "filled_quantity": 10,
    "commission": 105.00,
    "tax": 0.00,
    "timestamp": "2026-01-17T08:00:00Z"
  },
  "symbol": "005930",
  "side": "BUY"
}
```

---

#### Event: `virtual.account`
**Trigger**: 계좌 잔고 변동 시

**Payload**:
```json
{
  "type": "BALANCE",
  "data": {
    "balance": 99999895.00,
    "currency": "KRW",
    "timestamp": "2026-01-17T08:00:00Z"
  }
}
```

---

#### Event: `virtual.position`
**Trigger**: 포지션 변동 시 (매수/매도)

**Payload**:
```json
{
  "type": "POSITION_UPDATE",
  "symbol": "005930",
  "data": {
    "quantity": 10,
    "avg_price": 70000.00,
    "unrealized_pnl": 20000.00
  }
}
```

---

## 4. Data Models

### 4.1 Order
```typescript
interface Order {
  symbol: string;
  side: "BUY" | "SELL";
  type: "LIMIT" | "MARKET";
  quantity: number;
  price?: number;  // Required for LIMIT, optional for MARKET
}
```

### 4.2 Position
```typescript
interface Position {
  symbol: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
}
```

### 4.3 Account
```typescript
interface Account {
  account_id: number;
  name: string;
  balance: number;
  currency: string;
  created_at: string;
  updated_at: string;
}
```

---

## 5. Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "INSUFFICIENT_FUNDS",
    "message": "Available balance is less than required amount",
    "details": {
      "required": 700105.00,
      "available": 500000.00
    }
  }
}
```

### Error Codes
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INSUFFICIENT_FUNDS` | 400 | 잔고 부족 |
| `INSUFFICIENT_POSITION` | 400 | 보유 수량 부족 |
| `INVALID_SYMBOL` | 404 | 존재하지 않는 종목 |
| `INVALID_QUANTITY` | 400 | 잘못된 수량 (0 이하) |
| `ORDER_NOT_FOUND` | 404 | 주문 정보 없음 |
| `ACCOUNT_NOT_FOUND` | 404 | 계좌 정보 없음 |

---

## 6. Implementation Notes

### 6.1 Transaction Handling
- 모든 주문 처리는 DB 트랜잭션 내에서 원자적으로 실행
- 잔고 업데이트 → 포지션 업데이트 → 주문 기록 순서 보장

### 6.2 Real-time Updates
- Redis Pub/Sub를 통해 WebSocket 클라이언트에 실시간 이벤트 전송
- 채널: `virtual.execution`, `virtual.account`

### 6.3 Market Price Source
- MARKET 주문 시 현재가는 Redis에서 최신 틱 데이터 조회
- 캐시 미스 시 DB에서 마지막 종가 조회

### 6.4 Cost Calculation
- 수수료: 거래대금의 0.015% (키움증권 기준)
- 세금(한국): 매도 시 거래대금의 0.18%
- 세금(미국): 양도소득세 별도 계산 (향후 구현)

---

## 7. Future Enhancements

- [ ] **주문 취소**: `DELETE /api/virtual/orders/{order_id}`
- [ ] **일괄 청산**: `POST /api/virtual/positions/close-all`
- [ ] **지정가 미체결 Queue**: LIMIT 주문의 부분 체결 및 대기 로직
- [ ] **슬리피지 모델**: 호가창 기반 실제 체결가 시뮬레이션
- [ ] **마진 거래**: 신용매수/공매도 지원
