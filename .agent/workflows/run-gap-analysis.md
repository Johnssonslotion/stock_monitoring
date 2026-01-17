---
description: Run gap analysis to identify code-documentation mismatches
---

# Workflow: Gap Analysis

This workflow scans the codebase to identify gaps between implementation and documentation.

## Trigger Conditions
- Quarterly governance review
- Before major releases
- After significant refactoring
- User requests audit

## Steps

1. **Scan Source Code**
   - Enumerate all files in `src/`
   - Identify major components:
     - Backend services (`src/api/`, `src/data_ingestion/`)
     - Strategies (`src/backtest/strategies/`)
     - Core modules (`src/core/`)

2. **Check Spec Coverage**
   - For each component, search for corresponding spec in `docs/specs/`
   - Flag missing specs

3. **Verify Consistency**
   - Compare spec interfaces with actual code signatures
   - Check if DB schema matches migration files
   - Validate API spec against actual endpoints

4. **Identify Governance Violations**
   - Check for hardcoded values (Config should be external)
   - Look for unsafe defaults (e.g., Dual Socket)
   - Detect heuristic logic without strict schema

5. **Generate Report**
   - Location: `docs/gap_analysis_report_[YYYY-MM-DD].md`
   - Sections:
     - **Missing Specs**: List of code without docs
     - **Inconsistencies**: Spec vs Code mismatches
     - **Governance Violations**: Rule breaches
     - **Recommendations**: RFC proposals or immediate fixes

6. **Propose Actions**
   - High Priority: RFC creation
   - Medium: Spec update
   - Low: Deferred work registration

7. **Notify User**
   - Show report path
   - Summarize critical findings (P0 issues)

## Example Usage

**User says:**
- "/run-gap-analysis"
- "Gap 분석 돌려줘"
- "코드-문서 일치 검증해줘"

**AI will:**
1. Scan `src/` directory
2. Match against `docs/specs/`
3. Generate `gap_analysis_report_2026-01-17.md`
4. Notify user of critical issues
