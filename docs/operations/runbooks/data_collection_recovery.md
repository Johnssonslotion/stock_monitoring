# Runbook: Data Collection Recovery

**Last Updated**: 2026-01-15  
**Owner**: Dev Team  
**Severity**: CRITICAL

---

## Quick Reference

**Symptom**: No new ticks in database during market hours  
**Average Resolution Time**: 5-10 minutes  
**Required Access**: SSH to `oracle-a1` server

---

## 🩺 Quick Diagnosis

### Step 1: Check Recent Data

```bash
ssh oracle-a1

# Check last 5 minutes of data
docker exec stock-timescale psql -U postgres -d stockval -c \
  "SELECT COUNT(*) as ticks, MAX(time) as latest \
   FROM market_ticks \
   WHERE time > NOW() - INTERVAL '5 minutes';"
```

**Expected**: 
- During market hours (09:00-15:30 KST): `ticks > 500`, `latest < 2 min ago`
- After hours: `ticks = 0` is normal

**If `ticks = 0` or `latest > 5 min ago`**: Proceed to Step 2

---

### Step 2: Check Collector Status

```bash
# Check if collector is running
docker ps | grep real-collector

# Check recent logs
docker logs real-collector --tail 30
```

**Expected Logs**:
```
✅ WebSocket Connected
📤 PUBLISHED: ticker.kr | 005930 @ 142900.0
📤 PUBLISHED: orderbook.kr | 005930
```

**Problem Indicators**:
- ❌ Container not in `docker ps` output → Go to **Recovery: Collector Down**
- ⚠️  Logs show "WS Connection Error" → Go to **Recovery: Connection Issues**
- ⚠️  Logs show "ALREADY IN SUBSCRIBE" (repeated) → Go to **Recovery: Subscription Issues**

---

### Step 3: Check Archiver Status

```bash
# Check if archiver is running
docker ps | grep timescale-archiver

# Check recent logs
docker logs timescale-archiver --tail 20
```

**Expected Logs**:
```
Flushed 100 ticks to TimescaleDB
Flushed 58 ticks to TimescaleDB
```

**Problem Indicators**:
- ❌ Container not in output → Go to **Recovery: Archiver Down**
- ❌ No "Flushed" logs in last minute → Go to **Recovery: Archiver Stuck**

---

## 🔧 Recovery Procedures

### Recovery: Collector Down

**Symptoms**:
- `docker ps | grep real-collector` returns nothing
- OR Container status shows `Exited`

**Steps**:

```bash
cd ~/workspace/stock_monitoring

# 1. Check why it stopped (optional, for debugging)
docker logs real-collector --tail 100 | grep -E "(ERROR|FATAL|Exception)"

# 2. Restart collector
docker compose -f deploy/docker-compose.yml up -d real-collector

# 3. Wait 30 seconds for connection
sleep 30

# 4. Verify it's publishing
docker logs real-collector --tail 20 | grep "PUBLISHED"
```

**Expected Output**:
```
📤 PUBLISHED: ticker.kr | 005930 @ XX
```

**If still failing**: Escalate (see Escalation section)

---

### Recovery: Archiver Down

**Symptoms**:
- `docker ps | grep timescale-archiver` returns nothing
- Collector is publishing but DB has no new data

**Steps**:

```bash
cd ~/workspace/stock_monitoring

# 1. Check why it stopped
docker logs timescale-archiver --tail 100 2>&1 | grep -E "(ERROR|Exception)"

# 2. Start archiver
docker compose -f deploy/docker-compose.yml up -d timescale-archiver

# 3. Wait 30 seconds
sleep 30

# 4. Verify it's flushing
docker logs timescale-archiver --tail 20 | grep "Flushed"
```

**Expected Output**:
```
INFO:TimescaleArchiver:Flushed 100 ticks to TimescaleDB
```

**If still failing**: Check DB connection (see Advanced Troubleshooting)

---

### Recovery: Connection Issues

**Symptoms**:
- Logs show "WS Connection Error"
- OR "Connection closed"
- OR Repeated reconnect attempts

**Steps**:

```bash
# 1. Check KIS WebSocket endpoint
curl -I http://ops.koreainvestment.com:21000
# Expected: Some response (even error is OK, means endpoint reachable)

# 2. If no response, KIS API might be down
# Contact KIS support or wait for recovery

# 3. If endpoint is up, restart collector
docker compose -f deploy/docker-compose.yml restart real-collector

# 4. Monitor reconnection
docker logs -f real-collector | grep -E "(Connecting|Connected|Error)"
```

**If keeps failing**: May be API key issue → Check `.env` file for valid credentials

---

### Recovery: Subscription Issues

**Symptoms**:
- Logs show repeated "❌ SUBSCRIBE FAILED: XXX - ALREADY IN SUBSCRIBE"
- Some symbols working, others failing

**Cause**: Previous subscription still active on KIS server

**Steps**:

```bash
# 1. Hard restart collector (forces cleanup)
docker compose -f deploy/docker-compose.yml stop real-collector
sleep 5
docker compose -f deploy/docker-compose.yml start real-collector

# 2. Wait 60 seconds for cleanup + reconnect
sleep 60

# 3. Check subscription status
docker logs real-collector --tail 50 | grep -E "(SUBSCRIBE|ALL SUBSCRIBED)"
```

