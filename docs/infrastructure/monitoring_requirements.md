# Monitoring Requirements

**Purpose**: Define required monitoring infrastructure to prevent blind operations  
**Owner**: Infrastructure Team  
**Priority**: HIGH (required for production)  
**Council Decision**: 2026-01-15

---

## Executive Summary

Current state: **Flying blind** - no metrics, no alerts, manual SSH checks only.

Required state: **Observable system** - real-time metrics, automated alerts, visual dashboards.

**Without monitoring, we cannot operate a production system.**

---

## 1. Prometheus Metrics

### Required Exporters

#### 1.1 Collector Metrics

**Service**: `real-collector`  
**Port**: 9100 (example)  
**Endpoint**: `/metrics`

**Metrics**:

```python
# Python instrumentation example
from prometheus_client import Counter, Gauge, Histogram

# Service status
collector_status = Gauge(
    'collector_status',
    'Collector running status (1=up, 0=down)'
)

# Subscriptions
collector_subscribed_symbols = Gauge(
    'collector_subscribed_symbols',
    'Number of symbols currently subscribed'
)

# Data flow
collector_ticks_published_total = Counter(
    'collector_ticks_published_total',
    'Total number of ticks published to Redis',
    ['market', 'symbol']  # Labels
)

collector_orderbook_published_total = Counter(
    'collector_orderbook_published_total',
    'Total number of orderbook updates published',
    ['market', 'symbol']
)

# Errors
collector_subscribe_errors_total = Counter(
    'collector_subscribe_errors_total',
    'Total subscription errors',
    ['error_type']  # e.g., 'ALREADY_IN_SUBSCRIBE'
)

# Connection health
collector_websocket_reconnects_total = Counter(
    'collector_websocket_reconnects_total',
    'Total WebSocket reconnections'
)

collector_last_tick_timestamp = Gauge(
    'collector_last_tick_timestamp',
    'Unix timestamp of last published tick'
)
```

---

#### 1.2 Archiver Metrics

**Service**: `timescale-archiver`  
**Port**: 9101 (example)  
**Endpoint**: `/metrics`

**Metrics**:

```python
# Service status
archiver_status = Gauge(
    'archiver_status',
    'Archiver running status (1=up, 0=down)'
)

# Data flow
archiver_ticks_flushed_total = Counter(
    'archiver_ticks_flushed_total',
    'Total number of ticks flushed to database'
)

archiver_orderbook_flushed_total = Counter(
    'archiver_orderbook_flushed_total',
    'Total orderbook updates flushed'
)

# Buffer health
archiver_buffer_size = Gauge(
    'archiver_buffer_size',
    'Current number of items in flush buffer'
)

archiver_last_flush_timestamp = Gauge(
    'archiver_last_flush_timestamp',
    'Unix timestamp of last successful flush'
)

# Flush performance
archiver_flush_duration_seconds = Histogram(
    'archiver_flush_duration_seconds',
    'Time taken to flush batch to database'
)

# Errors
archiver_flush_errors_total = Counter(
    'archiver_flush_errors_total',
    'Total database flush errors'
)
```

---

#### 1.3 Database Metrics

**Service**: `stock-timescale`  
**Exporter**: postgres-exporter (use existing Docker image)  

**Key Metrics** (automatically provided):
- `pg_stat_database_tup_inserted` - Rows inserted
- `pg_stat_database_tup_updated` - Rows updated
- `pg_database_size_bytes` - Database size

**Custom Metrics** (via SQL queries):

```sql
-- Query for recent tick count
SELECT COUNT(*) FROM market_ticks 
WHERE time > NOW() - INTERVAL '1 minute';

-- Export as: db_ticks_last_1min

-- Query for recent tick count (5min)
SELECT COUNT(*) FROM market_ticks 
WHERE time > NOW() - INTERVAL '5 minutes';

-- Export as: db_ticks_last_5min
```

---

### Prometheus Configuration

**File**: `deploy/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'real-collector'
    static_configs:
      - targets: ['real-collector:9100']
  
  - job_name: 'timescale-archiver'
    static_configs:
      - targets: ['timescale-archiver:9101']
  
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
```

---

## 2. Alertmanager Rules

**File**: `deploy/prometheus/alerts.yml`

