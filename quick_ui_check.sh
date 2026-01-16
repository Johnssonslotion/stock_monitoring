#!/bin/bash
# Quick UI Validation Script
# Phase 14 - Docker Compose Environment

echo "🔍 Antigravity UI Quick Check"
echo "=============================="
echo ""

# Check Backend
echo "📡 Backend Status:"
echo "  Redis:       $(docker ps --filter name=stock-redis --format '{{.Status}}' | grep -q Up && echo '✅ Running' || echo '❌ Stopped')"
echo "  TimescaleDB: $(docker ps --filter name=stock-timescale --format '{{.Status}}' | grep -q Up && echo '✅ Running' || echo '❌ Stopped')"
echo "  API Server:  $(docker ps --filter name=api-server --format '{{.Status}}' | grep -q Up && echo '✅ Running' || echo '❌ Stopped')"
echo ""

# Check API Health
echo "🏥 API Health Check:"
health_response=$(curl -s http://localhost:8000/api/v1/health)
if echo "$health_response" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
    echo "  Status: ✅ Healthy"
    echo "  DB:     $(echo "$health_response" | jq -r '.db.connected') ($(echo "$health_response" | jq -r '.db.response_ms')ms)"
    echo "  Redis:  $(echo "$health_response" | jq -r '.redis.connected') ($(echo "$health_response" | jq -r '.redis.response_ms')ms)"
else
    echo "  Status: ❌ Unhealthy or unreachable"
fi
echo ""

# Check Frontend
echo "🎨 Frontend Status:"
if lsof -ti:5173 > /dev/null 2>&1; then
    echo "  Vite Server: ✅ Running on :5173"
else
    echo "  Vite Server: ❌ Not running"
    echo ""
    echo "  Start with:"
    echo "  $ cd src/web && VITE_API_TARGET=http://localhost:8000 npx vite --port 5173 --host"
    exit 1
fi
echo ""

# Check API Data
echo "📊 API Data Check:"
market_count=$(curl -s http://localhost:8000/api/v1/market-map/kr 2>/dev/null | jq '.symbols | length' 2>/dev/null || echo "0")
candle_count=$(curl -s "http://localhost:8000/api/v1/candles/005930?interval=1d&limit=100" 2>/dev/null | jq 'length' 2>/dev/null || echo "0")

echo "  Market Map (KR): $market_count symbols"
echo "  Candles (005930): $candle_count records"

if [ "$market_count" -eq 0 ] || [ "$candle_count" -eq 0 ]; then
    echo ""
    echo "  ⚠️  Note: Limited data available. Mock fallback will be used."
fi
echo ""

echo "=============================="
echo "✅ Environment Ready!"
echo ""
echo "🌐 Access UI at: http://localhost:5173/"
echo ""
echo "📋 Manual Test Checklist:"
echo "  1. Open http://localhost:5173/ in browser"
echo "  2. Check Console for errors (F12)"
echo "  3. Verify Dashboard → Market Map displays"
echo "  4. Click a stock symbol"
echo "  5. Verify Analysis → Candle Chart displays"
echo "  6. Test timeframe switching (1M/5M/1D)"
echo "  7. Check OrderBook in TradingPanel"
echo "  8. Review System tab for logs"
echo ""
echo "📸 Screenshot locations:"
echo "  docs/testing/screenshots/"
echo ""
