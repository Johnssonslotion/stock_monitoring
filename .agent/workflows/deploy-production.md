---
description: Deploy to production with safety checks, log verification, and health monitoring
---
# Workflow: Deploy to Production (RFC-006)

This workflow automates the production deployment process, enforcing **Deep Log Verification** to prevent silent failures.

## Trigger Conditions
- Feature branch merged to `develop` or `main`.
- User command: `/deploy-production`
- Hotfix deployment required.

## Steps

### 1. Pre-Deployment Validation
**Action**: Check environment and git status.
- Ensure branch is `develop` or `main`.
- Ensure no uncommitted changes.
- Check `.env.prod` exists and is valid (`make validate-env-prod`).

### 2. Push Changes
**Action**: Sync with remote repository.
```bash
git push origin [current-branch]
```

### 3. Apply Update (Rolling Restart)
**Action**: Pull images/source and restart containers.
```bash
make up-prod
```
*Note*: This command runs `docker compose --profile real up -d`.

### 4. Wait for Initialization
**Action**: Allow services to bootstrap.
```bash
echo "⏳ Waiting 30s for services to initialize..."
sleep 30
```

### 5. Deep Log Verification (RFC-006)
**Action**: Scan container logs for critical errors.
```bash
python3 scripts/verify_deployment_logs.py --duration 35
```

**Pass Criteria**:
- Exit Code 0 (No critical errors found).
- Warnings are allowed but reported.

**Fail Action**:
- If critical errors found, notify user immediately.
- Suggest: `make down` or rollback to previous tag.

### 6. Health Check (Application Level)
**Action**: Verify HTTP endpoints and dependencies.
```bash
curl -f http://localhost:8001/api/v1/health/detailed || echo "Health Check Failed"
```

### 7. Notify User
**Success Message**:
```
🚀 Deployment Successful!
- Branch: [branch]
- Log Check: ✅ Clean
- Health Check: ✅ Healthy
```

**Failure Message**:
```
❌ Deployment FAILED
- Log Check found CRITICAL ERRORS.
- Please check: docker logs [container-name]
```
