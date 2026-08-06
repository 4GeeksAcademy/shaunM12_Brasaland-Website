# Agent Operating Protocol (v2 — token-scoped)

> **Active agent protocol for this repo.** Legacy rules remain at `.agents/rules/` — use `.agents/rules/LEGACY_INDEX.md` on demand only (not bulk-read at session start).

## Precedence (highest wins)

1. Developer prompt (scope, @mentions)
2. This file (`agents.md`)
3. Live code and `.github/workflows/ci.yml`
4. Conditional reads: `memory-bank/techContext.md`, `CONTEXT.md`, named `memory-bank/historical-reference/` files
5. Legacy `.agents/rules/*.md` (triggered via `LEGACY_INDEX.md` only)
6. Other archived milestone docs under `memory-bank/historical-reference/`

On conflict: follow higher tier; flag discrepancy to developer. Never edit protected paths to resolve doc drift.

**Alignment:** Stay aligned with `CONTEXT.md`, triggered `memory-bank/` reads, and live code. Historical-reference files are milestone specs — consult only the one named for the active task; they are not authoritative by default.

---

## Default behavior (every task)

- Work from the developer's prompt scope first. If scope is missing, ask once — do not explore the repo.
- Read ONLY: files named in the prompt, files you must edit, and imports directly required by those edits.
- Do NOT read `memory-bank/historical-reference/`, `CONTEXT.md`, other `memory-bank/*`, or `.agents/rules/` unless a trigger below applies or the developer @mentions them.
- Do NOT grep repo-wide. Search within the scoped directory only.
- Do NOT spawn broad exploration subagents unless the developer asks for an audit or architecture review.
- Responses: cite line ranges; do not paste whole files.
- When in doubt whether **technical** conventions apply (paths, proxies, env, camelCase/snake_case, package boundaries), read `memory-bank/techContext.md` once before editing.

---

## Protected paths (never modify without explicit developer confirmation)

- `memory-bank/historical-reference/**`
- `data/raw/**`
- `workflows/**`
- `vercel.json`
- `.agents/**` (except when developer explicitly requests a rules/protocol update)

> **Note:** P0 rules (Deployment Rewrite Validity, Canonical Path Consistency) may require edits to `vercel.json`. That is permitted with explicit developer confirmation, consistent with the protected-paths policy above.

---

## Context triggers

Read the files below **only when the trigger applies** — not at every session start.

### `memory-bank/techContext.md`

Read when ANY apply. Otherwise skip.

**Must read (skim full file):**

- First backend, backoffice, website, or cross-app work in the session
- Task spans more than one area: `services/api/`, `uis/backoffice/`, `uis/website/`, `src/`, `mcps/`
- Developer says "new feature", "refactor", or scope is unclear

**Must read (targeted sections only):**

| Task touches… | Sections in techContext.md |
|---------------|----------------------------|
| Backoffice pages, API clients, query params | Tech Stack → Frontend; Architectural Decisions → URL parameter conventions; Shared FastAPI service |
| `next.config.mjs`, `/api/*` proxy, auth cookies | Architectural Decisions → Shared FastAPI service, Canonical Directory Structure |
| `services/api/` routers, Pydantic, seeds, pytest | Tech Stack → Backend/API (Python); Domain module layout |
| Shared TS in `src/` | Tech Stack → Business logic (TypeScript); Canonical Directory Structure |
| Local dev / run commands | Local development commands |
| Tests (root or backoffice) | Tech Stack → Tooling; Local development commands |

**Also trigger when editing routing/proxy:** `memory-bank/historical-reference/context-22-route-conventions.md` (developer-named or routing task).

**Skip when:** single-file change with explicit path, no API/routing/env/proxy, pure copy/CSS/text — unless developer @mentions techContext.

**Session rule:** do not re-read techContext.md in the same session unless scope expands to a new row above.

---

### `CONTEXT.md`

Read **relevant sections only** when task involves business/domain rules, Brasaland operations, Brasa Points, location-specific logic, or user-facing copy tied to domain constraints. Skip for pure technical refactors.

Root `CONTEXT.md` is repo-wide company context only. Milestone 1 website and Brasa Points form requirements live in `memory-bank/historical-reference/context-1-milestone-1.md`.

---

### `memory-bank/projectbrief.md` / `memory-bank/progress.md`

- **projectbrief.md:** onboarding-style tasks or when developer asks for project overview.
- **progress.md:** read before updating; update **only before commit** when the task materially changed project state (developer must ask for commit).

---

### Named milestone / feature specs

Read **one** developer-named file under `memory-bank/historical-reference/` — never bulk-read the directory.

Examples: `context-1-milestone-1.md` (public website, Brasa Points form, landing copy, M1 validations), `context-22-route-conventions.md` (routing), `context-24-mcp-company-tools.md` (MCP), `context-27-milestone-9-rfp-intake-routing-p1.md` (Milestone 9 RFP intake/routing — read p1 before p2/p3 companions), developer-specified milestone ticket.

Full index: `memory-bank/historical-reference/context-index.md`.

---

## Legacy rules (on demand)

Do NOT read all of `.agents/rules/`. Open **one** file when task matches `.agents/rules/LEGACY_INDEX.md`.

Priority tiers (detail in `.agents/rules/DEVELOPMENT_RULES.md`):

- **P0 (blocking):** Canonical Path Consistency, Deployment Rewrite Validity, Test Import Path Safety
- **P1 (must pass before commit):** Full-Scope Typecheck Coverage, Environment-First API Base URL
- **P2 (advisory / hardening):** Verification Gate, Centralized Validation Contract, Accessibility Baseline Preservation, Runtime Dependency Stability, Change Scope and Diff Hygiene

Quick reference:

| Task touches… | Legacy rule |
|---------------|-------------|
| Paths, imports, directory renames | `canonical-path-consistency.md`, `test-import-path-safety.md` |
| `vercel.json`, deploy rewrites | `deployment-rewrite-validity.md` |
| API base URL / env vars | `environment-first-api-base-url.md` |
| Forms / validation | `centralized-validation-contract.md` |
| UI / a11y | `accessibility-baseline-preservation.md` |
| Large refactors | `change-scope-and-diff-hygiene.md` |

CI-owned (agent rarely needs): `full-scope-typecheck-coverage.md`, `mandatory-verification-gate.md`.

If a legacy rule conflicts with `CONTEXT.md`, triggered memory-bank reads, or live code, the higher-precedence source wins — flag the discrepancy to the developer.

---

## Verification (quality without full-suite cost)

| When | Run |
|------|-----|
| During edits | Linter/diagnostics on changed files only |
| Before commit (developer asked) | Tests + typecheck for **one affected package** |
| Developer says "full CI" / "verify all" | Match `.github/workflows/ci.yml` |

**Package map:**

- Root TS/tests → `npm run typecheck`, `npm test`
- Backoffice → `cd uis/backoffice && npm run typecheck` / `npm test`
- Website → `cd uis/website && npm run typecheck`
- API → `npm run api:test`

Do NOT re-run the same passing check in the same session unless code changed again.

---

## Before commit only (developer must ask for commit)

Complete these steps in order:

1. Re-read scope and acceptance criteria from the active milestone context file (when applicable).
2. Scoped verification (table above).
3. Confirm user-facing flows changed in this task still work end-to-end (when applicable).
4. One-paragraph change summary with risks and rollback hints.
5. Update `memory-bank/progress.md` only if project state materially changed.

Do NOT re-read milestone context files unless commit is for active milestone work.
