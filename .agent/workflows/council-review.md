---
description: Conduct Council of Six deliberation for major decisions
---

# Workflow: Council Review

This workflow conducts a formal deliberation among the 6 personas for major decisions.

## Trigger Conditions (from personas.md)
- Architecture changes affecting 2+ components
- Rule violations (ai-rules.md breach)
- Quality gate failures (Tier 1-3 tests)
- Production incidents (data loss, downtime)
- API schema breaking changes

## Steps

1. **Validate Trigger**
   - Confirm the issue meets trigger conditions
   - If not critical, skip Council and proceed with normal development

2. **Prepare Context**
   - Summarize the issue/proposal
   - Gather relevant specs, RFCs, or code

3. **Conduct Deliberation (Strict Order)**
   - **순서**: PM → Architect → Data Scientist → Infra → Developer → QA → Doc Specialist
   - **규칙**: Each persona provides 3-5 sentences minimum
   - **형식**: Full quote in blockquote (원문 그대로)
   - **No Summary**: NEVER paraphrase or summarize

4. **Record in Implementation Plan**
   - Section: "## Council of Six - 페르소나 협의"
   - Format:
     ```markdown
     ### 👔 PM (Project Manager)
     > "[Full verbatim quote from PM]"
     
     ### 🏛️ Architect
     > "[Full verbatim quote from Architect]"
     ```

5. **PM Final Decision**
   - PM reviews all opinions
   - Makes binding decision based on business value + timeline
   - Record in separate "PM의 최종 결정" section

6. **Determine Auto-Proceed**
   - If unanimous + safe work → Auto-proceed
   - If unsafe or split decision → Notify user for approval

7. **Notify User**
   - Show implementation plan path
   - Highlight PM's decision
   - Request approval if needed (BlockedOnUser=true)

## Example Usage

**User says:**
- "/council-review"
- "Council 협의 필요해"
- "아키텍처 변경인데 검토해줘"

**AI will:**
1. Validate trigger condition
2. Gather 6 persona opinions (full quotes)
3. Record in implementation_plan.md
4. Show PM's final decision
5. Auto-proceed or request user approval
