# Full-Scope Typecheck Coverage

**Scope:** All TypeScript code, including root sources, subprojects (e.g., `uis/backoffice`, `uis/website`), and tests.

**Rationale:** Prevents silent type regressions in uncovered areas such as tests and app projects.

**Guardrails:**
- Root typecheck must cover root TypeScript sources and tests.
- Subprojects with their own TS config must have explicit typecheck commands.
- CI execution of all typecheck targets is recommended (advisory), not required. When the repo is hosted on GitHub, `.github/workflows/ci.yml` runs these targets; locally, run them via the npm scripts.

**How to Apply:**
1. Ensure `tsconfig.json` at the root includes all relevant source and test directories (e.g., `src`, `tests`).
2. For subprojects (e.g., `uis/backoffice`, `uis/website`), add a typecheck script in their `package.json` (e.g., `tsc --noEmit`).
3. In CI (e.g., GitHub Actions), run both root and subproject typechecks:
	 - `npx tsc --noEmit`
	 - `cd uis/backoffice && npx tsc --noEmit`
	 - `cd uis/website && npx tsc --noEmit`
4. When adding new directories, update `include` in the relevant `tsconfig.json` files.

**Example:**
- Add to CI workflow:
	```yaml
	- run: npx tsc --noEmit
	- run: cd uis/backoffice && npx tsc --noEmit
	- run: cd uis/website && npx tsc --noEmit
	```

**Detection Signals:**
- Root `tsconfig.json` includes only a subset of active code.
- App-level TS project exists without a CI typecheck step.
- New TS files added outside configured include patterns.

**Verification:**
- Run root typecheck and app-level typecheck in CI.
- Validate include patterns when new directories are added.
