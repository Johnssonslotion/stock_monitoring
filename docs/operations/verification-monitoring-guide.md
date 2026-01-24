# Verification System Monitoring Guide

## Overview

The verification-worker auto-recovery system includes 6 SQL views for real-time monitoring and health tracking.

**Database**: `stockval` (TimescaleDB)  
**Base Table**: `market_verification_results`

---

## Quick Start

### Check Overall System Health

```sql
-- Single metric for system health (last 7 days)
SELECT * FROM verification_health_score;
```

**Output**:
- `pass_rate_pct`: Percentage of successful verifications
- `gap_rate_pct`: Percentage triggering recovery
- `health_status`: HEALTHY (≥99%) | GOOD (≥95%) | FAIR (≥90%) | NEEDS_ATTENTION (<90%)

**Action**: If `health_status = 'NEEDS_ATTENTION'`, investigate high gap rate symbols.

---

## Monitoring Views Reference

### 1. verification_health_score
**Purpose**: Single-metric health dashboard  
**Time Window**: Last 7 days

```sql
SELECT * FROM verification_health_score;
```

**Key Metrics**:
- `total_checks_7d`: Total verifications performed
- `pass_rate_pct`: Success rate
- `gap_rate_pct`: Recovery trigger rate
- `error_rate_pct`: System error rate
- `symbols_checked`: Number of unique symbols

**Alert Thresholds**:
- ⚠️ Warning: `gap_rate_pct > 1.0%`
- 🚨 Critical: `gap_rate_pct > 5.0%`

---

### 2. verification_daily_summary
**Purpose**: Daily aggregated statistics  
**Time Window**: All historical data, grouped by day

```sql
-- Last 7 days
SELECT * FROM verification_daily_summary 
ORDER BY date DESC LIMIT 7;
```

**Columns**:
- `date`: Trading date
- `total_verifications`: Total checks performed
- `passed`: Successful verifications
- `gaps_detected`: Triggered recoveries
- `errors`: System errors
- `no_data`: API returned empty data
- `avg_delta_pct`: Average volume delta
- `max_delta_pct`: Maximum delta (worst case)
- `gap_rate_pct`: Daily gap detection rate

**Use Case**: Identify days with high gap rates.

---

### 3. verification_gap_rate
**Purpose**: Per-symbol gap detection rates  
**Time Window**: Last 7 days

```sql
-- High gap rate symbols
SELECT * FROM verification_gap_rate 
WHERE gap_rate_pct > 5.0
ORDER BY gap_rate_pct DESC;
```

**Columns**:
- `symbol`: Stock symbol (e.g., 005930)
- `total_checks`: Total verifications for this symbol
- `gaps_found`: Number of gaps detected
- `passed`: Successful checks
- `gap_rate_pct`: Gap percentage for this symbol
- `avg_delta_pct`: Average volume delta
- `last_checked`: Most recent verification time

**Use Case**: Identify symbols with persistent data quality issues.

**Action Items**:
- Gap rate > 10%: Check WebSocket connection for this symbol
- Gap rate > 20%: Consider switching provider (Kiwoom → KIS)

---

### 4. verification_recent
**Purpose**: Real-time activity monitoring  
**Time Window**: Last 24 hours

```sql
-- Recent gaps detected
SELECT * FROM verification_recent 
WHERE status = 'NEEDS_RECOVERY'
ORDER BY created_at DESC;

-- Recent errors
SELECT * FROM verification_recent 
WHERE status = 'ERROR'
ORDER BY created_at DESC;
```

**Columns**:
- `time`: Target minute being verified
- `symbol`: Stock symbol
- `status`: PASS | NEEDS_RECOVERY | ERROR | NO_DATA_KIS | NO_DATA_KIWOOM
- `kis_vol`: KIS API volume
- `kiwoom_vol`: Kiwoom API volume
- `delta_pct`: Volume delta percentage
- `created_at`: When verification was performed
- `processing_delay_sec`: Time between target minute and verification

**Use Case**: Real-time monitoring dashboard, alerting.

**Alert Example**:
```sql
-- Check if processing is lagging
SELECT COUNT(*) as delayed_checks 
FROM verification_recent 
WHERE processing_delay_sec > 600;  -- More than 10 minutes delayed
```

---

### 5. verification_hourly
**Purpose**: Hourly pattern analysis  
**Time Window**: Last 7 days, grouped by hour

```sql
-- Today's hourly activity
SELECT * FROM verification_hourly 
WHERE date = CURRENT_DATE
ORDER BY hour;

-- Peak gap hours
SELECT hour, AVG(gaps) as avg_gaps
FROM verification_hourly
GROUP BY hour
ORDER BY avg_gaps DESC;
```

**Columns**:
- `date`: Trading date
- `hour`: Hour of day (0-23)
- `checks_count`: Verifications in this hour
- `passed`: Successful checks
- `gaps`: Gaps detected
- `avg_delta_pct`: Average delta percentage
- `unique_symbols`: Symbols checked

**Use Case**: Identify problematic time periods (e.g., market open, lunch break).

---

### 6. verification_recovery_performance
**Purpose**: Track recovery task effectiveness  
**Time Window**: Last 30 days

```sql
-- Recovery success rate
SELECT * FROM verification_recovery_performance
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY date DESC;

-- Overall recovery stats
SELECT 
    SUM(gaps_detected) as total_gaps,
    SUM(ticks_recovered) as total_recoveries,
    ROUND(100.0 * SUM(ticks_recovered) / NULLIF(SUM(gaps_detected), 0), 2) as overall_success_rate
FROM verification_recovery_performance
WHERE date >= CURRENT_DATE - INTERVAL '30 days';
```

