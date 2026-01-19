# Runbook: Common Collector Failures

## Purpose
Quick reference guide for diagnosing and resolving common data collection failures.

---

## 🔴 Emergency Procedures

### Container Won't Start - ImportError

**Symptoms**:
- Container restarts continuously
- Logs show `ImportError` or `ModuleNotFoundError`

**Diagnosis**:
```bash
docker logs <container-name> --tail 50
```

**Solutions**:
1. **Check for missing function**: Search codebase for the missing import
   ```bash
   grep -r "def get_redis_connection" src/
   ```

2. **Rebuild Docker image** (dependencies changed):
   ```bash
   docker compose -f deploy/docker-compose.yml build --no-cache <service-name>
   ```

3. **Verify pyproject.toml** has all dependencies:
   ```bash
   cat pyproject.toml | grep -A 20 dependencies
   ```

---

### WebSocket Connection Unstable

**Symptoms**:
- Logs show: `no close frame received or sent`
- Frequent reconnections (every 3-5 seconds)
- Data gaps in TimescaleDB

**Diagnosis**:
```bash
docker logs <kis-service|kiwoom-service> | grep "ERROR\\|reconnect"
```

**Solutions**:
1. **Check heartbeat configuration** in `websocket_dual.py`:
   - `ping_interval` should be 20-30 seconds
   - `ping_timeout` should be 10 seconds

2. **Verify API server status**:
   - KIS: Check https://openapi.koreainvestment.com status
   - Kiwoom: Check API server connectivity

3. **Check network latency**:
   ```bash
   ping ops.koreainvestment.com
   ```

4. **Reduce subscription load** (too many symbols):
   - Limit to 100 symbols per collector
   - Use symbol sharding across multiple collectors

---

### OOM Kill (Exit 137)

**Symptoms**:
- Container stops with exit code 137
- `docker ps -a` shows `Exited (137)`
- System logs show OOM killer messages

**Diagnosis**:
```bash
docker stats <container-name>  # Real-time memory usage
dmesg | grep -i kill            # System OOM killer logs
```

**Solutions**:
1. **Increase memory limit** in `deploy/docker-compose.yml`:
   ```yaml
   deploy:
     resources:
       limits:
         memory: 2G  # Increase as needed
   ```

2. **Check for memory leaks**:
   - Monitor memory growth over time
   - Review raw logger buffer settings
   - Verify WebSocket message cleanup

3. **Add memory reservation**:
   ```yaml
   deploy:
     resources:
       reservations:
         memory: 512M
   ```

---

### Recovery Worker Failing

**Symptoms**:
- Data gaps not being filled
- Recovery worker crashes on startup

**Diagnosis**:
```bash
docker logs recovery-worker --tail 100
```

**Common Issues**:
1. **Missing httpx dependency**:
   - Solution: Rebuild Docker image (httpx in pyproject.toml)

2. **Database connection failure**:
   - Check `DB_HOST`, `DB_PORT`, `DB_PASSWORD` env vars
   - Verify TimescaleDB is running:
     ```bash
     docker ps | grep timescale
     ```

3. **API key expired**:
   - Check KIS/Kiwoom API key validity
   - Refresh tokens if needed

---

## 🟡 Warning Scenarios

### High Memory Usage (Not OOM)

**Action**:
1. Monitor with `docker stats`
2. Check raw logger file sizes:
   ```bash
   du -sh data/raw/*
   ```
3. Adjust retention hours:
   ```python
   RawWebSocketLogger(retention_hours=24)  # Reduce from 48/120
   ```

---

### Redis Connection Timeout

**Symptoms**:
- `REDIS_URL` connection errors
- Data not publishing to channels

**Solutions**:
1. Check Redis is running:
   ```bash
   docker ps | grep redis
   redis-cli ping
   ```

2. Verify REDIS_URL in env:
   ```bash
   grep REDIS_URL .env.prod
   ```

3. Test connection:
   ```bash
   docker exec -it stock-redis redis-cli
   > PING
   PONG
   ```

---

## 📋 Pre-Flight Checklist

Run before market open (08:30 KST):

```bash
# 1. Pre-flight health check
python scripts/preflight_check.py

# 2. Check disk space
df -h

# 3. Check container status
docker ps -a

# 4. Check logs for recent errors
docker logs kis-service --since 1h | grep ERROR
docker logs kiwoom-service --since 1h | grep ERROR

# 5. Verify Redis
redis-cli ping

# 6. Verify TimescaleDB
docker exec stock-timescale psql -U postgres -d stockval -c "SELECT version();"

# 7. Check API keys (KIS)
curl -X POST "https://openapi.koreainvestment.com/oauth2/tokenP" \
  -H "content-type: application/json" \
  -d "{\"grant_type\":\"client_credentials\",\"appkey\":\"$KIS_APP_KEY\",\"appsecret\":\"$KIS_APP_SECRET\"}"
```

---

## 📞 Escalation

If issues persist after following runbook:

1. **Check system resources**:
   ```bash
   top
   free -h
   df -h
   ```

2. **Collect diagnostic bundle**:
   ```bash
   mkdir -p /tmp/diagnostics
   docker logs kis-service > /tmp/diagnostics/kis.log
   docker logs kiwoom-service > /tmp/diagnostics/kiwoom.log
   docker logs recovery-worker > /tmp/diagnostics/recovery.log
   docker stats --no-stream > /tmp/diagnostics/stats.txt
   ```

3. **Review failure analysis document**:
   - `docs/ideas/stock_monitoring/ID-2026-01-19-collection-failure.md`

4. **Check related issues**:
   - `docs/issues/ISSUE-004-market-open-failure.md`

---

**Last Updated**: 2026-01-19  
**Maintainer**: DevOps Team  
**Related**: CHANGELOG-2026-01-19.md, preflight_check.py
