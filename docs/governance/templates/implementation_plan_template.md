# [Implementation Plan] {Task Title}

## 1. Goal Description
{Provide a brief description of the problem, background context, and what the change accomplishes.}

## 2. User Review Required
> [!IMPORTANT]
> **Blocking Pressure**: Is this blocking feature development? (Yes/No)
> **RFC Requirements**: List any RFCs that need approval before proceeding.

- [ ] **Breaking Changes**: {Description or None}
- [ ] **Security Implications**: {Description or None}

## 3. Proposed Changes
*Group files by component. Link to relevant RFCs/Specs.*

### 3.1 Governance & Specs
- **RFC**: [RFC-XXX](link)
- **Spec**: [Spec Name](link)

### 3.2 Implementation
#### [{Component Name}]
- [NEW] `path/to/new_file.py`
- [MODIFY] `path/to/modified_file.py`

## 4. Verification Plan
*Verify changes against the constraints defined in AI Rules.*

### 4.1 Automated Verification (Required for Code)
*If code is changed, automated verification is MANDATORY.*
- [ ] **Unit Tests**: `pytest tests/path/to/test.py`
- [ ] **Linter**: `ruff check .`
- [ ] **Spec Compliance**: Verify implementation matches the Schema defined in `docs/specs/`.

### 4.2 Manual Verification
*For visual changes or documentation review.*
- [ ] **Doc Review**: Check if generated docs render correctly.
- [ ] **User Approval**: Explicit user sign-off on RFCs.
