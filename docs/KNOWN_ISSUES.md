# Known Issues

**Purpose**: Document all known issues, their status, and resolutions  
**Update Frequency**: After each incident  
**Owner**: Dev Team

---

## 🔴 Critical Issues (Resolved)

### 1. Data Collection Gaps - ALREADY IN SUBSCRIBE Errors

**Status**: ✅ RESOLVED (2026-01-15)  
**Severity**: CRITICAL  
**Incident Report**: [docs/incidents/2026-01-15_data_collection_failures.md](incidents/2026-01-15_data_collection_failures.md)

#### Symptom

- Collector crashes repeatedly during WebSocket reconnection
- Logs show: `❌ SUBSCRIBE FAILED: <symbol> - ALREADY IN SUBSCRIBE`
- All retry attempts (3x) fail for affected symbols
- Result: 0 ticks collected, complete data loss

#### Root Cause

**Immediate**: WebSocket `run()` method did not explicitly unsubscribe before reconnecting.

**Mechanism**: 
1. WebSocket connection breaks (timeout, network issue, etc.)
2. Collector attempts to reconnect
3. KIS API server still has previous subscriptions active
4. New subscribe requests fail with "ALREADY IN SUBSCRIBE"
5. Retry logic exhausted → No data collection

**Why it happened repeatedly**:
- No restart policy → manual intervention required each time
- No monitoring → discovered hours later
- No documentation → same mistake repeated daily

#### Resolution

**Fix Applied**: 
- Added `cleanup_subscriptions()` method to `websocket_base.py`
- Calls `unsubscribe_market()` for all active markets before reconnect
- 3-second grace period for KIS server to process unsubscribes

**Commit**: `8781ff5`

**Code**:
```python
async def cleanup_subscriptions(self):
    \"\"\"🧹 EMERGENCY FIX: Explicit cleanup before reconnect\"\"\"
    for market in list(self.active_markets):
        try:
            await self.unsubscribe_market(market)
        except Exception as e:
            logger.error(f\"Cleanup failed for {market}: {e}\")
    
    await asyncio.sleep(3)  # Grace period
    logger.info(\"✅ Cleanup complete. Ready for reconnect.\")
```

#### Prevention

- **Immediate**: Cleanup method now runs on every reconnection
- **Monitoring**: Track subscribe error rates (Prometheus metric)
- **Alerting**: Alert if error rate > 0.5/sec for 5 minutes
- **Testing**: Add integration test for reconnection scenario

#### Related

- **Runbook**: [Data Collection Recovery - Subscription Issues](runbooks/data_collection_recovery.md#recovery-subscription-issues)
- **Monitoring**: [Monitoring Requirements - Subscribe Errors](infrastructure/monitoring_requirements.md#alert-5-high-subscribe-error-rate)

---

### 2. Data Collection Gaps - Archiver Missing Restart Policy

**Status**: ✅ RESOLVED (2026-01-15)  
**Severity**: CRITICAL  
**Incident Report**: [docs/incidents/2026-01-15_data_collection_failures.md](incidents/2026-01-15_data_collection_failures.md)

#### Symptom

- Collector is running and publishing to Redis
- Logs show: `📤 PUBLISHED: ticker.kr | 005930 @ 142900.0`
- BUT: Database has no new ticks
- No errors visible in collector logs

#### Root Cause

**Immediate**: `timescale-archiver` service had no `restart: unless-stopped` policy in docker-compose.yml.

**Mechanism**:
1. Archiver crashes (DB connection error, memory issue, etc.)
2. Container exits
3. Docker does NOT auto-restart (no restart policy)
4. Collector continues publishing to Redis (works fine)
5. Data accumulates in Redis but never reaches DB → **Silent data loss**

**Why undetected**:
- Collector logs look normal (still publishing)
- No monitoring on archiver status
- No DB write verification
- Only discovered by manual SQL query

#### Resolution

**Fix Applied**:
- Added `restart: unless-stopped` to `timescale-archiver` service in docker-compose.yml
- Ensures automatic recovery from crashes

**Commit**: `4fe80ca`

**Diff**:
```yaml
timescale-archiver:
  # ... existing config ...
  restart: unless-stopped  # ← ADDED
```

#### Prevention

- **Immediate**: All critical services now have restart policies
- **Verification**: Deployment checklist includes service status check
- **Monitoring**: Track archiver status + flush rate (Prometheus)
- **Alerting**: Alert if archiver down for > 1 minute

#### Action Items

- [ ] Audit ALL services in docker-compose.yml for restart policies
- [ ] Document which services should NOT auto-restart (one-offs like history-loader)
- [ ] Add smoke test: Verify archiver is flushing to DB

#### Related

- **Runbook**: [Data Collection Recovery - Archiver Down](runbooks/data_collection_recovery.md#recovery-archiver-down)
- **Deployment**: [Checklist - Service Status](deployment/CHECKLIST.md#critical-service-status-check)
- **Monitoring**: [Requirements - Archiver Metrics](infrastructure/monitoring_requirements.md#12-archiver-metrics)

---

## 🟡 Known Limitations (Not Issues)

### 1. Market Hours Only Data Collection

**Description**: System only collects data during market hours (09:00-15:30 KST).

**Reason**: Design choice - after-hours trading volume is minimal.

**Impact**: No pre-market or post-market data.

**Workaround**: None needed (by design).

---

### 2. KIS API Rate Limits

**Description**: KIS API has subscription limits (40 symbols max per connection).

**Current**: Using ~24 symbols (well within limit).

**Risk**: If we add more symbols, may need multiple collectors.

**Mitigation**: Monitor symbol count, plan for scale-out architecture.

---

## 🟢 Resolved Issues (Historical)

### 3. [Example] WebSocket Connection Timeout

**Status**: ✅ RESOLVED (2026-01-10)  
**Symptom**: Collector disconnected after 10 seconds  
**Fix**: Increased ping_timeout from 10s to 30s  
**Commit**: `abc1234`

---

## 📋 Template for New Issues

When adding a new issue, use this template:

```markdown
### N. <Issue Title>

**Status**: 🔴 ACTIVE / 🟡 MONITORING / ✅ RESOLVED  
**Severity**: CRITICAL / HIGH / MEDIUM / LOW  
**Discovered**: YYYY-MM-DD  

#### Symptom
- What users/operators observe
- Error messages
- Failure conditions

#### Root Cause
- Technical explanation
- Why it happens
- Mechanism breakdown

#### Resolution
- Fix applied (if resolved)
- Commit hash
- Code snippet (if relevant)

#### Prevention
- Monitoring added
- Alerts configured
- Process changes
- Tests added

#### Related
- Links to runbooks
- Links to incident reports
- Links to monitoring docs
```

---

## 🔗 Related Documentation

- **Incident Reports**: `docs/incidents/`
- **Runbooks**: `docs/runbooks/`
- **Deployment Checklist**: `docs/deployment/CHECKLIST.md`
- **Monitoring**: `docs/infrastructure/monitoring_requirements.md`

---

**Last Updated**: 2026-01-15  
**Next Review**: After each incident  
**Owner**: Dev Team
