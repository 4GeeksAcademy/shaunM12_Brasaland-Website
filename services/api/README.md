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
| `reporting/` | Weekly KPI APIs + pipeline trigger (enqueues Celery; see DEV-55) |
| `celery_app.py` | Celery app (Redis broker + result backend) + async pipeline task |
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
| `REDIS_URL` | Celery broker + result backend (DEV-55); local `redis://127.0.0.1:6379/0`, Compose `redis://redis:6379/0` |
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

### Celery worker (DEV-55)

`POST /reporting/pipeline-runs` enqueues work; a **separate** worker process consumes the queue. Design: [context-18](../../memory-bank/historical-reference/context-18-message-queues-async-tasks.md).

**Start (local)**

```bash
# Terminal 1 — Redis
docker compose up -d redis

# Terminal 2 — API
npm run api:dev

# Terminal 3 — worker (must connect to REDIS_URL before relying on enqueue)
cd services/api
uv run celery -A celery_app worker --loglevel=info
```

**Start (Compose)**

```bash
docker compose up -d redis celery-worker
# Optional monitor: docker compose up -d flower  → http://127.0.0.1:5555
```

**Stop**

- Local worker: `Ctrl+C` in the worker terminal
- Compose: `docker compose stop celery-worker` (Redis/Flower can stay up)
- Stopping the API does **not** stop the worker or drop queued Redis messages

Course equivalent: `celery -A services.celery_app worker` → this repo uses `-A celery_app` from `services/api`.

## Seeds

Loaders live under `seeds/`. Startup auto-seeds empty suppliers TinyDB and empty inventory.

```bash
npm run api:seed              # suppliers
npm run api:inventory-seed
npm run api:incidents-seed
npm run api:telemetry-seed
```

Nightly CSV export + pipeline trigger is **outside** this process and **outside** Celery — see [scripts/README.md](../../scripts/README.md) (`npm run api:nightly-export`).

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
| Reporting | `/reporting` | Weekly location KPIs; `POST /reporting/pipeline-runs` (202 + `task_id` via Celery) |
| Tasks | `/tasks` | `GET /tasks/{task_id}` — Celery status (`pending` / `started` / `success` / `failure`) |
| Health | `/api/health` | Liveness |

## Sales forecasting (context-19)

Random Forest monthly revenue forecast on **consolidated** market rows only. Dataset: `data/raw/brasaland_sales.csv`. Plan: [context-19](../memory-bank/historical-reference/context-19-sales-forecasting-regression.md). Metrics guide (MSE, **MAPE**, PSI, Gini, K2): [docs/forecasting/README.md](../docs/forecasting/README.md). Business context: [CONTEXT-brasaland.md](../docs/forecasting/CONTEXT-brasaland.md).

**Python packages** (in `pyproject.toml` via `uv`; installed with `uv sync`):

| Package | Purpose |
| ------- | ------- |
| `scikit-learn` | Random Forest, metrics, `StandardScaler` |
| `pandas` | CSV load and feature frames |
| `matplotlib` | Charts V1–V8 |
| `jupyter`, `ipykernel` | `notebooks/sales_forecasting.ipynb` |

Install or refresh:

```bash
cd services/api
uv sync
# adds ML stack if missing: uv add scikit-learn matplotlib jupyter ipykernel
```

**Jupyter kernel** (one-time per machine):

```bash
cd services/api
uv run python -m ipykernel install --user --name brasaland-forecasting --display-name "Brasaland Forecasting (Python 3.12)"
```

Open the notebook and select kernel **Brasaland Forecasting (Python 3.12)**.

```bash
# from repo root
cd services/api && uv run jupyter notebook ../../notebooks/sales_forecasting.ipynb
```

Holdout metrics (2024–2025 test window) include **MAPE** (~6% avg. forecast error) alongside MSE, PSI, Gini, and K2 — see `data/forecasting/evaluate.py` and V4 in the notebook.

Tests:

```bash
uv run pytest tests/pipelines/test_sales_forecast_split.py \
  tests/pipelines/test_sales_forecast_model.py \
  tests/pipelines/test_sales_forecast_visualize.py -q
```

## Tests

```bash
npm run api:test
# or: uv run pytest tests/ -q
```
