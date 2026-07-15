# Context 17 — Background Processes: Nightly Telemetry Script

**Ticket:** DEV-53 — Nightly Telemetry Script  
**Type:** Background orchestration (independent of FastAPI)  
**Depends on:** Milestone 6 pipeline (`data/pipelines/pipeline.py`, `reporting.pipeline_runs`)  
**Companion:** `docs/pipelines/PIPELINE_DESIGN.md`, context-16 Phase 2/3  

---

## Goal

Ship a **fully independent** nightly process that:

1. Exports the previous UTC day’s `telemetry_events` to CSV under `data/raw/` (backup/audit only).
2. Triggers the Milestone 6 weekly location pipeline as a **subprocess**.
3. Records each execution in `reporting.job_runs` with a strict lifecycle so no run stays a zombie `processing` row.

The script must never block API endpoints or run on FastAPI’s main thread.

---

## Locked decisions (D1–D11)

| ID | Topic | Lock |
| -- | ----- | ---- |
| D1 | Pipeline trigger | Subprocess: `cd services/api && uv run python ../../data/pipelines/pipeline.py` (default `use_prefect_engine=False` = course `--no-prefect`). Optional env override for the command (Docker). Do **not** invent `telemetry_kpi_daily`. |
| D2 | Status module | `services/api/job_runner/` (create / update / query helpers) |
| D3 | Table | `reporting.job_runs` + `ensure_job_runs_schema()` (same ensure pattern as reporting; no Alembic required) |
| D4 | Schedule | **Only** cron/worker runs `scripts/nightly_export.py`. Do not also deploy a separate Prefect/OS cron for the pipeline alone. **Docker worker sidecar** in compose (same image/env as backend). |
| D5 | Date vs cron | `target_date` = yesterday **UTC** (`datetime.now(timezone.utc).date() - timedelta(days=1)`). Cron: `0 2 * * *` with `TZ=America/Bogota`. Document UTC-vs-Bogota edge in PR. |
| D6 | Idempotency key | **UNIQUE** `(job_name, target_date)`; retries **UPDATE** the same row in place |
| D7 | Stale lock | If `status=processing` and `started_at` older than **2 hours**, mark `failed` (stale-lock message) then allow reclaim. No second lock table/column. |
| D8 | Export filter | Half-open UTC range on `telemetry_events.timestamp`: `[target_date, target_date+1day)`. Empty day → write **header-only** CSV. |
| D9 | File vs DB | **Completed** row = source of truth → skip export **and** pipeline. File exists alone → skip CSV rewrite only; still run pipeline if not completed. |
| D10 | Gitignore | Add `data/raw/*.csv` (keep `!data/raw/.gitkeep`) |
| D11 | API POST | Keep `POST /reporting/pipeline-runs` for manual runs. Nightly does **not** call HTTP. Manual runs do **not** write `job_runs`. |

---

## Architecture note — `job_runs` ≠ `pipeline_runs`

| Table | Layer | What it records |
| ----- | ----- | --------------- |
| `reporting.job_runs` | Nightly orchestration (this context) | CSV export, pipeline subprocess, lock, per-day idempotency |
| `reporting.pipeline_runs` | Internal ETL (Milestone 6) | Extract/transform/load, watermarks, rows processed |

CSV under `data/raw/telemetry_YYYY-MM-DD.csv` is a **backup**, not pipeline input. The pipeline continues to read `telemetry_events` via SQL — **do not** wire the pipeline to consume the export file.

---

## State machine

```text
pending → processing → completed
                    ↘ failed
```

| Status | When | Role |
| ------ | ---- | ---- |
| `pending` | Row created before work | Queued |
| `processing` | Set at start of execution, before work | **Distributed lock** (only lock mechanism) |
| `completed` | All steps succeeded | Releases lock; idempotent skip target |
| `failed` | Any caught exception / stale recovery | Releases lock; must never leave `processing` |

**Rules**

- If another instance sees an active `processing` lock for `job_name=nightly_export` (non-stale), **abort silently** and log cancellation.
- If `completed` already exists for `(nightly_export, target_date)`, skip as duplicate (no re-export, no pipeline).
- Every unhandled exception → `failed` + `error_message` + ERROR log; no zombie `processing`.

---

## Data model — `reporting.job_runs`

| Field | Notes |
| ----- | ----- |
| `id` | Primary key |
| `job_name` | e.g. `nightly_export` |
| `target_date` | `date` — required for per-day idempotency |
| `status` | `pending` \| `processing` \| `completed` \| `failed` |
| `started_at` | Set when entering `processing` |
| `finished_at` | Set on `completed` / `failed` |
| `error_message` | Exception text on failure (nullable) |
| `created_at` | Row creation time |

**Constraint:** UNIQUE `(job_name, target_date)` (satisfies efficient lookup; stronger than index-only).

Create via SQLModel + `ensure_job_runs_schema()` (extend or mirror `ensure_reporting_schema`). Do not merge with `pipeline_runs`.

