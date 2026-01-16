#!/bin/bash

# Configuration
REMOTE_HOST="oracle-a1"          # Name in ~/.ssh/config or user@ip
LOCAL_API_PORT=8000
REMOTE_API_PORT=8000
LOCAL_DB_PORT=5433
REMOTE_DB_PORT=5432

# ANSI Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🔌 Checking SSH Tunnel status for Stock Monitoring..."

# Check if port 8000 is already in use by ssh
PID=$(lsof -ti :$LOCAL_API_PORT -sTCP:LISTEN)

if [ -n "$PID" ]; then
    # Check if it's actually SSH
    PROCESS_NAME=$(ps -p $PID -o comm=)
    if [[ "$PROCESS_NAME" == *"ssh"* ]]; then
        echo -e "${GREEN}✅ Tunnel is ALREADY ACTIVE (PID: $PID)${NC}"
        echo "   - API: http://localhost:$LOCAL_API_PORT -> Remote:$REMOTE_API_PORT"
        echo "   - DB : localhost:$LOCAL_DB_PORT -> Remote:$REMOTE_DB_PORT"
        exit 0
    else
        echo -e "${RED}⚠️  Port $LOCAL_API_PORT is in use by '$PROCESS_NAME', not SSH!${NC}"
        echo "   Please terminate that process first."
        exit 1
    fi
fi

# Establish Tunnel
echo "🚀 Establishing new SSH Tunnel to $REMOTE_HOST..."
echo "   - Forwarding API: $LOCAL_API_PORT -> $REMOTE_API_PORT"
echo "   - Forwarding DB : $LOCAL_DB_PORT -> $REMOTE_DB_PORT"

# Run in background (-f), no command (-N)
ssh -L $LOCAL_API_PORT:localhost:$REMOTE_API_PORT \
    -L $LOCAL_DB_PORT:localhost:$REMOTE_DB_PORT \
    -f -N $REMOTE_HOST

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Tunnel SUCCESSFULLY ESTABLISHED!${NC}"
    echo "   You can now access the dashboard or database localy."
else
    echo -e "${RED}❌ Failed to establish tunnel.${NC} Check your SSH config or network."
    exit 1
fi
