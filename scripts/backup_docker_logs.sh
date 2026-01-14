#!/bin/bash
# Docker 로그 일일 백업 스크립트
# 장애 발생 시 재실험을 위해 로그 보관

LOG_DIR="/home/ubuntu/workspace/stock_monitoring/logs/docker"
DATE=$(date +%Y%m%d)

mkdir -p "$LOG_DIR"

# real-collector 로그 저장
echo "Saving real-collector logs..."
docker logs real-collector > "$LOG_DIR/real-collector_$DATE.log" 2>&1

# history-collector 로그 저장
echo "Saving history-collector logs..."
docker logs history-collector > "$LOG_DIR/history-collector_$DATE.log" 2>&1

# timescale-archiver 로그 저장
echo "Saving timescale-archiver logs..."
docker logs timescale-archiver > "$LOG_DIR/timescale-archiver_$DATE.log" 2>&1

# 7일 이상 된 로그 삭제
find "$LOG_DIR" -name "*.log" -mtime +7 -delete

echo "Log backup completed: $LOG_DIR/*_$DATE.log"
