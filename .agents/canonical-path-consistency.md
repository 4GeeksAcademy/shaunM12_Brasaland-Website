# Canonical Path Consistency

**Scope:** All code, tests, documentation, and deployment configuration referencing project directories (e.g., `brasaland-webpage`, `Brasaland webpage`).

**Rationale:** Prevents runtime and deployment failures caused by inconsistent or legacy path references.

**Guardrails:**
- Use `brasaland-webpage` as the only canonical path for the website implementation.
- Do not introduce new references to `Brasaland webpage` or other legacy names.
- Ensure all redirects, rewrites, and imports match real filesystem names.

**How to Apply:**
1. When creating or updating files, always use `brasaland-webpage` in imports, rewrites, and documentation.
2. When refactoring, search for `Brasaland webpage` and update all references to `brasaland-webpage`.
3. For new tests, use import paths like `from "../../brasaland-webpage/src/utils/validations"`.
4. When editing deployment configs (e.g., `vercel.json`), ensure all paths use the canonical name.

**Example:**
- Bad: `import { validate } from "../Brasaland webpage/src/utils/validations.js";`
- Good: `import { validate } from "../brasaland-webpage/src/utils/validations";`

**Detection Signals:**
- Mixed usage of path names for the same module area.
- Rewrite or redirect targets that do not exist in the repository structure.
- Test imports using legacy path variants.

**Verification:**
- Search the repository for `Brasaland webpage` and confirm no runtime/config references remain.
- Confirm root redirect and app routes resolve correctly after path updates.