**Columns**:
- `date`: Trading date
- `gaps_detected`: Number of NEEDS_RECOVERY statuses
- `ticks_recovered`: Number of ticks saved via KIS_RECOVERY
- `recovery_success_rate_pct`: Success rate percentage
- `symbols_with_gaps`: List of symbols with gaps

**Use Case**: Measure auto-recovery system effectiveness.

**Target Metric**: `recovery_success_rate_pct >= 95%`

---

## Common Monitoring Queries

### Daily Health Check
```sql
-- Run every morning after market close
SELECT 
    h.health_status,
    h.pass_rate_pct,
    h.gap_rate_pct,
    d.date,
    d.total_verifications,
    d.gaps_detected
FROM verification_health_score h
CROSS JOIN LATERAL (
    SELECT * FROM verification_daily_summary 
    WHERE date = CURRENT_DATE
) d;
```

### High Gap Rate Alert
```sql
-- Symbols requiring attention
SELECT 
    symbol,
    gap_rate_pct,
    total_checks,
    avg_delta_pct,
    last_checked
FROM verification_gap_rate
WHERE gap_rate_pct > 5.0
ORDER BY gap_rate_pct DESC;
```

### Recovery Performance Report
```sql
-- Weekly recovery summary
SELECT 
    date_trunc('week', date) as week,
    SUM(gaps_detected) as total_gaps,
    SUM(ticks_recovered) as total_recoveries,
    ROUND(AVG(recovery_success_rate_pct), 2) as avg_success_rate
FROM verification_recovery_performance
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY date_trunc('week', date)
ORDER BY week DESC;
```

### Real-Time Gap Detection
```sql
-- Gaps detected in last hour
SELECT 
    time,
    symbol,
    delta_pct,
    kis_vol,
    kiwoom_vol
FROM verification_recent
WHERE status = 'NEEDS_RECOVERY'
    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
ORDER BY created_at DESC;
```

---

## Grafana Dashboard Integration

### Recommended Panels

#### 1. Health Score Gauge
```sql
SELECT health_status, pass_rate_pct 
FROM verification_health_score;
```
**Panel Type**: Gauge  
**Thresholds**: Red (0-90), Yellow (90-95), Green (95-100)

#### 2. Daily Gap Rate Trend
```sql
SELECT date, gap_rate_pct 
FROM verification_daily_summary 
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY date;
```
**Panel Type**: Time Series  
**Y-Axis**: Gap Rate %

#### 3. Top Problematic Symbols
```sql
SELECT symbol, gap_rate_pct 
FROM verification_gap_rate 
ORDER BY gap_rate_pct DESC LIMIT 10;
```
**Panel Type**: Bar Chart

#### 4. Hourly Pattern Heatmap
```sql
SELECT date, hour, gaps 
FROM verification_hourly
WHERE date >= CURRENT_DATE - INTERVAL '7 days';
```
**Panel Type**: Heatmap

#### 5. Recovery Success Rate
```sql
SELECT date, recovery_success_rate_pct 
FROM verification_recovery_performance
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY date;
```
**Panel Type**: Time Series  
**Target Line**: 95%

---

## Alert Rules

### Critical Alerts

#### Gap Rate Above 5%
```sql
-- Alert condition
SELECT COUNT(*) > 0 as alert
FROM verification_health_score
WHERE gap_rate_pct > 5.0;
```
**Action**: Investigate WebSocket connections, check provider APIs

#### Recovery Success Rate Below 90%
```sql
-- Alert condition
SELECT recovery_success_rate_pct < 90.0 as alert
FROM verification_recovery_performance
WHERE date = CURRENT_DATE;
```
**Action**: Check API Hub worker logs, verify KIS API credentials

#### Error Rate Above 10%
```sql
-- Alert condition
SELECT error_rate_pct > 10.0 as alert
FROM verification_health_score;
```
**Action**: Check verification-worker logs, verify DB connectivity

### Warning Alerts

#### Processing Delay > 10 Minutes
```sql
-- Alert condition
SELECT COUNT(*) > 5 as alert
FROM verification_recent
WHERE processing_delay_sec > 600;
```
**Action**: Check queue backlog, consider scaling workers

#### Single Symbol Gap Rate > 20%
```sql
-- Alert condition
SELECT COUNT(*) > 0 as alert
FROM verification_gap_rate
WHERE gap_rate_pct > 20.0;
```
**Action**: Investigate specific symbol data quality

---

## Maintenance

### View Refresh
Views are automatically updated as new data is inserted into `market_verification_results`.

### Performance Optimization
```sql
-- Rebuild indexes (monthly)
REINDEX TABLE market_verification_results;

-- Update table statistics (weekly)
ANALYZE market_verification_results;
```

### Data Retention
```sql
-- Delete old verification results (keep 90 days)
DELETE FROM market_verification_results
WHERE created_at < CURRENT_DATE - INTERVAL '90 days';
```

---

## Troubleshooting

### No Data in Views
```sql
-- Check if base table has data
SELECT COUNT(*), MIN(time), MAX(time) 
FROM market_verification_results;
```

### Views Return Errors
```sql
-- Recreate views
\i migrations/008_add_verification_monitoring_views.sql
```

### Slow Query Performance
```sql
-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE tablename = 'market_verification_results'
ORDER BY idx_scan;
```

---

## Related Documentation

- [RFC-008: Tick Completeness QA](../governance/rfc/RFC-008-tick-completeness-qa.md)
- [Verification Worker Architecture](../architecture/verification-worker.md)
- [API Hub Integration Guide](../operations/api-hub-guide.md)
