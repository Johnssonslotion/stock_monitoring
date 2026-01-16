#!/bin/bash
# UI Test Environment Manager
# Phase 14 - Docker Compose + Vite

set -e

ACTION=${1:-"status"}

case "$ACTION" in
    start)
        echo "🚀 Starting Antigravity UI Test Environment..."
        echo ""
        
        # Start Backend
        echo "📦 Starting Docker services..."
        cd /Users/bbagsang-u/workspace/stock_monitoring
        docker compose -f deploy/docker-compose.yml up -d redis timescaledb api-server
        
        echo "⏳ Waiting for services to be ready..."
        sleep 5
        
        # Check health
        if curl -s http://localhost:8000/api/v1/health | jq -e '.status == "healthy"' > /dev/null; then
            echo "✅ Backend is healthy"
        else
            echo "❌ Backend health check failed"
            exit 1
        fi
        
        # Start Frontend
        echo "🎨 Starting Vite dev server..."
        cd src/web
        nohup npx vite --port 5173 --host > /tmp/vite_ui.log 2>&1 &
        echo $! > /tmp/vite.pid
        
        sleep 3
        
        if curl -s http://localhost:5173/ > /dev/null 2>&1; then
            echo "✅ Frontend is running"
        else
            echo "❌ Frontend failed to start"
            exit 1
        fi
        
        echo ""
        echo "=============================="
        echo "✅ Environment Ready!"
        echo "=============================="
        echo ""
        echo "🌐 UI:  http://localhost:5173/"
        echo "📡 API: http://localhost:8000/api/v1/health"
        echo ""
        echo "📋 Run tests with:"
        echo "   ./ui_test_env.sh test"
        echo ""
        ;;
        
    stop)
        echo "🛑 Stopping Antigravity UI Test Environment..."
        
        # Stop Frontend
        if [ -f /tmp/vite.pid ]; then
            PID=$(cat /tmp/vite.pid)
            if kill -0 $PID 2>/dev/null; then
                kill $PID
                echo "✅ Frontend stopped (PID: $PID)"
            fi
            rm /tmp/vite.pid
        fi
        
        # Stop Backend
        cd /Users/bbagsang-u/workspace/stock_monitoring
        docker compose -f deploy/docker-compose.yml stop api-server
        echo "✅ Backend stopped"
        
        echo ""
        echo "Note: Redis and TimescaleDB are still running"
        echo "To stop them: docker compose -f deploy/docker-compose.yml stop"
        ;;
        
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        echo "📊 Antigravity UI Test Environment Status"
        echo "=========================================="
        echo ""
        
        echo "📡 Backend:"
        echo "  Redis:       $(docker ps --filter name=stock-redis --format '{{.Status}}' | grep -q Up && echo '✅ Running' || echo '❌ Stopped')"
        echo "  TimescaleDB: $(docker ps --filter name=stock-timescale --format '{{.Status}}' | grep -q Up && echo '✅ Running' || echo '❌ Stopped')"
        echo "  API Server:  $(docker ps --filter name=api-server --format '{{.Status}}' | grep -q Up && echo '✅ Running' || echo '❌ Stopped')"
        
        echo ""
        echo "🏥 API Health:"
        if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
            health=$(curl -s http://localhost:8000/api/v1/health)
            echo "  Status: $(echo "$health" | jq -r '.status')"
            echo "  DB:     $(echo "$health" | jq -r '.db.connected') ($(echo "$health" | jq -r '.db.response_ms')ms)"
            echo "  Redis:  $(echo "$health" | jq -r '.redis.connected') ($(echo "$health" | jq -r '.redis.response_ms')ms)"
        else
            echo "  Status: ❌ Unreachable"
        fi
        
        echo ""
        echo "🎨 Frontend:"
        if lsof -ti:5173 > /dev/null 2>&1; then
            PID=$(lsof -ti:5173)
            echo "  Vite Server: ✅ Running (PID: $PID)"
            echo "  URL:         http://localhost:5173/"
        else
            echo "  Vite Server: ❌ Not running"
        fi
        
        echo ""
        ;;
        
    test)
        echo "🧪 Running UI Tests..."
        echo ""
        
        # Check environment
        if ! lsof -ti:5173 > /dev/null 2>&1; then
            echo "❌ Frontend not running. Start with: $0 start"
            exit 1
        fi
        
        if ! curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
            echo "❌ Backend not running. Start with: $0 start"
            exit 1
        fi
        
        echo "✅ Environment is ready"
        echo ""
        
        # Run quick checks
        echo "🔍 Quick API Checks:"
        echo "  /health:      $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/health)"
        echo "  /market-map:  $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/market-map/kr)"
        echo "  /candles:     $(curl -s -o /dev/null -w '%{http_code}' 'http://localhost:8000/api/v1/candles/005930?interval=1d&limit=10')"
        echo ""
        
        echo "📊 Data Availability:"
        market_count=$(curl -s http://localhost:8000/api/v1/market-map/kr 2>/dev/null | jq '.symbols | length' 2>/dev/null || echo "0")
        candle_count=$(curl -s "http://localhost:8000/api/v1/candles/005930?interval=1d&limit=100" 2>/dev/null | jq 'length' 2>/dev/null || echo "0")
        echo "  Market Symbols: $market_count"
        echo "  Candle Records: $candle_count"
        
        if [ "$market_count" -eq 0 ] || [ "$candle_count" -eq 0 ]; then
            echo ""
            echo "  ⚠️  Limited data. Mock fallback will activate."
        fi
        
        echo ""
        echo "=============================="
        echo "📋 Manual Test Checklist"
        echo "=============================="
        echo ""
        echo "1. Open http://localhost:5173/ in browser"
        echo "2. Check browser console (F12) for errors"
        echo "3. Dashboard Tab:"
        echo "   - [ ] Market Map displays"
        echo "   - [ ] TickerTape scrolls"
        echo "   - [ ] Click on '삼성전자'"
        echo "4. Analysis Tab:"
        echo "   - [ ] Candle Chart loads"
        echo "   - [ ] TimeFrame selector works (1M/5M/1D)"
        echo "   - [ ] OrderBook displays"
        echo "   - [ ] Volume Histogram shows"
        echo "   - [ ] MarketInfoPanel visible"
        echo "5. System Tab:"
        echo "   - [ ] Metrics display"
        echo "   - [ ] Logs stream"
        echo ""
        echo "See full test report:"
        echo "  docs/testing/UI_TEST_REPORT.md"
        echo ""
        ;;
        
    logs)
        echo "📜 Service Logs"
        echo "==============="
        echo ""
        
        TYPE=${2:-"all"}
        
        case "$TYPE" in
            frontend|vite)
                if [ -f /tmp/vite_ui.log ]; then
                    echo "🎨 Frontend Logs:"
                    tail -50 /tmp/vite_ui.log
                else
                    echo "❌ No frontend logs found"
                fi
                ;;
            backend|api)
                echo "📡 API Server Logs:"
                docker logs api-server --tail 50
                ;;
            *)
                echo "🎨 Frontend Logs (last 20):"
                [ -f /tmp/vite_ui.log ] && tail -20 /tmp/vite_ui.log || echo "  No logs"
                echo ""
                echo "📡 Backend Logs (last 20):"
                docker logs api-server --tail 20
                ;;
        esac
        ;;
        
    *)
        echo "UI Test Environment Manager"
        echo "============================"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|test|logs}"
        echo ""
        echo "Commands:"
        echo "  start    - Start Docker + Vite dev server"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  status   - Show current status"
        echo "  test     - Run quick API checks + manual test guide"
        echo "  logs     - Show logs (frontend|backend|all)"
        echo ""
        echo "Examples:"
        echo "  $0 start             # Start environment"
        echo "  $0 status            # Check status"
        echo "  $0 test              # Run tests"
        echo "  $0 logs frontend     # View Vite logs"
        echo "  $0 logs backend      # View API logs"
        echo ""
        exit 1
        ;;
esac
