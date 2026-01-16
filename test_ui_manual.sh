#!/bin/bash
# UI Manual Test Script
# Phase 14 - Local UI Verification with Mock Data

set -e

echo "🧪 Antigravity UI Manual Test Suite"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test Configuration
BASE_URL="http://localhost:5173"
TEST_RESULTS=()

# Helper Functions
check_endpoint() {
    local url=$1
    local name=$2
    
    echo -n "Testing: $name ... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" --max-time 5)
    
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $response)"
        TEST_RESULTS+=("PASS: $name")
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $response)"
        TEST_RESULTS+=("FAIL: $name (HTTP $response)")
        return 1
    fi
}

check_content() {
    local url=$1
    local pattern=$2
    local name=$3
    
    echo -n "Testing: $name ... "
    
    content=$(curl -s "$url" --max-time 5)
    
    if echo "$content" | grep -q "$pattern"; then
        echo -e "${GREEN}✓ PASS${NC}"
        TEST_RESULTS+=("PASS: $name")
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Pattern not found: $pattern)"
        TEST_RESULTS+=("FAIL: $name")
        return 1
    fi
}

# Wait for server
echo "⏳ Waiting for Vite dev server..."
for i in {1..10}; do
    if curl -s "$BASE_URL" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Server is ready${NC}"
        break
    fi
    if [ $i -eq 10 ]; then
        echo -e "${RED}✗ Server not responding after 10 seconds${NC}"
        exit 1
    fi
    sleep 1
done

echo ""
echo "📋 Test Suite: Frontend Components"
echo "-----------------------------------"

# Test 1: Main App Loads
check_endpoint "$BASE_URL" "Main App Load"

# Test 2: React Root Element
check_content "$BASE_URL" "root" "React Root Element Present"

# Test 3: Vite Configuration
check_content "$BASE_URL" "type=\"module\"" "Vite Module Loading"

# Test 4: Check for critical assets
echo ""
echo "📦 Test Suite: Asset Loading"
echo "----------------------------"

# Extract and test CSS
css_files=$(curl -s "$BASE_URL" | grep -o 'href="[^"]*\.css"' | sed 's/href="//;s/"$//' || true)
if [ ! -z "$css_files" ]; then
    for css in $css_files; do
        check_endpoint "$BASE_URL$css" "CSS: $css"
    done
else
    echo -e "${YELLOW}⚠ No CSS files found (may be inlined)${NC}"
fi

# Extract and test JS modules
js_files=$(curl -s "$BASE_URL" | grep -o 'src="[^"]*\.js"' | sed 's/src="//;s/"$//' || true)
if [ ! -z "$js_files" ]; then
    for js in $js_files; do
        check_endpoint "$BASE_URL$js" "JS: $js"
    done
else
    echo -e "${YELLOW}⚠ No JS files found in initial HTML${NC}"
fi

echo ""
echo "🧩 Test Suite: Mock Data Layer"
echo "-------------------------------"

# Check if mock files exist
echo -n "Checking Mock Files ... "
if [ -f "src/web/src/mocks/marketMocks.ts" ] && \
   [ -f "src/web/src/mocks/tradingMocks.ts" ] && \
   [ -f "src/web/src/mocks/marketHoursMock.ts" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    TEST_RESULTS+=("PASS: Mock Files Present")
else
    echo -e "${RED}✗ FAIL${NC}"
    TEST_RESULTS+=("FAIL: Mock Files Missing")
fi

# Check mock data structure
echo -n "Checking MOCK_SECTORS ... "
if grep -q "MOCK_SECTORS" "src/web/src/mocks/marketMocks.ts"; then
    echo -e "${GREEN}✓ PASS${NC}"
    TEST_RESULTS+=("PASS: MOCK_SECTORS Defined")
else
    echo -e "${RED}✗ FAIL${NC}"
    TEST_RESULTS+=("FAIL: MOCK_SECTORS Not Found")
fi

echo -n "Checking generateMockCandles ... "
if grep -q "generateMockCandles" "src/web/src/mocks/tradingMocks.ts"; then
    echo -e "${GREEN}✓ PASS${NC}"
    TEST_RESULTS+=("PASS: Mock Candle Generator Present")
else
    echo -e "${RED}✗ FAIL${NC}"
    TEST_RESULTS+=("FAIL: Mock Candle Generator Missing")
fi

echo ""
echo "🎨 Test Suite: Component Structure"
echo "-----------------------------------"

# Check critical components
components=(
    "App.tsx"
    "components/MarketMap.tsx"
    "components/CandleChart.tsx"
    "components/TradingPanel.tsx"
    "components/OrderBookView.tsx"
    "components/TickerTape.tsx"
    "components/MarketInfoPanel.tsx"
    "components/VolumeHistogram.tsx"
)

for comp in "${components[@]}"; do
    echo -n "Checking $comp ... "
    if [ -f "src/web/src/$comp" ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        TEST_RESULTS+=("PASS: Component $comp")
    else
        echo -e "${RED}✗ FAIL${NC}"
        TEST_RESULTS+=("FAIL: Component $comp Missing")
    fi
done

echo ""
echo "🔌 Test Suite: API Integration"
echo "-------------------------------"

# Check API utility
echo -n "Checking API Utility (fetchJson) ... "
if grep -q "fetchJson" "src/web/src/api.ts" 2>/dev/null; then
    echo -e "${GREEN}✓ PASS${NC}"
    TEST_RESULTS+=("PASS: API Utility Present")
else
    echo -e "${RED}✗ FAIL${NC}"
    TEST_RESULTS+=("FAIL: API Utility Missing")
fi

# Check fallback logic in App.tsx
echo -n "Checking Mock Fallback Logic ... "
if grep -q "setDataSource.*mock" "src/web/src/App.tsx"; then
    echo -e "${GREEN}✓ PASS${NC}"
    TEST_RESULTS+=("PASS: Mock Fallback Implemented")
else
    echo -e "${YELLOW}⚠ WARNING${NC}"
    TEST_RESULTS+=("WARN: Mock Fallback Not Verified")
fi

echo ""
echo "=================================="
echo "📊 Test Summary"
echo "=================================="

pass_count=$(printf '%s\n' "${TEST_RESULTS[@]}" | grep -c "^PASS:" || true)
fail_count=$(printf '%s\n' "${TEST_RESULTS[@]}" | grep -c "^FAIL:" || true)
warn_count=$(printf '%s\n' "${TEST_RESULTS[@]}" | grep -c "^WARN:" || true)
total_count=${#TEST_RESULTS[@]}

echo ""
echo -e "${GREEN}✓ Passed: $pass_count${NC}"
echo -e "${RED}✗ Failed: $fail_count${NC}"
echo -e "${YELLOW}⚠ Warnings: $warn_count${NC}"
echo "Total: $total_count"
echo ""

if [ $fail_count -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    echo ""
    echo "🌐 Access your UI at: http://localhost:5173/"
    echo ""
    echo "🧪 Manual Testing Checklist:"
    echo "  1. Open browser to http://localhost:5173/"
    echo "  2. Verify Dashboard tab shows Market Map"
    echo "  3. Click on a stock symbol (e.g., 삼성전자)"
    echo "  4. Switch to Analysis tab"
    echo "  5. Verify Candle Chart with mock data"
    echo "  6. Check OrderBook displays properly"
    echo "  7. Test Timeframe selector (1M, 5M, 1D)"
    echo "  8. Verify TickerTape scrolling"
    echo "  9. Check MarketInfoPanel (News/Related)"
    echo " 10. Switch to System tab and verify logs"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please review above.${NC}"
    exit 1
fi
