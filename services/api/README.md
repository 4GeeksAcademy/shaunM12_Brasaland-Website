# Brasaland API

FastAPI service for Brasaland backoffice: auth, suppliers, inventory, centralized incidents, telemetry, and reporting.

> Parent overview: [../../README.md](../../README.md)

## Package layout

| Path | Role |
| ---- | ---- |
| `auth/`, `users/`, `mailer/` | JWT auth, users, transactional email |
| `suppliers/` | Supplier directory (TinyDB) |
| `inventory/` | Ingredient catalogue and stock orders (Postgres) |
| `incidents/`, `incident_analyzer/` | Centralized incidents + CSV analyzer |
| `telemetry/` | Event capture, storage, on-demand report |
| `reporting/` | Weekly KPI APIs + pipeline trigger |
| `job_runner/` | Nightly job status (`reporting.job_runs`) — used by `scripts/nightly_export.py` |
| `seeds/` | Demo/bootstrap loaders (suppliers, inventory, incidents, telemetry) |
| `config.py`, `database.py` | Env / TinyDB + Postgres helpers |

Uses **[uv](https://docs.astral.sh/uv/)**. Venv: `services/api/.venv` (never commit).

## Setup

```bash
cd services/api
uv sync
# or from repo root: npm run api:install
```

### Environment

Copy the repo root template and set secrets:

```bash
cp ../../.env.example ../../.env
# JWT_SECRET_KEY required — e.g. python -c "import secrets; print(secrets.token_hex(32))"
```

| Variable | Purpose |
| -------- | ------- |
| `JWT_SECRET_KEY` | Required; API fails closed if missing |
| `DATABASE_URL` | Postgres/Supabase for inventory, incidents, telemetry, reporting |
| `EMAIL_PROVIDER` | `console` (default) / `resend` / `sendgrid` |
| `EMAIL_FROM`, `RESEND_API_KEY`, `SENDGRID_API_KEY` | Mail sender config |
| `PASSWORD_RESET_EXPIRES_MINUTES`, `RESET_REQUESTS_PER_HOUR` | Reset token / rate limits |

API keys come from the environment only — never commit them.

## Run

```bash
npm run api:dev    # from repo root → http://127.0.0.1:8000
# or: uv run uvicorn main:app --reload --port 8000
```

Swagger UI: `/docs` (Authorize with a login token for protected routes).

## Seeds

Loaders live under `seeds/`. Startup auto-seeds empty suppliers TinyDB and empty inventory.

```bash
npm run api:seed              # suppliers
npm run api:inventory-seed
npm run api:incidents-seed
npm run api:telemetry-seed
```

Nightly CSV export + pipeline trigger is **outside** this process — see [scripts/README.md](../../scripts/README.md) (`npm run api:nightly-export`).

## Authentication

JWT bearer on supplier, incident, inventory, reporting, and most user routes. Open: `GET /api/health` and public auth routes.

| Method | Path | Notes |
| ------ | ---- | ----- |
| `POST` | `/auth/register` | `{email, password}` → token |
| `POST` | `/auth/login` | form: `username`=email, `password` |
| `GET` | `/auth/me` | current user |
| `POST` | `/auth/forgot-password` | always `200`; rate-limited |
| `POST` | `/auth/reset-password` | `{token, new_password}` |

`/users`: `POST` public; other methods need a token (`PUT` self or admin).

## Main endpoint groups

| Area | Base | Highlights |
| ---- | ---- | ---------- |
| Incidents | `/api/incidents` | CRUD/list/summary/status; `POST …/analyze`, `GET …/results/export` |
| Suppliers | `/api/suppliers` | CRUD-ish register/list/detail; rate, status, notes patches |
| Inventory | `/inventory` | Products and inbound/outbound orders |
| Telemetry | `/telemetry` | Ingest + report |
| Reporting | `/reporting` | Weekly location KPIs; `POST /reporting/pipeline-runs` (202) |
| Health | `/api/health` | Liveness |

## Tests

```bash
npm run api:test
# or: uv run pytest tests/ -q
```
