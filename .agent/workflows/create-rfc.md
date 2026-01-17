---
description: Create a new RFC (Request for Comments) document
---

# Workflow: Create RFC

This workflow guides the creation of a new RFC document for major changes requiring council deliberation.

## Trigger Conditions
- DB schema changes
- External API integration
- Core logic modifications
- Infrastructure changes
- Breaking changes to public interfaces

## Steps

1. **Determine RFC Number**
   - Scan `docs/governance/decisions/` for existing RFCs
   - Auto-increment: `RFC-XXX` (e.g., if RFC-003 exists, create RFC-004)

2. **Create RFC Document**
   - Location: `docs/governance/decisions/RFC-[NUMBER]_[kebab-case-title].md`
   - Use template with required sections:
     - Status: Proposed
     - Date: Current date
     - Drivers: Persona(s) proposing
     - Context: Background and problem statement
     - Decision: Proposed solution
     - Consequences: Impact analysis
     - Alternatives Considered (optional)

3. **Council Review (Optional)**
   - If major change, trigger `/council-review` workflow
   - Record deliberation in RFC document

4. **Update HISTORY.md (After Approval)**
   - Add entry with version, summary, and RFC link
   - Only update when Status changes to "Accepted"

5. **Notify User**
   - Show created RFC path
   - Request review if Council deliberation needed

## Example Usage

**User says:**
- "/create-rfc"
- "새로운 RFC 작성해줘"
- "Config 표준 RFC 만들어"

**AI will:**
1. Determine next RFC number (e.g., RFC-004)
2. Create `RFC-004_[title].md` with template
3. Ask for: Title, Context, Proposed Decision
4. Save and notify user
