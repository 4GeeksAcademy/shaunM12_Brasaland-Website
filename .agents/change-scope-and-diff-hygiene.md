# Change Scope and Diff Hygiene

**Scope:** All code changes, pull requests, and commits.

**Rationale:** Prevents regressions introduced by large unrelated diffs and mixed concerns.

**Guardrails:**
- Edit only files required for the task scope.
- Avoid mixing behavior changes with broad formatting-only churn.
- Do not revert unrelated user changes.

**How to Apply:**
1. Before submitting a PR, review the changed-file list and ensure each file is relevant to the stated task.
2. Separate formatting-only changes (e.g., Prettier, stylelint) into their own PRs.
3. If a bugfix requires broad changes, document why in the PR description.
4. During code review, reject PRs that mix unrelated changes or touch unexpected modules.

**Example:**
- Bad: "Fixes a typo in one file, but also reformats 50 files and changes unrelated logic."
- Good: "Fixes a typo in one file. Formatting changes are in a separate PR."

**Detection Signals:**
- Small bugfix produces large unrelated file churn.
- Functional changes bundled with broad style-only edits.
- Unexpected modifications in untouched modules.

**Verification:**
- Review changed-file list before merge.
- Confirm each modified file maps to a stated task requirement.
