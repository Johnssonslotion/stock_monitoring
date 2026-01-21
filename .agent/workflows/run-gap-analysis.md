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
   - **DB Schema vs Migration SQL (Critical)**: `migrations/` 폴더의 SSoT SQL 파일과 실제 DB 스키마(컬럼명, 타입, 제약조건)를 비교한다.
     - 특히 `market_orderbook`과 같이 43컬럼 이상의 복잡한 테이블의 필드 누락 여부를 전수 체크한다.
   - **Python Model vs Migration SQL**: Pydantic 모델 필드 구성과 SQL DDL의 일치 여부를 검토한다.
   - **API Spec vs Migration SQL**: Swagger/OpenAPI 명세와 실제 DB 컬럼의 명칭 일치 여부를 검증한다.
   - **Check Strategy Alignment**:
     - Verify `docs/data_acquisition_strategy.md` reflects current API capabilities
     - Flag if new APIs (e.g., Recovery/Validation) are missing from Strategy

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
