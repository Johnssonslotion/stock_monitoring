#!/bin/bash
# CI/CD Smoke Test
# Tests if all collector containers can boot successfully

set -e

echo "🔍 Starting Docker Smoke Test..."

# Build all services
echo "📦 Building services..."
docker-compose -f deploy/docker-compose.yml build kis-service kiwoom-service recovery-worker

# Start services in detached mode
echo "🚀 Starting services..."
docker-compose -f deploy/docker-compose.yml --profile real up -d kis-service kiwoom-service recovery-worker

# Wait for containers to start
echo "⏳ Waiting 10 seconds for containers to initialize..."
sleep 10

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

# Cleanup
echo "🧹 Cleaning up..."
docker-compose -f deploy/docker-compose.yml down

if [ $FAILED -eq 0 ]; then
    echo "✅ All smoke tests passed!"
    exit 0
else
    echo "❌ Smoke test failed!"
    exit 1
fi
