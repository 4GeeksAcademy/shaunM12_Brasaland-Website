# Test Import Path Safety

**Scope:** All test files and their import statements.

**Rationale:** Prevents test failures in CI or Linux environments due to path inconsistency and legacy import targets.

**Guardrails:**
- Test imports must use canonical directory names.
- Do not mix multiple import path styles for the same source modules.
- Keep imports aligned with repository migration notes.

**Detection Signals:**
- Imports in `tests/` using legacy path names.
- Duplicate path styles for equivalent module roots.
- Import errors that only occur in case-sensitive environments.

**Verification:**
- Run all unit tests in CI and a local Linux-compatible environment.
- Search `tests/**/*.ts` for legacy path references.