---

## Must implement

### `services/api/job_runner/`

| Piece | Responsibility |
| ----- | ---------------- |
| Model / ensure schema | `JobRun` + `ensure_job_runs_schema` |
| Repository API | Create/upsert pending; claim → `processing`; complete; fail; `has_processing_lock`; `has_completed_for_date`; stale-processing recovery (D7) |
| Logging helpers | INFO for start/finish/skip; ERROR for exceptions; include timestamp, job name, status |

### `scripts/nightly_export.py`

| Step | Spec |
| ---- | ---- |
| Resolve date | `TARGET_DATE=YYYY-MM-DD` env **or** UTC yesterday (D5) |
| Claim / lock | Via `job_runner`: abort if non-stale `processing`; skip if `completed` for date |
| Export | Write `data/raw/telemetry_YYYY-MM-DD.csv` only if missing; filter D8; header-only if empty |
| Pipeline | Subprocess per D1 after export step (or after skip-rewrite) |
| Finalize | `completed` or `failed` with timestamps / error |
| CLI | `python scripts/nightly_export.py` (and documented Docker/worker equivalent) |

### Trigger (Docker worker)

| Item | Spec |
| ---- | ---- |
| Compose | Worker service: same image/env as backend; does **not** run uvicorn |
| Cron | `0 2 * * *` America/Bogota → `nightly_export.py` |
| Independence | No APScheduler, `@repeat_every`, or lifespan hooks on the API |
| PR body | Document cron expression + why worker/cron (not in-API scheduler) |

### Repo hygiene

- `.gitignore`: `data/raw/*.csv`
- Optional: npm/uv docs one-liner for manual run + `TARGET_DATE`

---

## Explicit non-goals

- Running nightly inside FastAPI (lifespan, APScheduler, background on request thread as the sole scheduler)
- Second lock mechanism (Redis, flock, extra column) beyond `processing` status (+ stale timeout recovery)
- Feeding CSV into the Milestone 6 pipeline
- Merging `job_runs` into `pipeline_runs`
- Replacing or removing `POST /reporting/pipeline-runs`
- Inventing `data.pipelines.telemetry_kpi_daily`

---

## Acceptance criteria

- [x] `scripts/nightly_export.py` runnable from CLI; independent of API process
- [x] Second concurrent start aborts silently when non-stale `processing` exists
- [x] Failures end as `failed` with `error_message`; no leftover `processing` after handled failure
- [x] Stale `processing` (>2h) recoverable per D7
- [x] Idempotent: second run same `target_date` after `completed` skips export + pipeline
- [x] CSV path `data/raw/telemetry_YYYY-MM-DD.csv`; skipped if file already exists (rewrite only)
- [x] Pipeline invoked via M6 subprocess (D1); writes its own `pipeline_runs`
- [x] `reporting.job_runs` with UNIQUE `(job_name, target_date)` and ensure-schema
- [x] `job_runner` module under `services/api/job_runner/`
- [x] Docker worker + cron documented; PR justifies scheduler choice
- [x] `TARGET_DATE` override works for tests
- [x] INFO/ERROR logs include timestamp, job name, status
- [x] `data/raw/*.csv` gitignored

---

## Evaluation map (rubric → evidence)

| Rubric theme | Evidence |
| ------------ | -------- |
| Independent process | Worker/cron → `scripts/nightly_export.py`; no API scheduler |
| Single-flight via `processing` | `has_processing_lock` + silent abort |
| No zombie `processing` | try/except/finally → `failed`; stale recovery |
| Idempotent per day | UNIQUE + `has_completed_for_date` |
| Lifecycle logged | `job_runs` status transitions + structured logs |
| Script in `scripts/` | `scripts/nightly_export.py` |
| Status logic in `services/` | `services/api/job_runner/` |
| CSV backup ≠ pipeline input | Export to `data/raw/`; pipeline still SQL on `telemetry_events` |
| Trigger documented | Compose worker + cron in PR |

---

## Implementation order (suggested)

1. `job_runner` model + ensure schema + repository (claim, complete, fail, stale)
2. CSV export helper (UTC window, header-only empty)
3. `scripts/nightly_export.py` orchestration + subprocess (D1)
4. `.gitignore` CSV rule
5. Docker worker + cron wiring
6. Tests: lock abort, completed skip, failure → `failed`, `TARGET_DATE`, stale reclaim
7. PR body: cron expression + justification

---

## Verification notes

```bash
# Manual (from repo patterns)
TARGET_DATE=2026-07-14 python scripts/nightly_export.py
TARGET_DATE=2026-07-14 python scripts/nightly_export.py   # expect skip / duplicate

# Confirm layers
# job_runs: nightly_export + target_date + completed|failed
# pipeline_runs: brasaland_weekly_location_performance_pipeline row(s)
# file: data/raw/telemetry_2026-07-14.csv
```
