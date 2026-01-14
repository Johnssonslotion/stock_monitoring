#!/bin/bash
# 매시간 데이터 수집 검증 및 자동 복구 스크립트
# Cron: 0 * * * * /home/ubuntu/workspace/stock_monitoring/scripts/hourly_validation.sh

set -e

LOG_FILE="/home/ubuntu/workspace/stock_monitoring/data/validation.log"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

echo "[$TIMESTAMP] Starting hourly validation..." >> "$LOG_FILE"

# 1. 지난 1시간 데이터 수집 확인
DB_COUNT=$(docker exec stock-timescale psql -U postgres -d stockval -t -c \
  "SELECT COUNT(*) FROM market_ticks WHERE time > NOW() - INTERVAL '1 hour';" | tr -d ' ')

echo "[$TIMESTAMP] Collected ticks in last hour: $DB_COUNT" >> "$LOG_FILE"

# 2. Zero-Data 감지 및 자동 복구
if [ "$DB_COUNT" -eq 0 ]; then
  echo "[$TIMESTAMP] 🚨 ZERO DATA ALERT! No data in last 1 hour!" >> "$LOG_FILE"
  
  # Discord Webhook (옵션)
  # DISCORD_WEBHOOK_URL="YOUR_WEBHOOK_URL"
  # curl -X POST "$DISCORD_WEBHOOK_URL" \
  #   -H "Content-Type: application/json" \
  #   -d "{\"content\": \"🚨 ZERO DATA ALERT: No data collected in last hour!\"}"
  
  # Auto-restart
  echo "[$TIMESTAMP] Triggering auto-restart..." >> "$LOG_FILE"
  docker restart real-collector
  
else
  echo "[$TIMESTAMP] ✅ OK: Data collection normal" >> "$LOG_FILE"
fi

# 3. 컨테이너 헬스체크
STATUS=$(docker inspect -f '{{.State.Status}}' real-collector)
RESTARTS=$(docker inspect -f '{{.RestartCount}}' real-collector)

echo "[$TIMESTAMP] Container status: $STATUS, Restarts: $RESTARTS" >> "$LOG_FILE"

# 4. 로그 로테이션 (5000줄 유지)
if [ $(wc -l < "$LOG_FILE") -gt 5000 ]; then
  tail -n 3000 "$LOG_FILE" > "${LOG_FILE}.tmp"
  mv "${LOG_FILE}.tmp" "$LOG_FILE"
fi

echo "[$TIMESTAMP] Validation complete" >> "$LOG_FILE"
