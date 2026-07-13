# CONTEXT — Milestone 6 Phase 1: Data Pipeline Design · Brasaland

## AI Engineering - 4Geeks Academy

> **Repository index:** `context-16-milestone-6-data-pipeline-design.md`  
> **Companion docs:** `docs/pipelines/PIPELINE_DESIGN.md`, `docs/telemetry/telemetry-plan.md`, `docs/telemetry/event-schemas.json`  
> **Related context:** `context-15-telemetry-plan.md`, `context-15-telemetry-frontend-capture.md`, `context-15-backend-storage.md`, `context-15-telemetry-report.md`  
> **Later phases (separate files):** resilient Prefect pipeline (Phase 2); subflows and tests (Phase 3)  
> **Type:** Data pipeline design (Milestone 6 Phase 1)  
> **Status:** 🟡 Design deliverable — no orchestration code in this phase

> **Authority rule:** Milestone 5 contexts remain the runtime source of truth for inventory APIs. Context 15 documents remain the source of truth for telemetry events, envelopes, storage (`telemetry_events`), and KPI definitions. This phase designs an additive batch ETL path and must not change Milestone 5 or Context 15 runtime contracts.

---

## Business Objective

Brasaland is a grilled food restaurant chain with 14 locations across Colombia and Florida. Brasaland Digital already captures inventory and backoffice telemetry and can serve on-request KPI reports. Operations needs a signed-off design for how data moves from capture to dashboard-ready facts, with explicit guarantees around idempotency and auditability, before production orchestration work begins.

This phase produces that design (and the folder layout the later phases will use). Implementation of Prefect flows is out of scope here.

---

## Locked Decisions

- **Canonical design doc:** `docs/pipelines/PIPELINE_DESIGN.md` (overall technical design for Milestone 6 Phases 1–3 continuity).
- **Assignment path pointer:** `data/pipelines/PIPELINE_DESIGN.md` links to the canonical docs file.
- **Folder layout (create in this phase):** `data/raw/`, `data/process/`, `data/pipelines/`, `data/eval/` (with `.gitkeep` if empty). Do not move `services/api/data/*.json` (TinyDB) into these folders.
- **Source table:** append-only Postgres/Supabase `telemetry_events` (dual ingest paths unchanged from Context 15).
- **Load targets (Postgres):** `kpi_daily_consumption`, `kpi_stock_out_frequency`, `kpi_waste_loss_ratio`, plus `pipeline_runs`.
- **KPI continuity:** same three Phase 1 KPIs as Context 15 (`daily_consumption_by_ingredient_and_location`, `stock_out_frequency`, `waste_loss_ratio`). Do not invent parallel KPI names.
- **Updates / duplicates:** never UPDATE raw `telemetry_events`. Upsert KPI aggregate rows by grain (see design doc).
- **Schedule:** daily ~02:00 `America/Bogota`; each run covers a rolling last **7 days**.
- **Prefect vocabulary (design only):** main flow `brasaland_telemetry_kpi_pipeline`; subflows `extract_telemetry_events_flow`, `transform_kpi_metrics_flow`, `load_kpi_tables_flow`; KPI transform task names aligned to Context 15 metrics.
- **Prefect Blocks (design only):** `brasaland-postgres` (from `DATABASE_URL`); `brasaland-pipeline-settings` (paths, lookback, timezone, schedule).
- **Existing report API:** `GET /telemetry/report` remains the on-request/debug path; KPI tables are the intended batch/dashboard source. Do not change the report endpoint in this phase.
- **No orchestration code** in this phase (no `pipeline.py`, no Prefect install requirement for Phase 1 completion).

---

## Scope of This Phase

1. Create `data/raw/`, `data/process/`, `data/pipelines/`, and `data/eval/`.
2. Author and commit `docs/pipelines/PIPELINE_DESIGN.md` covering current state, ETL design, resilience/idempotency, execution log, and Prefect mapping.
3. Add `data/pipelines/PIPELINE_DESIGN.md` as a short pointer to the docs canonical file (assignment path compatibility).
4. Do **not** implement flows, tasks, CLI runners, or pipeline HTTP endpoints in this phase.

---

## Required Content of `docs/pipelines/PIPELINE_DESIGN.md`

The design document must include the following sections (these map to the Phase 1 brief).

### Section A — Current state analysis

