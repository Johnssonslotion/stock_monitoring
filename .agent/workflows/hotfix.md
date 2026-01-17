---
description: Handle critical production hotfixes with expedited workflow
---

# Workflow: Hotfix

This workflow handles **critical production issues** that require immediate deployment, bypassing normal development flow.

## ⚠️ Use Only For Critical Issues
- Production down
- Data loss risk
- Security vulnerability
- Critical bug affecting users

**DO NOT use for:**
- Normal bugs (use `/create-issue`)
- Feature requests
- Refactoring

---

## Trigger Conditions
- Production incident detected
- Critical bug reported
- User command: `/hotfix`

## Steps

### 1. Verify Criticality
**Action**: Confirm this is truly a hotfix scenario

**Ask user:**
- What is broken?
- Is production affected?
- Can it wait for normal release cycle?

**If not critical** → Redirect to `/create-issue`

---

### 2. Create Incident Report
**Action**: Document the incident

**Location**: `docs/incidents/HOTFIX-[YYYY-MM-DD]-[short-title].md`

**Template**: Use `docs/templates/incident_report_template.md`

**Required Info:**
- **Severity**: Critical / High
- **Impact**: Number of users affected, data at risk
- **Timeline**: When did it start?
- **Root Cause** (if known)

---

### 3. Create Hotfix Branch
**Action**: Branch from `main` (NOT develop)
```bash
git checkout main
git pull origin main
git checkout -b hotfix/[YYYYMMDD]-[issue-name]
```

**Example**: `hotfix/20260117-fix-auth-bypass`

**Why main?**: Hotfixes deploy directly to production

---

### 4. Implement Fix (Minimal Changes)
**Principle**: **Minimum Viable Fix** only

**Guidelines:**
- Fix ONLY the critical issue
- No refactoring
- No feature additions
- Keep diff as small as possible

**Skip (for speed):**
- Spec updates (defer to post-hotfi

x)
- Extensive testing (run essentials only)
- Gap analysis

---

### 5. Run Critical Tests Only
**Action**: Execute minimal test suite
```bash
pytest tests/[affected-module]/ -k "critical"
```

**Pass Criteria**:
- Critical tests pass
- Fix verified manually

**If tests fail** → Continue fixing until pass

---

### 6. Merge to Main
**Action**: Direct merge to `main`
```bash
git checkout main
git merge hotfix/[name] --no-ff -m "HOTFIX: [description]"
git tag hotfix-$(date +%Y%m%d-%H%M)
git push origin main --tags
```

**No Council Review**: Hotfixes bypass normal governance (emergency exception)

---

### 7. Deploy to Production
**Action**: Trigger production deployment

**Command** (if automated):
```bash
make deploy-prod
```

**Manual deployment**: Follow `docs/governance/deployment_strategy.md`

---

### 8. Backport to Develop
**Action**: Ensure fix is in `develop` branch
```bash
git checkout develop
git merge hotfix/[name] --no-ff -m "Backport HOTFIX: [description]"
git push origin develop
```

**Purpose**: Prevent regression in next release

---

### 9. Update Documentation (Post-Hotfix)
**Action**: After fire is out, update docs

**Required Updates:**
- `BACKLOG.md`: Add hotfix to "Done" section
- Incident report: Add "Resolution" section
- `CHANGELOG.md`: Document hotfix
- Spec/RFC (if needed): Create follow-up tasks

---

### 10. Post-Mortem (Optional but Recommended)
**Action**: Schedule retrospective

**Questions:**
- What caused the issue?
- Why wasn't it caught earlier?
- How to prevent recurrence?

**Document**: Add to incident report or create ADR

---

### 11. Cleanup
**Action**: Delete hotfix branch
```bash
git branch -d hotfix/[name]
git push origin --delete hotfix/[name]
```

---

## Safety Features

### 1. Audit Trail
- All hotfixes tagged: `hotfix-[timestamp]`
- Incident report created
- Changes logged in CHANGELOG

### 2. Backport Protection
- Fix MUST be merged to `develop`
- Prevents regression

### 3. Minimal Scope
- Only critical fix
- No side changes

---

## Workflow Call Graph
```
/hotfix
├─> Create incident report
├─> Branch from main
├─> Minimal fix
├─> Critical tests only
├─> Merge to main → Deploy
└─> Backport to develop
```

**No recursive calls**: Speed is priority

---

## Example Usage

**User says:**
- "/hotfix"
- "긴급 수정 필요해"
- "프로덕션 장애 대응"

**AI will:**
1. Confirm criticality
2. Create incident report
3. Branch from `main`
4. Guide minimal fix
5. Test → Merge → Deploy
6. Backport to `develop`
7. Update docs

---

## Post-Hotfix Follow-up

After hotfix deployed, consider:
- [ ] Create RFC for permanent solution (if quick fix was hacky)
- [ ] Update specs
- [ ] Add regression tests
- [ ] Schedule refactoring (if needed)

**Register as**:
- Deferred Work (if permanent fix needed)
- Tech Debt (if workaround applied)
