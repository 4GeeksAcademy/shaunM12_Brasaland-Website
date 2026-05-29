# Mandatory Verification Gate

**Scope:** All pull requests and merges to mainline branches.

**Rationale:** Prevents high-risk issues from reaching mainline without validation.

**Guardrails:**
- Do not merge without passing required checks.
- Required checks include path consistency, tests, and type coverage.
- Include basic route smoke validation for public entry points.

**Detection Signals:**
- PR has changes in critical files but is missing verification evidence.
- Tests or typechecks skipped without documented justification.
- Deployment config changed without route validation.

**Verification:**
- Minimum gate checklist:
  - Legacy path scan completed.
  - Unit tests passed.
  - Root and app-level typechecks passed.
  - Route smoke test for `/` and `/application` passed.
