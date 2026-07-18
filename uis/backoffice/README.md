# Brasaland Backoffice

Internal Next.js + TypeScript ops app (incidents, suppliers, inventory, reporting, …).

> Parent overview: [../../README.md](../../README.md) · API: [../../services/api/README.md](../../services/api/README.md)

## Main routes

| Path | Purpose |
| ---- | ------- |
| `/` | Executive Assistant talent pipeline (4Geeks tracker) |
| `/candidates/[id]` | Candidate detail |
| `/data-processing` | Milestone 2 ops dashboard (`src/` logic) |
| `/incidents` | Incident manager + CSV analyzer |
| `/suppliers` | Supplier directory |
| `/inventory` | Ingredient inventory |
| `/reporting` | Weekly location KPI dashboard (`POST /reporting/pipeline-runs` returns `task_id`; needs Redis + Celery worker — see API README) |

Pages that call the API need FastAPI on port 8000. For **Run pipeline** on `/reporting`, also start Redis and the Celery worker ([services/api/README.md](../../services/api/README.md#celery-worker-dev-55)).

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

**Terminal 3 — backoffice:**

```bash
cp ../../.env.example ../../.env   # once
cd uis/backoffice
npm install
npm run dev    # http://localhost:3000
```

Incidents/suppliers/inventory/reporting are proxied to FastAPI via `next.config.mjs`. Env is loaded from the **repo root** `.env` (see `/.env.example`).

Useful vars: `BACKOFFICE_API_PROXY_TARGET` / `INCIDENTS_API_PROXY_TARGET` (default `http://127.0.0.1:8000`), optional `NEXT_PUBLIC_*_API_BASE_URL` to bypass the proxy, `NEXT_PUBLIC_TRACKER_API_BASE_URL` for the tracker.

## Build

```bash
npm run build && npm run start
```

In production, deploy FastAPI separately and point the proxy (or `NEXT_PUBLIC_*`) at the hosted API.
