# Verification Gate (Advisory)

**Status:** Advisory / recommended — non-blocking. This rule documents the preferred verification routine; it does not hard-block commits or merges. A GitHub Actions workflow (`.github/workflows/ci.yml`) implements these checks when the repo is hosted on GitHub, but it is optional tooling, not a precondition for working locally.

**Scope:** All pull requests and merges to mainline branches.

**Rationale:** Reduces the chance of high-risk issues reaching mainline without validation.

**Recommendations:**
- Prefer not to merge until the recommended checks pass.
- Recommended checks include path consistency, tests, and type coverage.
- Include basic route smoke validation for public entry points where practical.

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
