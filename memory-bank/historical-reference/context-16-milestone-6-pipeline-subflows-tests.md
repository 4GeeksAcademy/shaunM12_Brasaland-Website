# Context 16 — Milestone 6 Phase 3: Subflows, Tests & Reporting Dashboard

**Milestone:** 6 — Data Pipeline (Phase 3 of 3)  
**Phase:** Structure for course eval, automated tests, backoffice `/reporting`  
**Depends on:** Phase 2 resilient pipeline  

---

## Goal

Refactor the Phase 2 pipeline into clear extract / transform / load **subflows**, add `tests/pipelines/test_pipeline.py`, and ship a business-facing dashboard at `uis/backoffice` `/reporting` that reads `reporting.weekly_location_performance` (and run status).

---

## Must implement

### Subflows (names locked — P9)

| Subflow | Responsibility |
| ------- | ---------------- |
| `extract_telemetry_events_flow` | Read `telemetry_events` window; optional `data/raw/` artifact |
| `transform_weekly_location_performance_flow` | Orchestrate the five KPI tasks |
| `load_weekly_location_performance_flow` | Upsert KPI table + call `record_pipeline_run` |
| `export_pipeline_eval_flow` (optional) | Eval/export; parent uses `return_state=True` |

Main flow remains `brasaland_weekly_location_performance_pipeline` and composes the above.

### Tests

| Path | Coverage |
| ---- | -------- |
| `tests/pipelines/test_pipeline.py` | Happy path, missing-cost skip, upsert idempotency, at least one transform unit |
| Existing fixtures | Prefer course-floor v2 event shapes |

### Dashboard

| Item | Spec |
| ---- | ---- |
| Route | `/reporting` in backoffice |
| Data | Prefer `GET /reporting/weekly-location-performance` (+ latest run) |
| Labels | Use KPI names: Purchase Cost, Waste Cost, Waste Ratio, Stockout Frequency, Price Alert Frequency |
| Period | ISO week selector / default latest `week_start` |
| Audience | Mariana / Felipe — business language, not event dump |

---

## Explicit non-goals

- Changing telemetry capture contracts beyond what Phase 2 already required  
- Redesigning `GET /telemetry/report`  
- FX conversion across COP/USD  

---

## Acceptance criteria (Phase 3)

- [ ] Main flow invokes named extract/transform/load subflows  
- [ ] `tests/pipelines/test_pipeline.py` passes in CI / local  
- [ ] Backoffice `/reporting` shows weekly KPI rows (or empty state + last run status)  
- [ ] Design checklist in `PIPELINE_DESIGN.md` remains accurate  

---

## Verification notes

Manual: trigger `POST /reporting/pipeline-runs`, wait for completion, refresh `/reporting`, confirm grain uniqueness after second trigger.
