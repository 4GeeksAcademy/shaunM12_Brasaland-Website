# Context 16 — Milestone 6 Phase 2: Resilient Data Pipeline

**Milestone:** 6 — Data Pipeline (Phase 2 of 3)  
**Phase:** Implement Prefect pipeline + reporting APIs + run audit  
**Depends on:** Phase 1 design (`docs/pipelines/PIPELINE_DESIGN.md`)  
**Next:** `context-16-milestone-6-pipeline-subflows-tests.md` (Phase 3)

---

## Goal

Ship a schedulable Prefect 3 flow that extracts course-floor events from `telemetry_events`, computes the five weekly location KPIs, upserts `reporting.weekly_location_performance`, and records `reporting.pipeline_runs` — then expose read/trigger endpoints under `services/api/reporting/`.

---

## Must implement

| Item | Spec |
| ---- | ---- |
| Dependency | `uv add 'prefect>=3'` (or project-equivalent) |
| Entry | `data/pipelines/pipeline.py` — main flow `brasaland_weekly_location_performance_pipeline` |
| Transforms | Modules under `data/process/` matching § KPIs; tasks named per design §10 |
| Load | Upsert `reporting.weekly_location_performance` on `(location_id, week_start)` |
| Audit | Insert/update `reporting.pipeline_runs` (≥5 metadata fields) |
| Retry | Retries + delay on DB/network tasks |
| Optional failure | At least one optional eval/export/notify path with `return_state=True` so its failure does not fail the main run |
| Cache | `cache_key_fn` + `cache_expiration` (≤ 1 hour) on at least one expensive transform |
| Blocks | `brasaland-postgres`, `brasaland-pipeline-settings` (`data/pipelines/blocks.py`; env fallback OK) |
| CLI | From `services/api`: `uv run python ../../data/pipelines/pipeline.py` |
| Schedule | Cron `0 2 * * *` ~02:00 `America/Bogota` (`NIGHTLY_CRON_BOGOTA`) |
| API | `GET /reporting/weekly-location-performance`, `GET /reporting/pipeline-runs/latest`, `POST /reporting/pipeline-runs` in `services/api/reporting/` |

Reuse transforms from `data/process/` in services via imports — **do not nest ETL logic inside FastAPI handlers**.

---

## Explicit non-goals (Phase 2)

- Do not write to `telemetry_events`  
- Do not change `services/api/telemetry/analysis.py` or `GET /telemetry/report`  
- Do not require Phase 3 subflows layout or full `tests/pipelines/test_pipeline.py` suite yet (smoke OK)  
- Do not implement capture-layer `eventId` upsert (design-only per P10)

---

## Migrations

Add Alembic (or project migration path) for:

- `reporting` schema  
- `reporting.weekly_location_performance`  
- `reporting.pipeline_runs`  

DDL source of truth: `docs/pipelines/PIPELINE_DESIGN.md` §7.

---

## Acceptance criteria (Phase 2)

- [x] Pipeline module + transforms + named Prefect tasks/flows exist
- [x] Upsert on `(location_id, week_start)` + `pipeline_runs` audit fields
- [x] Missing `unit_cost` skipped from cost KPIs (unit-tested)
- [x] Reporting GET/POST (202) mounted under `/reporting` with JWT
- [x] Retry + `return_state=True` optional eval export + 1h cache key on purchase transform
- [x] End-to-end run against live Supabase seed window (`DATABASE_URL` CLI run completed)
- [x] Second live run confirms upsert without duplicate grains (6 runs → still **1** KPI grain for `(location_id=3, week_start=2026-07-13)`)

## Phase 2 evaluation map (course rubric → evidence)

| Rubric theme | Evidence |
| ------------ | -------- |
| Prefect 3 dependency | `services/api/pyproject.toml` → `prefect>=3` |
| `data/pipelines/pipeline.py` entry | `brasaland_weekly_location_performance_pipeline` (+ CLI via `run_weekly_pipeline_core`) |
| Extract / transform / load tasks | Named tasks in `pipeline.py`; transforms in `data/process/weekly_location_kpis.py` |
| Idempotent load | `ON CONFLICT (location_id, week_start)` |
| Run metadata | `reporting.pipeline_runs` (≥5 fields) |
| Retries | extract/load (+ waste) `retries` + `retry_delay_seconds` |
| Optional non-failing path | `export_pipeline_eval_flow(..., return_state=True)` on Prefect-engine path |
| Cache ≤1h | `transform_purchase_cost` `cache_key_fn` + `cache_expiration` |
| Blocks | `data/pipelines/blocks.py` → `brasaland-postgres`, `brasaland-pipeline-settings` (env fallback OK locally) |
| Schedule | Documented cron `0 2 * * *` America/Bogota (`NIGHTLY_CRON_BOGOTA` / settings.schedule_cron) |
| Reporting APIs | `/reporting/weekly-location-performance`, `/pipeline-runs/latest`, `POST /pipeline-runs` → 202 |
| CLI | `cd services/api && uv run python ../../data/pipelines/pipeline.py` |

## Phase 2 implementation locks

See `docs/pipelines/PIPELINE_DESIGN.md` §2 (L1–L7): lookback 2, sparse, ensure-schema, 202 background, Prefect in `services/api`, no lock, JWT like inventory.

---

## Verification notes

Prefer a small fixture set of v2 telemetry events covering each of the five source event types, including one waste event without `unit_cost` (must not inflate waste cost).

**Operator verification (2026-07-14):** CLI completed repeatedly; `reporting.weekly_location_performance` stayed at **1** row while `reporting.pipeline_runs` grew — upsert confirmed. Sparse eval JSON may show only CO locations when US events lack `unit_cost` / non-cost signals (by design, not a Colombia-only filter).
