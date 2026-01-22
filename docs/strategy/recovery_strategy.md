# Failure Recovery Strategy (Doomsday Protocol)

## 1. Risk Assessment
Despite successful verification, Dual-Socket architecture introduces complexity:
- **Simultaneous Failure**: Both sockets blocked by KIS (IP ban or server limit).
- **Synchronization Drift**: One socket constantly reconnecting while other stays dormant.

## 2. Detection Mechanism (Sentinel)
Leverage existing `sentinel-agent` to act as a "Dead Man's Switch".
- **Metric**: Redis `ticker.kr` & `orderbook.kr` message rates.
- **Threshold**: Zero messages for **60 seconds** during Market Hours (09:00-15:30).
- **Alert**: Discord/Log Error.

## 3. Automated Recovery Actions

### Level 1: Hard Restart (The "Kick" Approach)
- **Condition**: First detection of zero data.
- **Action**: `docker restart real-collector`
- **Logic**: Clears transient state, stuck websockets, or memory leaks.

### Level 2: Mode Degrade (The "Retreat" Approach)
- **Condition**: Zero data persists 5 min after Level 1 (or 2nd consecutive alarm).
- **Action**: 
    1. Update `.env` (or runtime config): `ENABLE_DUAL_SOCKET=false`.
    2. Restart `real-collector`.
- **Result**: System falls back to the legacy "Single Socket" mode (Verified stable but lower throughput). 
- **Trade-off**: High latency accepted to guarantee data survival.

## 4. Implementation Checklist
- [ ] **Sentinel Logic Update**: Add `check_ingestion_health()` in `sentinel.py`.
- [ ] **Unified Collector Update**: Add `ENABLE_DUAL_SOCKET` flag handling in `unified_collector.py`.
- [ ] **Docker Control**: Give `sentinel-agent` permission to restart containers (mount `docker.sock` - *Security Note: Use proxy or restricted API in prod, direct mount for Phase 2*).

## 5. Verification
- **Simulate Failure**: Manually block port 21000 or stop `real-collector` logic.
- **Verify Trigger**: Sentinel detects gap -> Restarts container.
- **Verify Fallback**: If failure continues, Sentinel disables Dual-Socket -> Restarts -> System recovers in Single Mode.