**Expected**:
```
✅ [KR] ALL SUBSCRIBED: 24/24 symbols confirmed
```

**If still seeing errors**: Emergency fix applied (cleanup_subscriptions), should auto-recover. If not, escalate.

---

### Recovery: Archiver Stuck

**Symptoms**:
- Archiver is running
- But no "Flushed" logs
- Redis is receiving data

**Steps**:

```bash
# 1. Check Redis connection
docker exec timescale-archiver python3 -c \
  "import redis; r = redis.Redis(host='stock-redis', port=6379); print(r.ping())"
# Expected: True

# 2. Check DB connection
docker exec timescale-archiver python3 -c \
  "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('postgresql://postgres:password@stock-timescale:5432/stockval'))"
# Expected: No error

# 3. If both work, restart archiver
docker compose -f deploy/docker-compose.yml restart timescale-archiver

#4. Monitor
docker logs -f timescale-archiver | grep "Flushed"
```

---

## ✅ Verification

After any recovery action, **ALWAYS verify**:

### 1. Services Running

```bash
docker ps | grep -E "(real-collector|timescale-archiver)"
```

Expected: Both containers with status "Up X minutes"

---

### 2. Data Flowing

Wait 2 minutes, then:

```bash
docker exec stock-timescale psql -U postgres -d stockval -c \
  "SELECT COUNT(*) as new_ticks \
   FROM market_ticks \
   WHERE time > NOW() - INTERVAL '2 minutes';"
```

**Expected**: `new_ticks > 100` (during market hours)

---

### 3. No Errors

```bash
# Check collector errors
docker logs real-collector --tail 50 | grep -c "ERROR"

# Check archiver errors
docker logs timescale-archiver --tail 50 | grep -c "ERROR"
```

**Expected**: Low count (< 5), ideally 0

---

## 🚨 Escalation

### When to Escalate

Escalate if:
- Recovery steps don't work after 2 attempts
- Services keep crashing repeatedly (> 3 times/hour)
- Data loss > 30 minutes during market hours

### Escalation Path

1. **Slack**: Post in `#stock-monitoring-alerts`
   - Include: Symptom, steps tried, current status
   - Tag: @eng-oncall

2. **Create Incident Ticket**: 
   - Title: `[CRITICAL] Data Collection Down - <Date> <Time>`
   - Include: This runbook steps attempted
   - Attach: Logs (`docker logs real-collector > collector.log`)

3. **If after hours**: 
   - Data loss is acceptable
   - Document in ticket for next day investigation
   - DO NOT wake people up unless data is revenue-critical

---

## 📊 Data Loss Assessment

If recovery took time, assess data loss:

```bash
# Find gap start (last good tick)
docker exec stock-timescale psql -U postgres -d stockval -c \
  "SELECT MAX(time) as gap_start FROM market_ticks;"

# Current time
date

# Calculate gap: current time - gap_start
# Example: If gap_start = 14:08 and now = 14:30
# Data loss = 22 minutes ≈ 2,200 ticks
```

**Data Loss Severity**:
- < 5 min: Low (acceptable during recovery)
- 5-30 min: Medium (document in incident report)
- > 30 min: High (requires backfill)

**Backfill**: TBD (future SOP)

---

## 🔍 Advanced Troubleshooting

### Check Redis Pub/Sub

```bash
# Monitor Redis channels
docker exec -it stock-redis redis-cli

# In redis-cli:
> PSUBSCRIBE ticker.*

# You should see messages like:
# 1) "pmessage"
# 2) "ticker.*"
# 3) "ticker.kr"
# 4) "{...json data...}"
```

If no messages: Collector not publishing → Check collector

---

### Check Database Hypertable

```bash
docker exec stock-timescale psql -U postgres -d stockval -c \
  "SELECT * FROM timescaledb_information.hypertables WHERE hypertable_name = 'market_ticks';"
```

Expected: 1 row returned

If empty: Hypertable not created → Contact DBA

---

### Manual Test: Publisher → DB

```bash
# 1. Publish test message
docker exec stock-redis redis-cli PUBLISH ticker.test \
  '{"symbol":"TEST","price":100}'

# 2. Check if archiver received it (won't save, but should log)
docker logs timescale-archiver --tail 10
```

---

## 📝 Post-Recovery Actions

After recovery, **ALWAYS**:

1. **Document in Incident Log**:
   ```bash
   # Create entry in docs/incidents/
   # Format: YYYY-MM-DD_brief_description.md
   ```

2. **Update Monitoring Log**:
   - Note downtime duration
   - Data loss estimate
   - Recovery actions taken

3. **Check if New Issue**:
   - If failure mode is NEW → Update this runbook
   - If pattern recurring → Notify PM for root cause analysis

---

## 🔗 Related Documents

- **Incident Report**: `docs/incidents/2026-01-15_data_collection_failures.md`
- **Deployment Checklist**: `docs/deployment/CHECKLIST.md`
- **Known Issues**: `docs/KNOWN_ISSUES.md`
- **Architecture**: `docs/ui_design_master.md` (system diagram)

---

## 🔄 Runbook Maintenance

**Review Frequency**: After each incident  
**Update Trigger**: New failure mode encountered  
**Owner**: Developer on-call rotation

**Version History**:
- 2026-01-15: Initial version (based on Jan 14-15 incidents)

---

**Emergency Contact**: [TBD]  
**Runbook Version**: 1.0
