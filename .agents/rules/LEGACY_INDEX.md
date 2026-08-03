# Legacy Rules Index (on-demand)

> **Superseded for mandatory agent reads** by root `agents.md` v2.
> Open ONE file below when the task trigger matches. Never bulk-read this directory.

| Legacy file | Read when… | Prevents… |
|-------------|------------|-----------|
| `canonical-path-consistency.md` | Renaming/moving dirs; fixing imports across apps | CI legacy path scan failures |
| `deployment-rewrite-validity.md` | Editing `vercel.json` or `next.config.mjs` rewrites | Broken production routes |
| `test-import-path-safety.md` | Adding, moving, or fixing tests | Linux/CI import failures |
| `environment-first-api-base-url.md` | API client base URL, env configuration | Hardcoded URLs, prod misconfig |
| `centralized-validation-contract.md` | New/changed forms, validators, Pydantic models | Validation duplication/drift |
| `accessibility-baseline-preservation.md` | UI layout, interactions, keyboard nav | a11y regressions |
| `change-scope-and-diff-hygiene.md` | Large refactors, mixed concerns in one PR | Noisy diffs, scope creep |
| `runtime-dependency-stability.md` | CDN/script loading, runtime deps | Load-order/network failures |
| `full-scope-typecheck-coverage.md` | Adding new TS packages or tsconfig roots | **Prefer CI** — agent rarely needs |
| `mandatory-verification-gate.md` | Pre-merge checklist reference | **Prefer CI** — agent rarely needs |

## Historical reference (separate from this directory)

| File | Read when… |
|------|------------|
| `memory-bank/historical-reference/context-22-route-conventions.md` | FastAPI mounts, backoffice `/api/*` proxy, auth rewrites |
| Other `context-*.md` | Developer names the file for active milestone/ticket work |

## Conflict rule

Live code and `agents.md` v2 beat legacy rules and historical-reference. Flag conflicts; do not edit protected paths to reconcile docs.
