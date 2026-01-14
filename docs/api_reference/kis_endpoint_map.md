# 📚 KIS API Endpoint & TR ID Map

> **Purpose**: Central reference for Korea Investment Securities (KIS) API endpoints, distinguishing between **REST API (Pull)** and **WebSocket (Push)** services.

---

## 1. Real-time WebSocket (Push)
> **Domain**: `ws://ops.koreainvestment.com:21000` (Real) / `ws://ops.koreainvestment.com:21000` (Virtual - check port)

| Base Asset | Data Type | TR ID (Real) | TR ID (Mock) | Path | Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Domestic (KR)** | Execution (체결) | `H0STCNT0` | `H0STCNT0` | `/tryitout/H0STCNT0` | Tick Data |
| **Domestic (KR)** | Orderbook (호가) | `H0STASP0` | `H0STASP0` | `/tryitout/H0STASP0` | 10-level Hoga |
| **Overseas (US)** | Execution (체결) | `HDFSCNT0` | *N/A* (Check Note) | `/tryitout/HDFSCNT0` | **Official Real TR**. Mock support varies by doc. |
| **Overseas (US)** | Orderbook (호가) | `HDFSASP0` | N/A | `/tryitout/HDFSASP0` | Code uses `HHDFS76200100` (Legacy Alias?) |
| **Overseas (US)** | Notification (통보) | `H0GSCNI0` | `H0GSCNI0` | `/tryitout/H0GSCNI0` | Account Tx Notification |

> **Note on TR IDs & Simulation**:
> *   **US Execution (`HDFSCNT0`)**: Official KIS docs list this for Realtime. Some sources say it works for Mock, but your reference says "Mock Unsupported". We follow your reference (N/A).
> *   **US Orderbook**: Official Doc = `HDFSASP0`. Actual Working Code = `HHDFS76200100`. KIS API often supports multiple aliases, but `HHDFS...` is safer for older keys.

---

## 4. WebSocket Output Fields (Data Structure)

### 4.1 Real-time Execution (체결)
| Market | TR ID | Symbol | Price | Change | Volume |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **KR** | `H0STCNT0` | `Field[0]` | `Field[2]` | `Field[5]` | `Field[7]` (Acml) |
| **US** | `HDFSCNT0` | `Field[1]` | `Field[11]` | N/A | `Field[13]` (Tick) |

### 4.2 Real-time Orderbook (호가)
| Market | TR ID | Structure |
| :--- | :--- | :--- |
| **KR** | `H0STASP0` | **Asks 1~5**: Price `[3..7]`, Vol `[21..25]` <br> **Bids 1~5**: Price `[12..16]`, Vol `[30..34]` |
| **US** | `HHDFS76200100` | **Loop (5 Levels)**: <br> Ask Price `[10 + 4i]`, Vol `[11 + 4i]` <br> Bid Price `[12 + 4i]`, Vol `[13 + 4i]` |

---

## 2. REST API (Pull/Query)
> **Domain**: `https://openapi.koreainvestment.com:9443` (Real) / `https://openapivts.koreainvestment.com:29443` (Mock)

### 2.1 Domestic Stock (국내주식) - Quotations (시세)

| Service Name | Description | Endpoint URL | TR ID (Real) | TR ID (Mock) |
| :--- | :--- | :--- | :--- | :--- |
| **주식현재가 예상체결** | 장전/장후 동시호가 예상체결가 조회 | `/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn` | `FHKST01010200` | `FHKST01010200` |
| **주식현재가 체결** | 현재가 및 최근 체결 내역 조회 | `/uapi/domestic-stock/v1/quotations/inquire-ccnl` | `FHKST01010300` | `FHKST01010300` |
| **국내주식 시간외호가** | 시간외 단일가 등 호가 조회 | `/uapi/domestic-stock/v1/quotations/inquire-overtime-asking-price` | `FHPST02300400` | *(Not Supported)* |

### 2.2 Formatting Rules
- **Header**:
    - `Content-Type`: `application/json; charset=utf-8`
    - `tr_id`: (Matched TR ID)
    - `custtype`: `P` (Individual) or `B` (Corporate)

---

## 3. Detailed Comparison: Verified WebSocket vs. Provided REST API

| Feature | ✅ Verified WebSocket Config (US Success) | 🆕 Provided REST API Config (KR Inquire) |
| :--- | :--- | :--- |
| **Protocol** | **WebSocket** (RFC 6455) | **HTTPS** (REST/JSON) |
| **Domain** | `ops.koreainvestment.com:21000` | `openapi.koreainvestment.com:9443` |
| **Path Structure** | `/{TR_ID}` (e.g., `/HDFSCNT0`) | `/uapi/domestic-stock/v1/quotations/...` |
| **Interaction** | **Push (Subscription)** | **Pull (Request/Response)** |
| **Data Nature** | **Streaming** (Continuous Ticks) | **Snapshot** (Current State/History) |
| **Authentication** | **Approval Key** (WebSocket Key) | **Access Token** (Bearer Token) |
| **Primary Use** | **Live Trading**: Monitoring rapid price changes. | **Inquiry**: Checking overtime prices, market cap, or filling missing data gaps. |
| **TR ID Examples** | `HDFSCNT0` (US Tick), `H0STCNT0` (KR Tick) | `FHKST01010300` (KR Tick Info), `FHPST02300400` (Overtime) |
