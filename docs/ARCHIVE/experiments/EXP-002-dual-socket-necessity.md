# 🧪 Experiment Record: Single-Socket Concurrency Failure & Dual-Socket Strategy

> **Experiment ID**: EXP-002
> **Date**: 2026-01-10
> **Status**: Concluded (Pivot to Dual-Socket)
> **Related Rules**: `.ai-rules.md` Rule 2.1 (Data Quality), Rule 7.1 (TDD)

## 1. Hypothesis
**"Can a single WebSocket connection simultaneously collect Real-time Execution (Tick) and Orderbook (Hoga) data for both KR and US markets without error?"**

## 2. Experimental Setup
- **Target**: KIS WebSocket Endpoint (`ws://ops.koreainvestment.com:21000`)
- **Protocol**: Mixed TR subscription on one socket.
    - KR Tick: `H0STCNT0`
    - US Tick: `HDFSCNT0` (previously `HHDFS00000300`)
    - Orderbook: `H0STASP0` / `HDFSASP0`
- **Environment**: Docker Container `real-collector`

## 3. Results & Observations

### 3.1 Failure Mode: `invalid tr_key`
- When attempting to mix `HDFSCNT0` (US Tick) with legacy or other TRs on the `/tryitout` endpoint, the server returned `invalid tr_key` or `Zero Data`.
- **Finding**: The endpoint path (`/HDFSCNT0` vs `/tryitout/...`) is sensitive to the *primary* TR intended for that connection. Mixing TRs that ostensibly require different "paths" (even if logically same port) caused authentication or routing failures on KIS side.

### 3.2 Failure Mode: Head-of-Line Blocking (Latency)
- **Observation**: Orderbook data is voluminous (10x updates/sec compared to Ticks).
- **Impact**: On a single asyncio loop, processing massive JSON blobs of Orderbooks delayed the parsing of critical Tick data.
- **Risk**: During high volatility (Market Open), the single socket buffer fills up, causing disconnected sessions or delayed tick timestamps.

### 3.3 Success Case: Isolated Dual-Socket
- By implementing `DualWebSocketManager`:
    - **Socket A (Tick)**: Dedicated to `HDFSCNT0`/`H0STCNT0`. (Path: `/HDFSCNT0`)
    - **Socket B (Orderbook)**: Dedicated to Orderbooks.
- **Verification**: Logs confirmed simultaneous `SUBSCRIBE SUCCESS` on both channels without `invalid tr_key` errors.

## 4. Conclusion & Decision
- **Hypothesis Rejected**: Single socket cannot reliably handle the diverse traffic patterns protocols of Tick and Orderbook simultaneously.
- **Action Item**: Adopt **Dual-Socket Architecture** as the standard implementation (Pillar 2).
- **Alignment with .ai-rules.md**:
    - **Data Integrity (Rule 2.1)**: Isolation prevents Orderbook floods from dropping Tick data.
    - **Resilience (Rule 3.3)**: If Orderbook socket fails/reconnects, Tick socket remains alive.

---

## 5. Artifacts
- **Implementation**: `src/data_ingestion/price/common/websocket_dual.py`
- **Strategy Doc**: `docs/strategies/realtime_ingestion_strategy.md`
