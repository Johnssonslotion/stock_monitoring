#!/bin/bash
# CI/CD Smoke Test (RFC-009 Enhanced)
# Tests if all collector containers can boot successfully
# AND verifies Self-Diagnosis correctly kills containers on bad config

set -e

echo "🔍 Starting Docker Smoke Test (RFC-009 Compliant)..."

# === Phase 1: Positive Test (Normal Boot) ===
echo ""
echo "=== PHASE 1: POSITIVE TEST (정상 구동 확인) ==="

# Build all services
echo "📦 Building services..."
docker-compose -f deploy/docker-compose.yml build kis-service kiwoom-service recovery-worker

# Start services in detached mode
echo "🚀 Starting services..."
docker-compose -f deploy/docker-compose.yml --profile real up -d kis-service kiwoom-service recovery-worker

# Wait for containers to start
echo "⏳ Waiting 15 seconds for containers to initialize..."
sleep 15

# Check if containers are still running
echo "🔍 Checking container status..."
FAILED=0

for service in kis-service kiwoom-service recovery-worker; do
    STATUS=$(docker inspect -f '{{.State.Status}}' deploy-${service}-1 2>/dev/null || echo "not_found")
    
    if [ "$STATUS" = "running" ]; then
        echo "  ✅ $service is running"
    else
        echo "  ❌ $service failed (status: $STATUS)"
        echo "  📋 Logs:"
        docker logs deploy-${service}-1 --tail 20
        FAILED=1
    fi
done

# Cleanup Phase 1
echo "🧹 Cleaning up Phase 1..."
docker-compose -f deploy/docker-compose.yml down

if [ $FAILED -eq 1 ]; then
    echo "❌ Phase 1 (Positive Test) failed!"
    exit 1
fi

echo "✅ Phase 1 (Positive Test) passed!"

# === Phase 2: Negative Test (Fail-Fast on Bad Config) ===
echo ""
echo "=== PHASE 2: NEGATIVE TEST (환경 오염 시 종료 확인) ==="
echo "🧪 Testing if Self-Diagnosis correctly kills containers with missing KIS_APP_KEY..."

# Create corrupted env file (missing KIS_APP_KEY)
cp .env.prod .env.prod.backup
grep -v "KIS_APP_KEY" .env.prod > .env.prod.negative || true

# Temporarily use corrupted env
export ENV_FILE=.env.prod.negative

# Start only recovery-worker (it has Self-Diagnosis)
echo "🚀 Starting recovery-worker with corrupted env..."
docker-compose -f deploy/docker-compose.yml --profile real up -d recovery-worker 2>&1 || true

# Wait briefly for Self-Diagnosis to trigger
echo "⏳ Waiting 10 seconds for Self-Diagnosis..."
sleep 10

# Check if container has exited (expected behavior)
STATUS=$(docker inspect -f '{{.State.Status}}' deploy-recovery-worker-1 2>/dev/null || echo "not_found")
EXIT_CODE=$(docker inspect -f '{{.State.ExitCode}}' deploy-recovery-worker-1 2>/dev/null || echo "-1")

echo "  📊 Container Status: $STATUS"
echo "  📊 Exit Code: $EXIT_CODE"

# Restore original env
mv .env.prod.backup .env.prod
rm -f .env.prod.negative

# Cleanup
docker-compose -f deploy/docker-compose.yml down

# Verify: Container should have exited with non-zero code
if [ "$STATUS" = "exited" ] && [ "$EXIT_CODE" != "0" ]; then
    echo "✅ Phase 2 (Negative Test) passed! Self-Diagnosis correctly killed the container."
else
    echo "❌ Phase 2 (Negative Test) FAILED!"
    echo "   Container should have exited with non-zero code, but got: status=$STATUS, exit_code=$EXIT_CODE"
    echo "   ⚠️  This is a ZOMBIE CONTAINER risk - Self-Diagnosis is not working!"
    exit 1
fi

# === Final Result ===
echo ""
echo "🎉 All smoke tests passed! (RFC-009 Compliant)"
echo "   - Phase 1: Positive Test ✅"
echo "   - Phase 2: Negative Test ✅"
exit 0
