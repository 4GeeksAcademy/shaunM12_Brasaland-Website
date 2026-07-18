# Context 18 — Message Queues and Async Tasks

**Ticket:** DEV-55 — Async Task Queue with Redis and Celery  
**Type:** Producer / consumer queue (API enqueue + independent worker)  
**Depends on:** Milestone 6 reporting pipeline (`reporting.runner.run_weekly_pipeline`, `POST /reporting/pipeline-runs`)  
**Companion:** context-16 Phase 2/3, context-17 (nightly stays separate), `docs/pipelines/PIPELINE_DESIGN.md`  

---

## Goal

Decouple the slowest API-triggered heavy operation from the FastAPI request lifecycle:

1. Add Redis as the Celery broker (and result backend) via Docker Compose.
2. Convert `POST /reporting/pipeline-runs` from an in-process daemon thread to a Celery task.
3. Return `202 Accepted` with a `task_id` immediately; expose `GET /tasks/{task_id}` for status.
4. Run workers as separate processes; monitor with Flower; persist exhausted failures in a DB dead-letter table.

```text
Client → API (Producer) → Redis (Broker) → Worker (Consumer) → Result
```

---

## Locked decisions (D1–D11)

| ID | Topic | Lock |
| -- | ----- | ---- |
| D1 | Celery module path | `services/api/celery_app.py`. Local worker: `cd services/api && uv run celery -A celery_app worker --loglevel=info`. Course path `services/celery_app.py` / `celery -A services.celery_app` is **monorepo-adapted** (same pattern as context-17 → `services/api/job_runner/`). |
| D2 | Heavy operation | Convert **only** `POST /reporting/pipeline-runs`. Task calls `run_weekly_pipeline(lookback_weeks=2)` (or thin wrapper). Remove daemon `threading.Thread`. Leave incident CSV analyze and nightly export alone. |
| D2b | Accept body | `202` with `{ "task_id", "status": "accepted", "message": "…" }` (compat with existing backoffice fields + required `task_id`). |
| D3 | Frontend scope | Minimal backoffice update: extend `PipelineRunAccepted` with `task_id`; keep “Run pipeline” UX; keep polling `GET /reporting/pipeline-runs/latest`. No full task-status UI. |
| D4 | Task status API | Auth-protected `GET /tasks/{task_id}` → `{ task_id, status, result }`. Lowercase statuses: `pending` \| `started` \| `success` \| `failure`. Map Celery: `PENDING`→`pending`, `STARTED`→`started`, `SUCCESS`→`success`, `FAILURE`→`failure`, `RETRY`→`pending`, `REVOKED`→`failure`. Unknown id: Celery’s usual `pending` (document; no special 404). |
| D5 | Retries | `max_retries=2` → **3 total attempts** (1 initial + 2 retries), then DLQ. Exponential backoff; never immediate retry. |
| D6 | DLQ table | New `task_dead_letters` + `ensure_task_dead_letters_schema()`. Columns: `task_id`, `attempt`, `error_message`, `created_at` (+ optional `task_name`). One row per exhausted `task_id`; write **only** when retries exhausted. Do not merge into `job_runs` or `pipeline_runs`. |
| D7 | Timeouts | Pipeline task: `soft_time_limit=600` (10 min), hard `time_limit≈720` (12 min). |
| D8 | Compose + env | Services: `redis` (official image, `6379`, `maxmemory-policy noeviction`), `flower` (`5555`), `celery-worker` (same image as backend, Celery command, not uvicorn). `REDIS_URL` for broker **and** result backend (Docker `redis://redis:6379/0`; local `redis://127.0.0.1:6379/0`). Add to `.env.example`. |
| D9 | Message payload | Queue args = `lookback_weeks=2` only (or empty + default). No CSV bytes, dataframes, or large KPI blobs. Worker loads DB/pipeline itself. Results stay small; ETL truth remains in reporting tables. |
| D10 | Observability | Log each execution: `task_id`, attempt, status, duration. Failures: full error message (+ stack at ERROR). Flower demo: ≥1 completed and ≥1 failed task. Shared logging helper preferred. |
| D11 | Non-goals | See [Explicit non-goals](#explicit-non-goals). |

---

## Architecture note — Celery ≠ nightly ≠ ETL rows

| Layer | What it is | What it is not |
| ----- | ---------- | -------------- |
| Celery + Redis (this context) | On-demand API enqueue for manual pipeline runs; `task_id` status in Redis result backend | Not the nightly scheduler |
| `reporting.job_runs` (context-17) | Nightly orchestration lock / per-day idempotency | Not Celery DLQ |
| `reporting.pipeline_runs` | Milestone 6 ETL run metadata | Not queue/task status |
| `task_dead_letters` | Exhausted Celery failures | Not retry-in-progress state |

Stopping the API must **not** stop `celery-worker` or drop queued Redis messages.

---

## Producer / consumer rules (always apply)

1. **Lightweight messages** — ids/refs only (`lookback_weeks`); worker fetches data.
2. **ACK after success** — Celery confirms after successful completion; failures retry then DLQ.
3. **Every task has a timeout** — soft/hard limits per D7.

---

## Celery status mapping

| Celery state | API `status` |
| ------------ | ------------ |
| `PENDING` | `pending` |
| `STARTED` | `started` |
| `SUCCESS` | `success` |
| `FAILURE` | `failure` |
| `RETRY` | `pending` |
| `REVOKED` | `failure` |

---

## Data model — `task_dead_letters`

| Field | Notes |
| ----- | ----- |
| `id` | Primary key |
| `task_id` | Celery task id (unique preferred — one row per exhausted task) |
| `attempt` | Attempt number when retries were exhausted |
| `error_message` | Failure text |
| `created_at` | Timestamp when recorded |
| `task_name` | Optional; e.g. weekly pipeline task name |

Create via SQLModel + `ensure_task_dead_letters_schema()` in API lifespan (same ensure pattern as `job_runs`).

---

## Must implement

### Dependencies

```bash
cd services/api && uv add celery redis flower
```

### `services/api/celery_app.py`

| Piece | Responsibility |
| ----- | ---------------- |
| Celery app | Broker + result backend from `REDIS_URL` |
| Pipeline task | `@app.task` wrapping `run_weekly_pipeline`; `bind=True`; `max_retries=2`; exponential backoff; soft/hard time limits (D7) |
| Logging | `task_id`, attempt, status, duration; full error on failure |
| DLQ hook | On retries exhausted → insert `task_dead_letters` |

### Docker Compose

| Service | Spec |
| ------- | ---- |
| `redis` | Official image; `6379:6379`; `maxmemory-policy noeviction` |
| `celery-worker` | Same build as `backend`; `uv run celery -A celery_app worker --loglevel=info`; shares `REDIS_URL`, `DATABASE_URL`, data mounts; does **not** run uvicorn |
| `flower` | Port `5555`; same Redis broker |

### API

| Endpoint | Behavior |
| -------- | -------- |
| `POST /reporting/pipeline-runs` | Enqueue task; return `202` + `{ task_id, status, message }` immediately (&lt;200ms independent of ETL) |
| `GET /tasks/{task_id}` | Auth required; `{ task_id, status, result }` from Celery `AsyncResult` |

### Backoffice (minimal)

- Extend `PipelineRunAccepted` with `task_id`
- Keep existing accept messaging + `pipeline-runs/latest` polling

### Docs

- Root + `services/api` READMEs: how to start/stop Redis, worker, Flower (local + Compose)

---

## Explicit non-goals

- Celery worker inside FastAPI lifespan / in-process worker
- Migrating nightly export (`DEV-53` / `nightly-worker`) to Celery
- Merging DLQ into `job_runs` or `pipeline_runs`
- Converting `POST /api/incidents/analyze` (CSV blob) in this context
- Using Redis as a general app cache or session store beyond broker + result backend
- Polished task-status UI beyond D3 minimal backoffice compat

---

## Acceptance criteria

- [x] Redis runs as broker in Docker; API and workers share `REDIS_URL`
- [x] `uv` deps: `celery`, `redis`, `flower` in `services/api`
- [x] `services/api/celery_app.py` configured with Redis broker + result backend
- [x] Worker started and verified connected to broker **before** changing the endpoint
- [x] `POST /reporting/pipeline-runs` enqueues Celery task (no daemon thread); returns `202` with `task_id` (+ compat `status`/`message`)
- [x] `GET /tasks/{task_id}` returns lowercase lifecycle status + `result` when available
- [x] Retries: `max_retries=2`, exponential backoff (no immediate retry)
- [x] After 3 failed attempts, row in `task_dead_letters` with `task_id`, attempt, error, timestamp
- [x] `celery-worker` is a separate process/Compose service; stopping API does not stop worker or lose queued messages
- [x] Queue messages contain only `lookback_weeks` (or empty/default) — no large payloads
- [x] Flower on `:5555` shows queued / in-progress / completed; demo includes ≥1 success and ≥1 failure
- [x] Task logs include `task_id`, attempt, status, duration; failures log full error
- [x] Soft/hard time limits on pipeline task (D7)
- [x] Minimal backoffice `task_id` typing update
- [x] Worker start/stop documented in monorepo README + API README

---

## Evaluation map (rubric → evidence)

| Rubric theme | Evidence |
| ------------ | -------- |
| Redis in Docker; workers connect cleanly | Compose `redis` + worker logs Connected to `REDIS_URL` |
| 202 + `task_id` under 200ms | `POST /reporting/pipeline-runs` enqueues only; timing independent of ETL |
| `GET /tasks/{task_id}` lifecycle | Poll `pending` → `started` → `success` / `failure` |
| Retries with backoff | Forced failure; logs show increasing countdown; no zero-delay retry |
| DLQ after three failures | `task_dead_letters` row: `task_id`, attempt, error |
| Worker ≠ API | Stop API container; worker + Redis queue still alive |
| Lightweight messages | Flower/Redis payload = `lookback_weeks` only |
| Flower demo | ≥1 completed + ≥1 failed task visible |

---

## Implementation order (suggested)

1. `uv add celery redis flower`; add `REDIS_URL` to `.env.example` / config
2. Compose `redis`; start Redis; create `celery_app.py`; start worker; **verify broker connection**
3. Pipeline task + retries + timeouts + structured logging + DLQ model/ensure/hook
4. Swap `POST /reporting/pipeline-runs` to enqueue; add `GET /tasks/{task_id}`
5. Compose `celery-worker` + `flower`
6. Minimal backoffice type/client update
7. README start/stop docs (root + API)
8. Demo: one success + one forced failure (Flower + DLQ row)

---

## Verification notes

```bash
# Redis + worker (local example)
docker compose up -d redis
cd services/api && uv run celery -A celery_app worker --loglevel=info
# Expect: Connected to redis://…

# Enqueue (auth token required)
curl -s -X POST http://127.0.0.1:8000/reporting/pipeline-runs \
  -H "Authorization: Bearer $TOKEN"
# Expect: 202 + task_id quickly

# Status
curl -s http://127.0.0.1:8000/tasks/$TASK_ID \
  -H "Authorization: Bearer $TOKEN"

# Flower
# http://127.0.0.1:5555

# Independence check
# Stop backend; confirm celery-worker still consuming / Redis still holding messages
```

**Course command mapping:** `celery -A services.celery_app worker` ≡ this repo’s `cd services/api && uv run celery -A celery_app worker`.
