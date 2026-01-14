#!/bin/bash
# 5분 간격 데이터 수집 검증 스크립트
# 1시간 연속 수집 성공 목표 (12회 검증)

set -e

LOG_FILE="/home/ubuntu/workspace/stock_monitoring/data/5min_validation.log"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
CHECK_NUM=$1  # 1~12

echo "========================================" >> "$LOG_FILE"
echo "[$TIMESTAMP] Check #$CHECK_NUM - Starting..." >> "$LOG_FILE"

# 1. Collector 상태 확인
STATUS=$(docker inspect -f '{{.State.Status}}' real-collector)
UPTIME=$(docker inspect -f '{{.State.StartedAt}}' real-collector)
echo "  Container: $STATUS (Started: $UPTIME)" >> "$LOG_FILE"

# 2. 지난 5분 Tick 데이터 확인
TICK_COUNT=$(docker exec stock-timescale psql -U postgres -d stockval -t -c \
  "SELECT COUNT(*) FROM market_ticks WHERE time > NOW() - INTERVAL '5 minutes';" | tr -d ' ')

echo "  Tick Count (5min): $TICK_COUNT" >> "$LOG_FILE"

# 3. 지난 5분 Orderbook 데이터 확인
ORDERBOOK_COUNT=$(docker exec stock-timescale psql -U postgres -d stockval -t -c \
  "SELECT COUNT(*) FROM market_orderbook WHERE time > NOW() - INTERVAL '5 minutes';" | tr -d ' ')

echo "  Orderbook Count (5min): $ORDERBOOK_COUNT" >> "$LOG_FILE"

# 4. 최신 Tick 데이터 샘플
LATEST_TICK=$(docker exec stock-timescale psql -U postgres -d stockval -t -c \
  "SELECT symbol, price, volume, time FROM market_ticks ORDER BY time DESC LIMIT 1;")

echo "  Latest Tick: $LATEST_TICK" >> "$LOG_FILE"

# 5. Redis 키 확인
REDIS_KEYS=$(docker exec stock-redis redis-cli KEYS "*" | wc -l)
echo "  Redis Keys: $REDIS_KEYS" >> "$LOG_FILE"

# 6. 성공/실패 판정
if [ "$TICK_COUNT" -gt 0 ] && [ "$ORDERBOOK_COUNT" -gt 0 ]; then
  echo "  ✅ CHECK #$CHECK_NUM PASSED (Tick: $TICK_COUNT, Orderbook: $ORDERBOOK_COUNT)" >> "$LOG_FILE"
  echo "✅ Check $CHECK_NUM: SUCCESS"
  exit 0
elif [ "$TICK_COUNT" -gt 0 ]; then
  echo "  ⚠️  CHECK #$CHECK_NUM PARTIAL (Tick OK, Orderbook 0)" >> "$LOG_FILE"
  echo "⚠️  Check $CHECK_NUM: PARTIAL SUCCESS (Tick only)"
  exit 1
else
  echo "  ❌ CHECK #$CHECK_NUM FAILED (Both Zero)" >> "$LOG_FILE"
  echo "❌ Check $CHECK_NUM: FAILED"
  
  # 로그 확인
  echo "  Last 10 collector logs:" >> "$LOG_FILE"
  docker logs --tail 10 real-collector >> "$LOG_FILE" 2>&1
  
  exit 2
fi