### Critical Alerts

#### Alert 1: Collector Down

```yaml
- alert: CollectorDown
  expr: collector_status == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Real-time collector is DOWN!"
    description: "Collector has been down for 1 minute. No new data is being collected."
    runbook: "docs/runbooks/data_collection_recovery.md#recovery-collector-down"
```

**Action**: Immediate page to on-call engineer

---

#### Alert 2: Archiver Down

```yaml
- alert: ArchiverDown
  expr: archiver_status == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Archiver is DOWN!"
    description: "Archiver has been down for 1 minute. Data is being lost."
    runbook: "docs/runbooks/data_collection_recovery.md#recovery-archiver-down"
```

**Action**: Immediate page to on-call engineer

---

#### Alert 3: No Data Flow

```yaml
- alert: NoDataFlow
  expr: rate(archiver_ticks_flushed_total[5m]) == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "No data flowing to database!"
    description: "No ticks have been flushed to DB in 2 minutes during market hours."
    runbook: "docs/runbooks/data_collection_recovery.md"
```

**Action**: Immediate investigation

---

#### Alert 4: Market Hours Data Gap

```yaml
- alert: MarketHoursDataGap
  expr: |
    (hour() >= 9 AND hour() < 16) AND
    rate(archiver_ticks_flushed_total[5m]) < 10
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Low data rate during market hours"
    description: "Only {{ $value }} ticks/sec during market hours (expected ~50)"
```

**Action**: Investigate within 10 minutes

---

### Warning Alerts

#### Alert 5: High Subscribe Error Rate

```yaml
- alert: HighSubscribeErrorRate
  expr: rate(collector_subscribe_errors_total[5m]) > 0.5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High rate of subscription errors"
    description: "Collector is experiencing {{ $value }} subscription errors/sec"
```

**Action**: Monitor, may indicate API issues

---

#### Alert 6: Frequent Reconnects

```yaml
- alert: FrequentReconnects
  expr: rate(collector_websocket_reconnects_total[10m]) > 0.1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Frequent WebSocket reconnections"
    description: "Collector is reconnecting {{ $value }} times/sec"
```

**Action**: Investigate network or API stability

---

#### Alert 7: Database Growing Too Fast

```yaml
- alert: DatabaseGrowthAnomalous
  expr: |
    rate(pg_database_size_bytes{datname="stockval"}[1h]) > 
    avg_over_time(rate(pg_database_size_bytes{datname="stockval"}[1h])[7d:]) * 2
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "Database growing 2x faster than normal"
    description: "May indicate data duplication or logging issue"
```

**Action**: Investigate data quality

---

## 3. Grafana Dashboard

### Dashboard: "Stock Monitoring - Data Pipeline"

**Panels**:

#### Panel 1: Service Health (Top Row)

- **Type**: Stat (gauge)
- **Metrics**: 
  - `collector_status` (1=green, 0=red)
  - `archiver_status` (1=green, 0=red)
- **Thresholds**: 1=green, 0=red

#### Panel 2: Data Flow Rate (Second Row)

- **Type**: Graph (time series)
- **Metrics**:
  - `rate(collector_ticks_published_total[1m])` (blue line)
  - `rate(archiver_ticks_flushed_total[1m])` (green line)
- **Y-axis**: Ticks per second
- **Expected**: ~50-100 ticks/sec during market hours

#### Panel 3: Recent DB Data (Second Row)

- **Type**: Stat (single value)
- **Query**: Custom SQL via postgres-exporter
  ```sql
  SELECT COUNT(*) FROM market_ticks 
  WHERE time > NOW() - INTERVAL '5 minutes'
  ```
- **Thresholds**: < 100 = red, < 500 = yellow, >= 500 = green

#### Panel 4: Error Rates (Third Row)

- **Type**: Graph
- **Metrics**:
  - `rate(collector_subscribe_errors_total[5m])` by `error_type`
  - `rate(archiver_flush_errors_total[5m])`

#### Panel 5: Buffer & Performance (Bottom Row)

- **Type**: Graph
- **Metrics**:
  - `archiver_buffer_size`
  - `archiver_flush_duration_seconds` (histogram)

#### Panel 6: Subscribed Symbols (Bottom Row)

