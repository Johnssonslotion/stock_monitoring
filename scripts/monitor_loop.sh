#!/bin/bash
# Automated 5-minute monitoring loop
# Target: Monitor until 01:40 UTC

END_TIME="2026-01-14 01:40:00"
INTERVAL=300  # 5 minutes

echo "=== Monitoring Loop Started at $(date -u +%Y-%m-%d\ %H:%M:%S) ==="
echo "Target End Time: $END_TIME"

while true; do
    CURRENT=$(date -u +%Y-%m-%d\ %H:%M:%S)
    echo ""
    echo "[$CURRENT] Running verification check..."
    
    # Run verification
    python3 /home/ubuntu/workspace/stock_monitoring/scripts/verify_realtime_flow.py
    
    # Check if we've reached end time
    if [[ "$CURRENT" > "$END_TIME" ]] || [[ "$CURRENT" == "$END_TIME" ]]; then
        echo "[$CURRENT] Monitoring complete. Target time reached."
        break
    fi
    
    # Wait 5 minutes
    echo "[$CURRENT] Waiting 5 minutes until next check..."
    sleep $INTERVAL
done

echo "=== Monitoring Loop Ended at $(date -u +%Y-%m-%d\ %H:%M:%S) ==="
