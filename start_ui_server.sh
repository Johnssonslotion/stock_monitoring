#!/bin/bash
# UI 서버 시작 스크립트

cd /Users/bbagsang-u/workspace/stock_monitoring/src/web

echo "🚀 Starting Vite Dev Server..."
VITE_API_TARGET=http://localhost:8000 npm run dev > /tmp/vite_server.log 2>&1 &
PID=$!

echo "Process ID: $PID"
echo $PID > /tmp/vite_server.pid

sleep 3

if ps -p $PID > /dev/null; then
    echo "✅ Server started successfully"
    echo "📍 URL: http://localhost:5173/"
    echo "📜 Logs: tail -f /tmp/vite_server.log"
    echo "🛑 Stop: kill \$(cat /tmp/vite_server.pid)"
else
    echo "❌ Server failed to start"
    cat /tmp/vite_server.log
    exit 1
fi
