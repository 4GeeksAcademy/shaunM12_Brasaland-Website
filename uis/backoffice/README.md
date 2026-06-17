# Brasaland Backoffice

Internal app built with Next.js + TypeScript.

## Routes

- `/`: Executive Assistant talent pipeline (4Geeks tracker API)
- `/candidates/[id]`: Candidate detail, notes, and status updates
- `/data-processing`: Milestone 2 operations dashboard and aggregated reports
- `/incidents`: Incident CSV upload and analysis (requires local FastAPI)
- `/suppliers`: Procurement supplier directory (requires local FastAPI)

## Integration with Milestone 2

Business logic is imported from the original monorepo module in [src](../../src), without copying code.
The data-processing page renders computed outputs (reports, filters, searches) in the interface.

## Development

Backoffice pages that call incidents or suppliers need the Python API running on port 8000.

**Terminal 1 — from repo root:**

```bash
npm run api:install   # once
npm run api:seed      # once
npm run api:dev       # http://127.0.0.1:8000
```

**Terminal 2 — backoffice:**

```bash
npm install
cp .env.example .env.local
npm run dev           # http://localhost:3000
```

Open:

- http://localhost:3000/suppliers
- http://localhost:3000/incidents
- http://localhost:3000/data-processing
- http://localhost:3000/

The candidate tracker uses the external 4Geeks API by default in development. Incidents and suppliers are proxied to the local FastAPI service via `next.config.mjs` rewrites.

## Environment variables

See [.env.example](./.env.example):

- `NEXT_PUBLIC_TRACKER_API_BASE_URL` — candidate tracker API base URL
- `BACKOFFICE_API_PROXY_TARGET` or `INCIDENTS_API_PROXY_TARGET` — FastAPI origin (default `http://127.0.0.1:8000`)
- `NEXT_PUBLIC_INCIDENTS_API_BASE_URL` / `NEXT_PUBLIC_SUPPLIERS_API_BASE_URL` — optional direct API base URLs (bypass Next.js proxy)

## Build

```bash
npm run build
npm run start
```

For production, deploy FastAPI separately and set the proxy target or `NEXT_PUBLIC_*_API_BASE_URL` variables to the hosted API origin.
