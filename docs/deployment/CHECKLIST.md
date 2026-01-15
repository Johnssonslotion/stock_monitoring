# Deployment Checklist

**Mandatory for ALL deployments**  
**Policy**: No deployment is complete without this checklist ✅  
**Council Decision**: 2026-01-15

---

## 📋 Pre-Deployment

### Code Review
- [ ] PR created and reviewed by at least 1 person
- [ ] All CI/CD checks passed (tests, lint, build)
- [ ] No merge conflicts with target branch

### Testing
- [ ] Unit tests passed locally
- [ ] Integration tests passed (if applicable)
- [ ] Manual testing completed for changed functionality

### Documentation
- [ ] Code changes documented (if public API)
- [ ] CHANGELOG updated (for user-facing changes)
- [ ] Runbook updated (if new failure mode possible)

### Rollback Plan
- [ ] Previous commit hash noted: `________________`
- [ ] Rollback command prepared:
  ```bash
  git checkout <previous_commit>
  docker compose -f deploy/docker-compose.yml up -d --build
  ```
- [ ] Team notified of deployment window

---

## 🚀 Deployment

### 1. Backup Current State

```bash
ssh oracle-a1

# Note current commit
cd ~/workspace/stock_monitoring
git log --oneline -1 > /tmp/pre_deploy_commit.txt

# Backup docker-compose.yml
cp deploy/docker-compose.yml /tmp/docker-compose.yml.backup

# Snapshot running containers
docker ps > /tmp/pre_deploy_containers.txt
```

**Commit before deployment**: `________________`

### 2. Pull Latest Code

```bash
cd ~/workspace/stock_monitoring

# Stash any local changes (should be none)
git stash

# Pull latest
git pull origin develop

# Verify commit hash
git log --oneline -1
```

**Deployed commit**: `________________`

### 3. Build & Deploy

```bash
# Stop affected services (if specific service update)
# docker compose -f deploy/docker-compose.yml stop <service_name>

# OR Full rebuild (safer)
docker compose -f deploy/docker-compose.yml build

# Deploy
docker compose -f deploy/docker-compose.yml up -d
```

**Deployment started at**: `__:__` KST

### 4. Wait for Startup

```bash
# Wait 60 seconds for all services to stabilize
sleep 60
```

---

## ✅ Post-Deployment Verification

### Critical: Service Status Check

```bash
# Check all critical services are running
docker ps | grep -E "(real-collector|timescale-archiver|api-server|stock-redis|stock-timescale)"
```

**Expected**: ALL 5 services with status "Up X seconds/minutes"

- [ ] `real-collector`: Running ✅
- [ ] `timescale-archiver`: Running ✅
- [ ] `api-server`: Running ✅
- [ ] `stock-redis`: Running ✅
- [ ] `stock-timescale`: Running ✅

**If ANY service missing**: STOP → Rollback immediately

---

### Critical: Data Flow Verification

```bash
echo "=== Checking Collector ==="
docker logs real-collector --tail 20 | grep -E "(WebSocket Connected|PUBLISHED)"

echo ""
echo "=== Checking Archiver ==="
docker logs timescale-archiver --tail 20 | grep "Flushed"

echo ""
echo "=== Checking Recent DB Data ==="
docker exec stock-timescale psql -U postgres -d stockval -c \
  "SELECT COUNT(*) as ticks_last_2min, MAX(time) as latest \
   FROM market_ticks \
   WHERE time > NOW() - INTERVAL '2 minutes';"
```

**Expected**:
- Collector: Shows "WebSocket Connected" ✅
- Collector: Shows multiple "PUBLISHED: ticker.kr" messages ✅
- Archiver: Shows "Flushed X ticks to TimescaleDB" ✅
- DB: `ticks_last_2min > 50` (during market hours) ✅
- DB: `latest < 2 minutes ago` ✅

**Checklist**:
- [ ] Collector logs show "WebSocket Connected"
- [ ] Collector logs show recent "PUBLISHED" messages
- [ ] Archiver logs show recent "Flushed" messages
- [ ] Database has recent data (< 2 min old)

**If ANY check fails**: STOP → Investigate before proceeding

---

### API Health Check

```bash
# Check API is responding
curl -s http://localhost:8000/health | jq .

# OR if /health not implemented yet:
curl -s http://localhost:8000/api/v1/symbols | jq '.[:3]'
```

**Expected**: HTTP 200 response with valid JSON

- [ ] API responds successfully ✅

---

### Error Log Review

