# ISSUE-042: Docker Network Isolation Fix

**Status**: Open
**Priority**: P1 (High)
**Type**: Bug
**Created**: 2026-01-26
**Assignee**: Agent

## Problem Description
Service containers in the `stock_prod` stack (`sentinel-agent`, `news-archiver`, `recovery-worker`) failed to connect to Redis instances (`redis`, `redis-gatekeeper`) in the `deploy` stack.
- **Cause**: Distinct default bridge networks (`deploy_default` vs `stock_prod_default`) created by `docker compose` isolation.
- **Impact**: Service startup failures, monitoring gaps, and potential data loss (though backup mechanisms existed).

## Acceptance Criteria
- [ ] Unified network configuration in `docker-compose.yml` (e.g., external network or shared stack).
- [ ] All `stock_prod` services can resolve `redis` and `redis-gatekeeper` hostnames automatically.
- [ ] No manual `docker network connect` required after deployment.

## Technical Details
- Current workaround: Manually bridging networks via `docker network connect`.
- Proposed solution: Define an external network `stock_network` and attach all services in both `deploy` and `stock_prod` stacks to it.

## Resolution Plan
1. Update `deploy/docker-compose.yml` to define a top-level network (or external).
2. Update service definitions to use this shared network.
3. Validate connectivity with a fresh `up -d` cycle.

## Related
- Discovered during: 2026-01-26 Morning Health Check
