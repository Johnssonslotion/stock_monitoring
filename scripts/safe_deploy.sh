#!/bin/bash

# Configuration
CONTAINER_NAME="history-collector"
LOG_FILE="logs/safe_deploy.log"

# Create logs directory if it doesn't exist
mkdir -p logs

echo "[$(date)] Starting safe deploy watcher..." >> "$LOG_FILE"

# Loop until the container stops
while true; do
    # Check container status
    STATUS=$(docker inspect --format '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null)

    if [ "$STATUS" == "exited" ] || [ -z "$STATUS" ]; then
        echo "[$(date)] Container $CONTAINER_NAME has finished (Status: $STATUS). Proceeding with update." >> "$LOG_FILE"
        break
    else
        echo "[$(date)] Container $CONTAINER_NAME is still $STATUS. Waiting..." >> "$LOG_FILE"
        sleep 60 # Check every minute
    fi
done

# Apply changes
echo "[$(date)] Running 'make up' to apply restart policies..." >> "$LOG_FILE"
cd /home/ubuntu/workspace/stock_monitoring && make up >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "[$(date)] Update successful." >> "$LOG_FILE"
else
    echo "[$(date)] Update FAILED." >> "$LOG_FILE"
fi