```bash
# Check for critical errors in last 2 minutes
echo "=== Collector Errors ==="
docker logs real-collector --since 2m 2>&1 | grep -i error | head -10

echo ""
echo "=== Archiver Errors ==="
docker logs timescale-archiver --since 2m 2>&1 | grep -i error | head -10
```

**Expected**: No critical errors (some ALREADY_IN_SUBSCRIBE warnings OK)

- [ ] No critical errors in collector logs
- [ ] No critical errors in archiver logs

---

## 🔄 5-Minute Stability Check

**Wait 5 minutes**, then re-run verification:

```bash
# After 5 minutes, verify continuous data flow
docker exec stock-timescale psql -U postgres -d stockval -c \
  "SELECT COUNT(*) as ticks_last_5min \
   FROM market_ticks \
   WHERE time > NOW() - INTERVAL '5 minutes';"
```

**Expected**: `ticks_last_5min > 200` (during market hours)

- [ ] 5-minute data flow confirmed ✅

**Deployment successful at**: `__:__` KST ✅

---

## ❌ On Failure

### When to Rollback

Rollback immediately if:
- ❌ Any critical service not running after 60s
- ❌ No "WebSocket Connected" in collector logs
- ❌ No data in DB for 5 minutes (during market hours)
- ❌ API returns 5xx errors
- ❌ Critical errors in logs

### Rollback Procedure

```bash
ssh oracle-a1
cd ~/workspace/stock_monitoring

# 1. Stop current deployment
docker compose -f deploy/docker-compose.yml down

# 2. Restore previous commit
git checkout <previous_commit_from_backup>

# 3. Restore docker-compose.yml if changed
cp /tmp/docker-compose.yml.backup deploy/docker-compose.yml

# 4. Rebuild with previous version
docker compose -f deploy/docker-compose.yml build

# 5. Deploy previous version
docker compose -f deploy/docker-compose.yml up -d

# 6. Wait and verify
sleep 60
docker ps
docker logs real-collector --tail 20
```

**Rollback completed at**: `__:__` KST

### After Rollback

- [ ] Notify team in Slack: "#stock-monitoring-alerts"
- [ ] Create incident ticket
- [ ] Document failure in `docs/incidents/`
- [ ] Investigation meeting scheduled

---

## 📊 Post-Deployment Actions

### Required Actions (Always)

- [ ] Update deployment log in `docs/deployment/HISTORY.md`:
  ```markdown
  ## YYYY-MM-DD HH:MM
  - Commit: <hash>
  - Changes: <brief description>
  - Status: SUCCESS / ROLLED_BACK
  - Verification: All checks passed
  ```

- [ ] Monitor for 30 minutes (market hours) or until next market open
- [ ] If issues found: Create incident report

### Smoke Test Execution

Once implemented:

```bash
pytest tests/smoke/test_deployment.py -v
```

Expected: ALL tests pass

---

## 🔒 Deployment Policy Enforcement

### Mandatory Requirements

**Before deployment is considered COMPLETE**:

1. ✅ All Pre-Deployment checks passed
2. ✅ All Post-Deployment verifications passed
3. ✅ 5-minute stability check passed
4. ✅ Deployment logged

**Violation = Deployment REJECTED**

### Deployment Freeze Conditions

Deployment is **NOT ALLOWED** if:
- ❌ Documentation freeze is active (Council decision)
- ❌ Critical incident is ongoing
- ❌ No on-call engineer available
- ❌ During peak market hours (09:00-09:30 KST) without approval

---

## 📝 Checklist Summary

Quick reference for experienced engineers:

```
PRE:
- [ ] Code reviewed, tests passed, docs updated
- [ ] Rollback plan ready
- [ ] Backup current state

DEPLOY:
- [ ] Pull latest code
- [ ] Build & deploy
- [ ] Wait 60s

VERIFY:
- [ ] All services running
- [ ] Collector: WebSocket Connected + Publishing
- [ ] Archiver: Flushing to DB
- [ ] DB: Recent data (< 2min)
- [ ] API: Responding
- [ ] No critical errors
- [ ] Wait 5min stability check

POST:
- [ ] Log deployment
- [ ] Monitor 30min
- [ ] Document if issues
```

---

## 🔗 Related Documents

- **Runbook**: `docs/runbooks/data_collection_recovery.md`
- **Incident Report**: `docs/incidents/2026-01-15_data_collection_failures.md`
- **Monitoring Requirements**: `docs/infrastructure/monitoring_requirements.md`

---

**Checklist Version**: 1.0  
**Last Updated**: 2026-01-15  
**Next Review**: After each deployment failure
