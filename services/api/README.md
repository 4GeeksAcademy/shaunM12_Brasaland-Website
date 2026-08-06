# Brasaland API

FastAPI service for Brasaland backoffice: auth, suppliers, inventory, centralized incidents, telemetry, reporting, knowledge (RAG), support agent (LangGraph), and async tasks.

> Parent overview: [../../README.md](../../README.md) · Backoffice proxy map: [../../memory-bank/historical-reference/context-22-route-conventions.md](../../memory-bank/historical-reference/context-22-route-conventions.md)

## Package layout

| Path | Role |
| ---- | ---- |
| `auth/`, `users/`, `mailer/` | JWT auth, users, transactional email |
| `suppliers/` | Supplier directory (TinyDB) |
| `inventory/` | Ingredient catalogue and stock orders (Postgres) |
| `incidents/`, `incident_analyzer/` | Centralized incidents + CSV analyzer |
| `telemetry/` | Event capture, storage, on-demand report |
| `reporting/` | Weekly KPI APIs + pipeline trigger (enqueues Celery; see DEV-55) |
| `knowledge/` | RAG query + reindex (`POST /knowledge/query`, `POST /knowledge/reindex`) |
| `agent/` | LangGraph support agent (`POST /agent/query`; SQLite checkpoint — context-23; MEM-092 memory in `agent/memory/`) |
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
| `QDRANT_URL`, `QDRANT_COLLECTION`, `EMBEDDING_*`, `GENERATION_*` | Knowledge RAG (context-21); see root `.env.example` |
| `AGENT_CHECKPOINT_DB_PATH` | Support Agent LangGraph SQLite checkpointer (default `data/agent/checkpoints.db`) |
| `AGENT_MCP_SERVER_URL` | MCP company-tools URL for incident ops (default `http://127.0.0.1:8765`; context-24) |
| `AGENT_DEFAULT_LOCATION_ID` | Default inventory location when omitted in stock questions (default `1`) |
| `AGENT_MEMORY_*` | Agent memory caps, TTLs, proposal rate limit, injection max (MEM-092; see root `.env.example`) |
| `MCPAUTH_REGISTRATION_SECRET` | Required for MCP server + agent token minting — see root `.env.example` |

API keys come from the environment only — never commit them.

### Backoffice proxy (local dev)

When using `uis/backoffice`, the browser calls same-origin `/api/<domain>/*` (or `/auth/*`, `/users/*`). Next.js rewrites those to this service’s bare mounts (`/incidents`, `/suppliers`, …). See [context-22](../../memory-bank/historical-reference/context-22-route-conventions.md).

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

JWT bearer on supplier, incident, inventory, reporting, knowledge, agent, and most user routes. Open: `GET /api/health` and public auth routes.

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
| Incidents | `/incidents` | CRUD/list/summary/status; `POST …/analyze`, `GET …/results/export` |
| Suppliers | `/suppliers` | CRUD-ish register/list/detail; rate, status, notes patches |
| Inventory | `/inventory` | Products and inbound/outbound orders |
| Telemetry | `/telemetry` | Ingest + report |
| Reporting | `/reporting` | Weekly location KPIs; `POST /reporting/pipeline-runs` (202 + `task_id` via Celery) |
| Knowledge | `/knowledge` | `POST /knowledge/query`, `POST /knowledge/reindex` (Qdrant + LLM env required) |
| Support Agent | `/agent` | `POST /agent/query` — LangGraph + optional `thread_id`; user-approved memory (MEM-092); same RAG env as Knowledge |
| RFP workflow | `/rfp` | Milestone 9 — PDF intake → draft → approval → final document; see [RFP operator guide](#rfp-workflow-milestone-9) |

### RFP workflow (Milestone 9)

Agentic RFP pipeline: upload PDF, classify/route departments, generate drafts, human approval, CEO gate (when contract &gt; $50k USD/year), deterministic final merge.

**Required env:** `DATABASE_URL`, `GENERATION_BASE_URL`, `GENERATION_API_KEY`, `GENERATION_MODEL_ID`. Optional: `RFP_CHECKPOINT_DB_PATH` (LangGraph SQLite checkpoints), `RFP_GENERATION_USE_RAG=true` (Qdrant enrichment, off by default).

**Seed PDFs:** `assets/milestone-9/` — seed #1 (Sunset Bay, CEO path), #2 (Andes Tech, no CEO), #3 (discarded franchise).

**Smoke / E2E (no HTTP):**

```bash
cd services/api && uv run python ../../scripts/rfp_intake_smoke.py --seed 2
cd services/api && uv run python ../../scripts/rfp_e2e_smoke.py --seed 2
cd services/api && uv run python ../../scripts/rfp_e2e_smoke.py --seed 1   # CEO path
```

**Key routes:** `POST /rfp/tickets` (upload), `GET /rfp/tickets/{id}`, `POST …/draft`, `POST …/sections/{dept}/decision`, `GET …/trace`, `GET …/final-document`.

**Artifacts:** source PDF and runtime `final_proposal.md` mirror under `data/raw/intakes/{ticket_id}/` (gitignored). Tracked examples: [`docs/rfp/examples/`](../../docs/rfp/examples/README.md).

**Tests:**

```bash
cd services/api && uv run pytest tests/test_rfp_approval_api.py tests/pipelines/test_rfp_e2e.py -q
```

Spec: [context-27 P1/P2/P3](../memory-bank/historical-reference/context-27-milestone-9-rfp-intake-routing-p1.md) companions in `memory-bank/historical-reference/`.

### Agent memory module (`agent/memory/`)

Postgres-backed episodic store with audit log. Graph nodes: `resolve_memory_proposal`, `read_memory`, `memory_ack` / `memory_reject`. Design: [docs/agent/memory-design.md](../../docs/agent/memory-design.md).

| File | Role |
| ---- | ---- |
| `store.py` | `read_memory()`, `write_memory()`, `log_proposal()` |
| `proposal.py`, `patterns_proposal.py` | Rule-first approve/reject/edit classifier (P26-L9) |
| `denylist.py`, `keys.py`, `schemas.py` | Write gates and allowlists |
| `proposal_inference.py` | Infer proposal when LLM omits JSON |
| `correction_intent.py`, `location_hint.py` | Correction detection and location scoping |
| `models.py` | SQLModel tables (`agent_memory_entries`, `agent_memory_audit_log`) |

**Tests:** `uv run pytest tests/pipelines/test_agent_memory*.py tests/test_agent_api.py -q`

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

Holdout metrics (2024–2025 test window) include **MAPE** (~6% avg. forecast error) alongside MSE, **PSI (train→holdout drift)**, Gini, and **K2 (D'Agostino on residuals)** — see `data/forecasting/evaluate.py` and V4 in the notebook.

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
