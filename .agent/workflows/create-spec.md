---
description: Create a new specification document for a feature or module
---

# Workflow: Create Specification

This workflow creates a comprehensive specification document following the "No Spec, No Code" principle.

## Trigger Conditions
- New feature development
- Major refactoring
- API/Interface changes
- Gap analysis identifies missing spec

## Steps

1. **Identify Target**
   - User specifies module path (e.g., `src/backtest/strategies/momentum.py`)
   - OR feature name (e.g., "Orderbook Collector")

2. **Determine Spec Location**
   - Backend: `docs/specs/backend_specification.md` or module-specific
   - Frontend: `docs/specs/frontend_specification.md`
   - Database: `docs/specs/database_schema.md`
   - Strategy: `docs/specs/strategies/[name].md`

3. **Analyze Existing Code (if exists)**
   - Extract interfaces, classes, functions
   - Identify data structures
   - Note dependencies

4. **Create Spec Document**
   - Use RFC-002 template for strategies
   - Include required sections:
     - **Overview**: Purpose and scope
     - **Interface**: Function signatures, API endpoints
     - **Data Structures**: DTOs, schemas (Swagger/DDL)
     - **Edge Cases**: Null, timeout, error handling
     - **Dependencies**: External libs, services
     - **Constraints**: Performance, resource limits

5. **Validate Completeness**
   - Check: Schema defined? (Swagger/OpenAPI/DDL)
   - Check: Edge cases documented?
   - Check: Dependencies listed?

6. **Notify User**
   - Show spec document path
   - Highlight TODOs if auto-generation incomplete

## Example Usage

**User says:**
- "/create-spec"
- "SampleMomentum 전략 Spec 만들어줘"
- "Orderbook Collector 명세서 작성"

**AI will:**
1. Determine category (e.g., strategies)
2. Analyze code if exists
3. Create `docs/specs/strategies/sample_momentum.md`
4. Request user review