- Telemetry events already captured (inventory + backoffice), consistent with `docs/telemetry/event-schemas.json`.
- Storage: `telemetry_events` column contract and append-only semantics.
- Existing reporting: `services/api/telemetry/analysis.py` + `GET /telemetry/report` (Pandas, period filter, 60s cache).
- Limitations: no scheduled ETL; no pipeline run log; mid-failure state is unclear; re-running ad-hoc analysis is not an idempotent Load into durable KPI tables.

### Section B — Pipeline design

- **Purpose (locked sentence):**  
  Deliver daily, idempotent KPI tables from Brasaland backoffice telemetry so Operations (Felipe Guerrero) and leadership (Mariana Restrepo) can see consumption, stock-outs, and waste by location and act before the next service day.
- Extraction: source = `telemetry_events`; format = relational rows (`id`, `event_type`, `timestamp`, `service`, `level`, `value`, `tags`, `created_at`); cadence = daily with rolling 7-day window.
- Mermaid (or text) diagram with three stages — **extraction**, **transformation**, **load** — using real table names above.
- Strategy for sources that update existing facts: raw events are insert-only; KPI tables use **upsert by unique grain**.

### Section C — Resilience and idempotency

- Explicit second-run-after-load-failure behavior: re-extract/transform the same window; `INSERT … ON CONFLICT DO UPDATE` on KPI grains so rows are not duplicated.
- Execution log table `pipeline_runs` with at least: `start_time`, `end_time`, `records_processed` (defined as loaded, with separate extract/load counts), `status`, `errors`, plus `period_start`, `period_end`, `flow_name`, `records_extracted`, `records_loaded`.

### Section D — Mapping to Prefect (design only)

- Identify flows, tasks, and states (`Running`, `Completed`, `Failed`) using the locked vocabulary.
- Identify Blocks: `brasaland-postgres`, `brasaland-pipeline-settings`.

---

## Upsert Grains (must appear in the design)

| Table | Unique key | Payload fields |
| ----- | ---------- | -------------- |
| `kpi_daily_consumption` | `(date, ingredient_id, location_id)` | `quantity` |
| `kpi_stock_out_frequency` | `(date, ingredient_id, location_id)` | `stock_out_count` |
| `kpi_waste_loss_ratio` | `(date, location_id)` | `waste_quantity`, `total_quantity`, `ratio` |
| `pipeline_runs` | `id` (PK) | run metadata (insert-only per run) |

---

## Folder Semantics (for later phases; create empty now)

| Path | Role |
| ---- | ---- |
| `data/raw/` | Extracted inputs and intermediate extracts (Phase 2+) |
| `data/process/` | Reusable transformation scripts (Phase 2+) |
| `data/pipelines/` | Orchestration entrypoints (Phase 2+); pointer to design doc |
| `data/eval/` | Validation outputs (Phase 2+) |

---

## Out of Scope (This Phase)

- Installing Prefect or writing `@flow` / `@task` code
- `data/pipelines/pipeline.py` CLI
- Pipeline status/trigger HTTP endpoints
- Unit tests under `tests/pipelines/`
- Changing `GET /telemetry/report` or Milestone 5 inventory APIs
- Loading optional `auth_failure_rate_per_day` into KPI tables (optional metric remains report-only unless a later context promotes it)

---

## Verification Checklist

- [x] `data/raw/`, `data/process/`, `data/pipelines/`, `data/eval/` exist
- [x] `docs/pipelines/PIPELINE_DESIGN.md` exists and is readable Markdown
- [x] `data/pipelines/PIPELINE_DESIGN.md` pointer exists for assignment path compatibility
- [x] Purpose is one concrete business sentence (company value, not only technology)
- [x] Data-flow diagram shows extraction, transformation, and load with real Brasaland table names
- [x] Update strategy documents upsert-by-grain (not updates to `telemetry_events`)
- [x] Idempotency describes the second run after a load-phase failure concretely
- [x] Execution log specifies ≥5 fields with name, type, and audit justification
- [x] Prefect mapping identifies ≥2 flows and ≥3 tasks with locked names
- [x] Design stays consistent with Context 15 events and KPIs
- [x] No orchestration implementation committed as part of this phase’s required deliverable

---

## Evaluation Criteria

- Design document committed and readable
- Pipeline purpose sentence mentions Brasaland business outcomes
- ETL diagram uses real entity/table names
- Concrete mechanism for avoiding duplicates on re-processing (upsert by primary/unique key)
- Idempotency is explicit for a second run after load failure
- Execution log has ≥5 justified fields
- Prefect mapping has ≥2 flows and ≥3 tasks aligned to stages
- Consistency with prior telemetry KPI/event contracts

---

_Brasaland Digital — Internal document for 4Geeks Academy AI Engineering Track_
