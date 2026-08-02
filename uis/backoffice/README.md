# Brasaland Backoffice

Internal Next.js + TypeScript ops app (incidents, suppliers, inventory, reporting, knowledge, support agent, …).

> Parent overview: [../../README.md](../../README.md) · API: [../../services/api/README.md](../../services/api/README.md) · Route conventions: [../../memory-bank/historical-reference/context-22-route-conventions.md](../../memory-bank/historical-reference/context-22-route-conventions.md)

## Main routes

### Authenticated app pages

| Path | Purpose |
| ---- | ------- |
| `/` | Executive Assistant talent pipeline (4Geeks tracker) |
| `/candidates/[id]` | Candidate detail |
| `/data-processing` | Milestone 2 ops dashboard (`src/` logic) |
| `/registration-analytics` | Brasa Points registration analytics |
| `/incidents` | Incident manager + CSV analyzer |
| `/incidents/[id]` | Incident detail |
| `/suppliers` | Supplier directory |
| `/suppliers/[id]` | Supplier detail |
| `/inventory` | Redirects to `/inventory/products` |
| `/inventory/products` | Product stock dashboard |
| `/inventory/orders/inbound` | Log inbound delivery |
| `/inventory/orders/outbound` | Log outbound consumption/waste |
| `/inventory/orders` | Combined order history (read-only) |
| `/reporting` | Weekly location KPI dashboard |
| `/knowledge` | RAG knowledge query + reindex (needs Qdrant) |
| `/support` | LangGraph support agent query (needs Qdrant; no reindex) |
| `/account/profile` | User profile |
| `/account/users` | User admin (admin only) |

### Public auth pages

| Path | Purpose |
| ---- | ------- |
| `/login` | Sign in |
| `/register` | Create account |
| `/forgot-password` | Request password reset |
| `/reset-password` | Complete password reset (`?token=`) |
| `/verify-email` | Email verification (`?token=`) |

Pages that call the API need FastAPI on **`http://127.0.0.1:8000`**. For **Run pipeline** on `/reporting`, also start Redis and the Celery worker ([services/api/README.md](../../services/api/README.md#celery-worker-dev-55)). For `/knowledge` and `/support`, also run Qdrant (see root `.env.example`). **`/support` incident queries** additionally require the MCP company-tools server on **`http://127.0.0.1:8765`** — see [mcps/brasaland-company-tools/README.md](../../mcps/brasaland-company-tools/README.md).

## Development

**Terminal 1 — API (repo root):**

```bash
npm run api:install
npm run api:dev
```

**Terminal 2 — Redis + Celery worker (for reporting pipeline enqueue):**

```bash
docker compose up -d redis
cd services/api && uv run celery -A celery_app worker --loglevel=info
```

**Terminal 3 — MCP server (for `/support` incident queries):**

```bash
npm run mcp:dev    # from repo root → http://127.0.0.1:8765
```

**Terminal 4 — backoffice:**

```bash
cp ../../.env.example ../../.env   # once
cd uis/backoffice
npm install
npm run dev    # http://localhost:3000
```

Env is loaded from the **repo root** `.env` (see `/.env.example`). The public marketing site is a separate app: `cd uis/website && npm run dev -- -p 3001`.

### API proxy (Next.js rewrites)

Same-origin browser calls use `uis/backoffice/next.config.mjs`:

| Browser path | FastAPI destination |
| ------------ | ------------------- |
| `/api/incidents/*` | `/incidents/*` |
| `/api/suppliers/*` | `/suppliers/*` |
| `/api/inventory/*` | `/inventory/*` |
| `/api/reporting/*` | `/reporting/*` |
| `/api/knowledge/*` | `/knowledge/*` |
| `/api/agent/*` | `/agent/*` |
| `/api/telemetry/*` | `/telemetry/*` |
| `/api/tasks/*` | `/tasks/*` |
| `/auth/*`, `/users/*` | same path on API (first-party cookies) |

Set `BACKOFFICE_API_PROXY_TARGET=http://127.0.0.1:8000` (legacy alias: `INCIDENTS_API_PROXY_TARGET`).

Optional **direct FastAPI** overrides (bypass Next proxy): `NEXT_PUBLIC_INCIDENTS_API_BASE_URL`, `NEXT_PUBLIC_SUPPLIERS_API_BASE_URL`, `NEXT_PUBLIC_INVENTORY_API_BASE_URL`, `NEXT_PUBLIC_REPORTING_API_BASE_URL`, `NEXT_PUBLIC_KNOWLEDGE_API_BASE_URL`, `NEXT_PUBLIC_AGENT_API_BASE_URL`, `NEXT_PUBLIC_TASKS_API_BASE_URL`, `NEXT_PUBLIC_TELEMETRY_API_BASE_URL`, plus `NEXT_PUBLIC_TELEMETRY_ENDPOINT` for the browser telemetry POST path.

External tracker: `NEXT_PUBLIC_TRACKER_API_BASE_URL`.

### Query parameters

- **Browser URLs** use camelCase: `?productId=7&locationId=3`, `?referenceDate=2026-04-23`.
- **FastAPI calls** use snake_case: `?location_id=3`, `?week_start=2026-07-21`.
- Helpers live in `lib/query-params.ts`; API clients in `lib/inventory.ts`, `lib/reporting.ts`, etc. perform the mapping.

## Build

```bash
npm run build && npm run start
```

In production, deploy FastAPI separately and point the proxy (or `NEXT_PUBLIC_*`) at the hosted API.
