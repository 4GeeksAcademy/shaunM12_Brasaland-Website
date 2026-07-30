# Technical Context

## Tech Stack
- **Frontend:**
  - Next.js (v16.2.6) and React (v19.2.4) for `uis/website` and `uis/backoffice`
  - Tailwind CSS (v4) for styling
  - Static Brasa Points registration assets served from `uis/website/public`
  - TypeScript 5 with strict mode; Vitest and Testing Library for backoffice tests
- **Backend/API (Python):**
  - FastAPI + Uvicorn shared service at `services/api/` (port 8000 in local dev)
  - Pydantic v2 and email-validator for supplier request/response validation
  - TinyDB JSON persistence for the supplier directory (`services/api/data/suppliers.json`)
  - pandas for incident CSV analysis and sales forecasting (`data/raw/brasaland_sales.csv`); pytest for API tests (`services/api/tests/`)
  - Sales forecasting (context-19): `scikit-learn`, `matplotlib`, `jupyter`, `ipykernel` in `services/api/pyproject.toml` (`uv sync`); notebook `notebooks/sales_forecasting.ipynb`; modules under `data/forecasting/`; holdout metrics include MSE, MAPE, PSI, Gini, K2
- **Backend/API (external):**
  - 4Geeks Talent Tracker REST API for candidate CRUD and notes (`NEXT_PUBLIC_TRACKER_API_BASE_URL`)
- **Business logic (TypeScript):**
  - Milestone 2 utilities in `src/` (operations, validations, transformations)
  - Backoffice data-processing module at `uis/backoffice/app/data-processing/data-processing-core/`
  - Incident analyzer package at `services/api/incident_analyzer/`
- **Tooling:**
  - Node.js/npm for dependency and script management
  - Python 3.12 for the FastAPI service: root `.venv` for `api:dev`/`api:install`, or **uv** in `services/api/` (`pyproject.toml`, `uv sync`, `uv run seed` / `python -m seeds.*`) for checklist-aligned seeding
  - Vitest for unit testing
  - Custom Node.js scripts for static site serving and incident CSV analysis (`scripts/analyze.py`)
  - Vercel for deployment (static public website rewrites in `vercel.json`; backoffice and FastAPI require separate hosting for full production)

## Architectural Decisions
- **Canonical Directory Structure:**
  - Active UI apps are `uis/website` (public) and `uis/backoffice` (internal).
  - Legacy duplicate app folders are retired when not part of active runtime paths.
- **Shared FastAPI service:**
  - Domain routers use bare FastAPI mounts (`/incidents`, `/suppliers`, `/inventory`, `/reporting`, `/knowledge`, `/telemetry`, `/tasks`).
  - The backoffice keeps browser-facing `/api/<domain>/*` URLs and translates them to bare FastAPI mounts through `uis/backoffice/next.config.mjs` (including `/api/telemetry/*` and `/api/tasks/*`).
  - Auth and users use bare same-origin rewrites (`/auth/*`, `/users/*`) for HttpOnly refresh cookies.
  - **Authoritative route decision log:** `memory-bank/historical-reference/context-22-route-conventions.md` (supersedes legacy `/api/incidents` FastAPI path notes in older milestone contexts).
- **URL parameter conventions (backoffice):**
  - Browser address bar / Next.js page query params use **camelCase** (e.g. `productId`, `locationId`, `referenceDate`).
  - FastAPI query params and JSON bodies use **snake_case** (e.g. `location_id`, `week_start`, `ingredient_id`).
  - Map between the two in `uis/backoffice/lib/query-params.ts` and domain API clients under `uis/backoffice/lib/` — not in page components.
- **Domain module layout:**
  - Suppliers: `services/api/suppliers/` (constants, models, repository, routes)
  - Incidents: `services/api/incident_analyzer/` (constants, schemas, validators, analyzer, reporting)
- **Historical context naming:**
  - Files such as `context-6-supplier-directory.md` use a repository index (`context-{n}`), not the course milestone number. The supplier directory corresponds to course **Milestone 09 — Lightweight Storage API**.
- **Centralized Validation:**
  - Validation logic is shared in dedicated modules to prevent duplication and drift.
- **Type Safety:**
  - TypeScript is enforced with strict settings and CI coverage for all subprojects and tests.
- **Deployment Safety:**
  - All deployment rewrites and routes are validated against the real file structure; legacy paths are forbidden.
- **Accessibility:**
  - Accessibility features (skip links, ARIA labels) are baseline requirements for all UI changes.
- **Runtime Dependency Management:**
  - CDN dependencies are allowed only with documented fallbacks or for demo/dev use; production prefers build-time integration.
- **Rule-Driven Engineering:**
  - All development follows a formal ruleset for risk mitigation, code review, and merge gating.

## Technical Constraints
- **No legacy path references:**
  - All code, tests, and configs must use the canonical directory names.
- **Environment configuration required:**
  - API base URLs and other sensitive settings must be provided via environment variables in production/staging.
- **Typecheck and test coverage:**
  - CI must run typechecks and tests for all code, including subprojects and tests.
- **No ad-hoc validation:**
  - All validation must use shared modules; no inline or duplicated logic.
- **Deployment rewrites must match structure:**
  - All rewrite rules must point to existing files/directories; changes require review.
- **Accessibility cannot regress:**
  - UI changes must not remove or break accessibility features.
- **No critical runtime dependency without fallback:**
  - All essential runtime dependencies must have a documented fallback or be bundled at build time.

## Local development commands

| Goal | Command |
|------|---------|
| Install Python API dependencies | `npm run api:install` (pip) or `npm run api:sync` (uv in `services/api/`) |
| Seed supplier directory | `npm run api:seed` or `cd services/api && uv run seed` |
| Run FastAPI (incidents + suppliers) | `npm run api:dev` → `http://127.0.0.1:8000` |
| Run backoffice | `cd uis/backoffice && npm run dev` → `http://localhost:3000` |
| Run public website | `cd uis/website && npm run dev -- -p 3001` |
| Run supplier API tests | `cd services/api && ../../.venv/bin/python -m pytest tests/ -q` |
| Run incident CSV analyzer CLI | `python scripts/analyze.py data/incidents-brasaland.csv` |