- **Type**: Stat
- **Metric**: `collector_subscribed_symbols`
- **Expected**: 24 (KR market)

---

### Dashboard JSON

Template: `deploy/grafana/dashboards/data-pipeline.json`

---

## 4. Health Check Endpoints

### 4.1 Collector Health Check

**Endpoint**: `GET /health/collector`  
**Implementation**: Add to `real-collector` service

```python
# In unified_collector.py or new health module

from fastapi import FastAPI
import time

app = FastAPI()

@app.get("/health/collector")
async def collector_health():
    return {
        "status": "healthy" if manager.websocket else "unhealthy",
        "uptime_seconds": int(time.time() - manager.start_time),
        "subscribed_symbols": len(manager.active_markets) * 24,  # Example
        "last_tick_ago_seconds": int(time.time() - manager.last_traffic_time),
        "websocket_connected": manager.websocket is not None,
        "error_count_1h": manager.error_counter.get_count_last_hour()
    }
```

**Response Example**:
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "subscribed_symbols": 24,
  "last_tick_ago_seconds": 2,
  "websocket_connected": true,
  "error_count_1h": 3
}
```

---

### 4.2 Archiver Health Check

**Endpoint**: `GET /health/archiver`

```python
@app.get("/health/archiver")
async def archiver_health():
    return {
        "status": "healthy" if archiver.running else "unhealthy",
        "buffer_size": len(archiver.buffer),
        "last_flush_ago_seconds": int(time.time() - archiver.last_flush_time),
        "total_flushed": archiver.total_flushed_count,
        "db_connected": await archiver.check_db_connection()
    }
```

---

### 4.3 API Server Health Check

**Endpoint**: `GET /health`  
**Already exists in**: `src/api/main.py`

Enhance to include:
```python
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "services": {
            "redis": await check_redis(),
            "database": await check_database(),
            "collector": await check_collector_health(),  # NEW
            "archiver": await check_archiver_health()     # NEW
        },
        "timestamp": datetime.now(pytz.timezone('Asia/Seoul')).isoformat()
    }
```

---

## 5. Implementation Priority

### Phase 1: Immediate (This Week)

1. ✅ Health check endpoints (collector, archiver)
2. ✅ Basic Prometheus exporters (service status, tick counts)
3. ✅ Critical alerts (Collector Down, Archiver Down, No Data Flow)

### Phase 2: Short-term (Next Week)

4. ✅ Grafana dashboard (basic data flow visualization)
5. ✅ Alertmanager integration (Slack notifications)
6. ✅ Warning alerts (high error rates, reconnects)

### Phase 3: Long-term (This Month)

7. ✅ Advanced metrics (performance histograms, per-symbol stats)
8. ✅ Data quality dashboard
9. ✅ Historical analysis tools

---

## 6. Alert Routing

**Alertmanager Config**: `deploy/alertmanager/config.yml`

```yaml
route:
  receiver: 'slack-critical'
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  
  routes:
    - match:
        severity: critical
      receiver: slack-critical
      continue: true
    
    - match:
        severity: warning
      receiver: slack-warnings

receivers:
  - name: 'slack-critical'
    slack_configs:
      - api_url: '<WEBHOOK_URL>'
        channel: '#stock-monitoring-alerts'
        title: '🚨 CRITICAL: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
  
  - name: 'slack-warnings'
    slack_configs:
      - api_url: '<WEBHOOK_URL>'
        channel: '#stock-monitoring-warnings'
        title: '⚠️  WARNING: {{ .GroupLabels.alertname }}'
```

---

## 7. Acceptance Criteria

**Monitoring is considered COMPLETE when**:

- ✅ All critical metrics are being collected
- ✅ All critical alerts are configured
- ✅ Grafana dashboard displays real-time data
- ✅ Health check endpoints return 200
- ✅ Test alert successfully sent to Slack
- ✅ Documentation updated with runbook links

**Until then, system is NOT production-ready.**

---

## 8. Related Documents

- **Runbook**: `docs/runbooks/data_collection_recovery.md`
- **Incident Report**: `docs/incidents/2026-01-15_data_collection_failures.md`
- **Deployment Checklist**: `docs/deployment/CHECKLIST.md`

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-15  
**Owner**: Infrastructure Team  
**Review**: After each monitoring gap discovered
