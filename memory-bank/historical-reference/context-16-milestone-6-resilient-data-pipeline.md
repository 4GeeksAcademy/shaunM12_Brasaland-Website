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
| Blocks | `brasaland-postgres`, `brasaland-pipeline-settings` |
| CLI | `python data/pipelines/pipeline.py` |
| Schedule | Document / configure ~02:00 `America/Bogota` |
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
- [ ] End-to-end run against live Supabase seed window (operator check with `DATABASE_URL`)
- [ ] Second live run confirms upsert without duplicate grains

## Phase 2 implementation locks

See `docs/pipelines/PIPELINE_DESIGN.md` §2 (L1–L7): lookback 2, sparse, ensure-schema, 202 background, Prefect in `services/api`, no lock, JWT like inventory.

---

## Verification notes

Prefer a small fixture set of v2 telemetry events covering each of the five source event types, including one waste event without `unit_cost` (must not inflate waste cost).
