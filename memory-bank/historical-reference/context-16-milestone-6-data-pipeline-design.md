# Context 16 — Milestone 6 Phase 1: Data Pipeline Design

**Milestone:** 6 — Data Pipeline (Phase 1 of 3)  
**Phase:** Design only (`PIPELINE_DESIGN.md`)  
**Authority:** Course telemetry floor (`schemaVersion` 2); Milestone 5 inventory unchanged  
**Shared design:** `docs/pipelines/PIPELINE_DESIGN.md`  
**Next:** `context-16-milestone-6-resilient-data-pipeline.md` (Phase 2)

---

## Course context (business problem)

Brasaland needs a weekly answer for Mariana and Felipe: **purchase cost, waste cost, waste ratio, stockouts, and price alerts by location** — not only the quantity-focused technical report at `GET /telemetry/report`.

This phase produces the design document that later Phases implement in Prefect.

---

## Locked decisions used by this phase

| ID | Decision |
| -- | -------- |
| P1 | `reporting.weekly_location_performance`, unique `(location_id, week_start)` |
| P2 | APIs live under `services/api/reporting/` |
| P3 | Integer `location_id` 1–14 |
| P4 | ISO week; `week_start` = Monday UTC; nightly ~02:00 `America/Bogota` |
| P5 | Waste cost uses `unit_cost` on `stock_waste_registered` |
| P6 | Missing cost → skip from cost sums; log counts |
| P7 | Leave `/telemetry/report` alone |
| P8 | Three context-16 phase files + shared design |
| P9 | Prefect vocabulary in design §10 |
| P10 | Capture RFP Qs answered in design; pipeline implements upsert + run log only |
| P11 | `reporting.pipeline_runs` for audit |
| L1–L7 | Phase 2 locks in design §2 (lookback 2, sparse, ensure-schema, 202, Prefect in api, no lock, JWT) |


Full tables, ETL diagram, KPIs, Prefect names, and RFP answers: **`docs/pipelines/PIPELINE_DESIGN.md`**.

Pointer: `data/pipelines/PIPELINE_DESIGN.md` → `docs/pipelines/PIPELINE_DESIGN.md`.

---

## Deliverables (Phase 1)

| Deliverable | Location | Status |
| ----------- | -------- | ------ |
| Canonical pipeline design | `docs/pipelines/PIPELINE_DESIGN.md` | Done (this iteration) |
| Data folder pointer | `data/pipelines/PIPELINE_DESIGN.md` | Keep in sync |
| Phase contexts (2–3 scaffolding) | `context-16-milestone-6-resilient-data-pipeline.md`, `context-16-milestone-6-pipeline-subflows-tests.md` | Done |

**Out of scope for Phase 1 code:** Prefect runtime, migrations applied to prod, reporting route handlers, dashboard UI.

---

## Prerequisite (telemetry — outside ETL itself)

`stock_waste_registered` must allow optional `unit_cost` (and emit it when known) so waste cost KPI is computable. Tracked alongside this design; does not modify `analysis.py` or quantity report contracts beyond additive schema/allowlist.

---

## Acceptance criteria (Phase 1)

- [x] Design names the five KPIs and maps them to course-floor events  
- [x] Design specifies extract → transform → load and destination DDL  
- [x] Design covers duplicates / late events / re-run via upsert + `pipeline_runs`  
- [x] Design states schedule, CLI path, and reporting API surface (to implement later)  
- [x] Capture-layer RFP questions answered as design text (P10)  
- [x] Prefect flow/task/block names locked (P9)  

---

## Non-goals

- Changing Milestone 5 inventory business rules  
- Rewriting `GET /telemetry/report` Pandas KPIs (P7)  
- Implementing Phase 2/3 code in this phase  
