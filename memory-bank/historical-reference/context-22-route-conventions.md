# CONTEXT — Route & proxy conventions (supersedes legacy path notes)

> **Repository index:** `context-22-route-conventions.md`
> **Status:** Locked 2026-07-28 — supersedes conflicting **path/proxy** statements in older context files (do not rewrite history; use this file for current routing).
> **Companion:** `memory-bank/techContext.md`, `uis/backoffice/next.config.mjs`, `/.env.example`

---

## Summary

Brasaland uses a **two-layer route model**:

| Layer | Convention | Example |
| ----- | ------------ | ------- |
| **FastAPI mounts** | Bare domain prefix | `/incidents`, `/suppliers`, `/inventory`, `/reporting`, `/knowledge`, `/telemetry`, `/tasks` |
| **Backoffice browser API calls** | Same-origin `/api/<domain>/*` rewritten to FastAPI | `/api/incidents` → `http://127.0.0.1:8000/incidents` |
| **Auth & users (backoffice)** | Bare same-origin rewrites (HttpOnly refresh cookie) | `/auth/*`, `/users/*` |
| **Backoffice UI pages** | App Router paths under `uis/backoffice/app/` | `/inventory/products`, `/knowledge`, `/incidents/[id]` |
| **Browser URL query params** | camelCase | `?productId=7&locationId=3` |
| **FastAPI query/body fields** | snake_case | `location_id`, `week_start`, `ingredient_id` |

---

## Locked decisions

| ID | Topic | Choice |
| -- | ----- | ------ |
| **R1** | FastAPI domain mounts | Bare prefixes only (`/suppliers`, not `/api/suppliers` on the Python app) |
| **R2** | Backoffice data API proxy | `/api/<domain>/*` in `next.config.mjs` for incidents, suppliers, inventory, reporting, knowledge, telemetry, tasks |
| **R3** | Auth proxy | `/auth/*` and `/users/*` stay bare on the Next origin (first-party cookies) |
| **R4** | Incident analyzer endpoints | Remain on FastAPI at `POST /incidents/analyze` and `GET /incidents/results/export` (not merged into incidents CRUD router) |
| **R5** | UI inventory entry | `/inventory` redirects to `/inventory/products`; sub-routes under `/inventory/*` |
| **R6** | Query param casing | camelCase in browser URLs; snake_case on FastAPI — map in `uis/backoffice/lib/query-params.ts` and `lib/*` clients |
| **R7** | Direct API override | Optional `NEXT_PUBLIC_*_API_BASE_URL` per domain bypasses the Next proxy and calls FastAPI mounts directly |

---

## Historical files with outdated path wording

These remain as milestone history. When they mention `/api/incidents` or `/api/suppliers` as **FastAPI** paths, read **R1–R2** above instead:

- `context-7-authentication-and-route-restriction.md`
- `context-8-authentication-flows-frontend.md`
- `context-13-centralized-incident-manager.md`
- `context-21-rag-knowledge-base.md` (follow-up migration note — **completed**)

---

## Environment variables (backoffice + API)

| Variable | Purpose |
| -------- | ------- |
| `BACKOFFICE_API_PROXY_TARGET` | Primary Next.js rewrite target (default `http://127.0.0.1:8000`) |
| `INCIDENTS_API_PROXY_TARGET` | Legacy alias; falls back when `BACKOFFICE_API_PROXY_TARGET` unset |
| `NEXT_PUBLIC_INCIDENTS_API_BASE_URL` | Direct FastAPI origin for incidents client (optional) |
| `NEXT_PUBLIC_SUPPLIERS_API_BASE_URL` | Direct FastAPI origin for suppliers client (optional) |
| `NEXT_PUBLIC_INVENTORY_API_BASE_URL` | Direct FastAPI origin for inventory client (optional) |
| `NEXT_PUBLIC_REPORTING_API_BASE_URL` | Direct FastAPI origin for reporting client (optional) |
| `NEXT_PUBLIC_KNOWLEDGE_API_BASE_URL` | Direct FastAPI origin for knowledge client (optional) |
| `NEXT_PUBLIC_TASKS_API_BASE_URL` | Direct FastAPI origin for tasks client (optional) |
| `NEXT_PUBLIC_TELEMETRY_ENDPOINT` | Browser telemetry POST target (default `/api/telemetry/events`) |
| `NEXT_PUBLIC_TELEMETRY_API_BASE_URL` | Direct FastAPI origin for telemetry (optional) |
| `FRONTEND_BASE_URL` | Backoffice origin for auth email links (default `http://localhost:3000`) |

---

## Verification checklist

- [x] FastAPI OpenAPI lists bare mounts (`/incidents`, `/suppliers`, …)
- [x] Backoffice `next.config.mjs` rewrites `/api/<domain>/*` for all data domains
- [x] API clients use `/api/<domain>` same-origin or bare mount when `NEXT_PUBLIC_*_API_BASE_URL` is set
- [x] `/inventory` redirects to `/inventory/products`
- [x] Incident list links to `/incidents/[id]`
- [x] Query param helpers in `lib/query-params.ts` with tests
