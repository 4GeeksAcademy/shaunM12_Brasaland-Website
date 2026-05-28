# Deployment Rewrite Validity

**Scope:** All deployment routing rules and configuration (e.g., `vercel.json`).

**Rationale:** Prevents production 404 errors by ensuring all rewrites map to valid, existing targets.

**Guardrails:**
- Every rewrite destination in `vercel.json` must map to an existing file or directory.
- Review rewrite changes whenever folder names or structure change.
- Avoid hardcoded legacy paths in hosting configuration.

**How to Apply:**
1. When editing `vercel.json`, check that each `destination` path exists in the repository.
2. After renaming or moving folders, update all rewrite rules to match the new structure.
3. During code review, verify that rewrites are updated if any folder or file is renamed.

**Example:**
- Bad: `{ "destination": "/Brasaland webpage/index.html" }` (folder does not exist)
- Good: `{ "destination": "/brasaland-webpage/index.html" }`

**Detection Signals:**
- Destination path does not exist in the repository tree.
- Deployment config references path aliases not used elsewhere.
- Divergence between local routes and hosting rewrites.

**Verification:**
- Validate rewrite destinations in `vercel.json` against the current folder tree.
- Perform route smoke tests for `/`, `/application`, and at least one nested route.
