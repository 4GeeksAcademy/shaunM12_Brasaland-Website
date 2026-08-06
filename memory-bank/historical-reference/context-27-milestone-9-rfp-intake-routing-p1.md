# Context 27 — Milestone 9 Agentic Workflow: RFP Intake & Routing (Part 1)

**Ticket:** Milestone 9 Part 1 — RFP ticket-mode intake, PDF→Markdown, classifier, orchestrator-worker-synthesizer, department routing  
**Type:** LangGraph orchestration + FastAPI `/rfp` + backoffice `/rfp` UI + Postgres + tests  
**Branch:** `milestone-9-agentic-workflow-rfp-intake-routing`  
**Status:** Spec locked — Part 1 implemented on branch `milestone-9-agentic-workflow-rfp-intake-routing`  
**Depends on:** [context-22-route-conventions.md](./context-22-route-conventions.md) (routing/proxy/casing), root [`CONTEXT.md`](../../CONTEXT.md) (company identity only)  
**Companions:** [context-27-milestone-9-rfp-response-generation-p2.md](./context-27-milestone-9-rfp-response-generation-p2.md) (generation + evaluation — **not Part 1 scope**), [context-27-milestone-9-rfp-intake-routing-p3.md](./context-27-milestone-9-rfp-intake-routing-p3.md) (HITL approval + final document — **not Part 1 scope**)  
**Stakeholders:** Camila Ospina (Marketing — process owner); Brasaland Digital backoffice users

> **Read this file before Part 1 implementation.** Parts 2 and 3 must read **§1–§9** here before their companion files.

---

## Ticket brief (Part 1)

Corporate RFPs arrive as PDFs on Camila Ospina’s desk (Marketing). Today coordination is manual (~9 business days). Part 1 delivers **ticket-mode intake**: upload PDF → convert to Markdown → classify → orchestrator → parallel department workers → synthesizer → **`intake_complete`** with per-department **`key_aspects`**.

Tech lead note:

> Keep RFP separate from the Support Agent. One ticket-scoped LangGraph, queryable trace, Postgres persistence, and thin HTTP. If I can’t see why we routed an RFP to procurement vs training, I can’t trust the workflow in production.

### Core acceptance criteria (Part 1 — non-negotiable)

1. **Ticket-mode upload** — `POST /rfp/tickets` returns immediately with `status: analyzing`; client polls until terminal P1 status.
2. **PDF → Markdown** — MarkItDown before any LLM; readability metrics stored on ticket metadata.
3. **Classifier** — Accept valid RFPs; **discard** invalid docs (seed #3) with **`discard_reason`**; no silent failure.
4. **Orchestrator-worker-synthesizer** — Separate agents; not one monolithic prompt.
5. **Department routing** — Persist **`departments_needed`** and per-dept **`key_aspects`** on **`rfp_department_sections`**.
6. **Trace** — Append-only **`trace_events`** (context-23 shape) + durable **`rfp_trace_events`** rows from P1.
7. **Thin HTTP** — Routes create/poll tickets only; business logic in graph + `data/pipelines/rfp_intake.py`.

---

## §1 Introduction

Brasaland does not have a traditional Sales department. Corporate RFPs (institutional catering, co-branding, resort concessions) land with **Camila Ospina**, **Marketing, Brand and Digital Experience**. For Milestone 9, Marketing is **Sales**: they open the ticket and wait for the agentic flow.

Today Camila forwards PDFs over WhatsApp to Felipe (Operations), Lucía (Procurement), and Jake (Training), then waits for email replies. A full proposal takes **~9 business days** on average; opportunities are sometimes lost when a department does not respond in time.

**Part 1 goal:** Replace manual triage and routing with an agentic intake pipeline that produces structured metadata, readability signals, department assignments, and **`key_aspects`** for each needed department — in under a few minutes of automated processing (human drafting/approval are Parts 2–3).

**Course wording note:** Spec text may say “Sales”; **owner = Marketing (Camila)**.

---

## §2 Departments and orchestrator selection

### 2.1 Department identifiers (English — locked)

Use **exactly** these `department_id` values in code, API, DB, and graph state:

| `department_id` | Department | Owner | Contribution |
| --------------- | ---------- | ----- | ------------ |
| `marketing` | Marketing and Digital Experience | Camila Ospina | Brand terms, exclusivity, co-branding, offer validity language. **Owns the ticket.** |
| `operations` | Restaurant Operations | Felipe Guerrero | Kitchen/staff capacity, setup times, cost per event |
| `procurement` | Procurement and Suppliers | Lucia Fernandez | Ingredient cost by volume, supplier lead times |
| `training` | Training and Quality Standards | Jake Morrison | New recipe/standard development and certification time |

> **Naming lock:** Use `operations`, not `operaciones`.

Not every RFP needs all four departments. The classifier/orchestrator selects a **subset** from document content (seed #2: no `training`).

### 2.2 Unknown departments

If the document mentions a department/topic outside the four IDs → append to ticket **`unmapped_topics[]`**. **Do not** spawn workers or create section rows for unknown IDs. Does **not** alone cause **`discarded`**.

### 2.3 Worker input (Part 1)

Each department worker receives:

- **`metadata`** — shared classifier output  
- **`department_excerpt`** — Markdown slice for that dept (orchestrator-produced)  
- **`department_id`**, **`ticket_id`**

Workers do **not** receive full **`markdown_text`** by default (stored on ticket; read from DB inside pipeline if needed).

---

## §3 RFP format

- Arrive as **PDF** (formal or informal).
- Typical fields: client name, location, service type, scope/volume, deadline, optional budget.
- Informal letters of intent are valid RFPs (seed #2).

---

## §4 Entities and status machine

### 4.1 Entities

| Entity | Part 1 fields | Later parts |
| ------ | ------------- | ----------- |
| **`rfp_tickets`** | `ticket_id`, `status`, `metadata`, `departments_needed`, `unmapped_topics`, `conflicts`, `intake_summary`, `requires_ceo_approval`, `markdown_text`, `markdown_length`, `source_pdf_path`, `source_pdf_sha256`, `discard_reason`, `error_message`, `error_code`, timestamps | P2–P3 drafting/approval/final doc |
| **`rfp_department_sections`** | `ticket_id`, `department_id`, **`key_aspects`** | `draft_content`, `evaluation_results`, `approval_status` (P2–P3) |
| **`rfp_trace_events`** | `ticket_id`, `node`, `payload` (JSONB), `created_at` | Full workflow trace |
| **`FinalDocument`** | — | P3 only |

**ID lock:** Use **`ticket_id`** (UUID string) only — **no separate `rfp_id`** for M9.

### 4.2 Metadata object (snake_case API)

| Field | Required P1 |
| ----- | ----------- |
| `client_name` | When extractable |
| `location` | When extractable |
| `service_type` | When extractable |
| `scope` | When extractable |
| `deadline` | When extractable |
| `budget_range` | Optional |
| `estimated_contract_value_usd` | Optional; used for CEO flag |
| `readability_scores` | After conversion (e.g. Flesch-Kincaid) |

### 4.3 Status machine (all parts)

```text
P1:  analyzing → intake_complete | discarded | failed
P2:  intake_complete → [Start drafting] → drafting → under_evaluation → …
P3:  … → waiting_for_approval → completed
```

| Status | Meaning | Terminal? |
| ------ | ------- | --------- |
| `analyzing` | Intake running | |
| `intake_complete` | P1 success — routing done | P1 terminal |
| `discarded` | Not a valid Brasaland RFP | P1 terminal |
| `failed` | Processing/infra error | P1 terminal |
| `drafting` | P2 generators running | |
| `under_evaluation` | P2 evaluator loop | |
| `waiting_for_approval` | P3 HITL | |
| `completed` | Final document delivered | Workflow terminal |

**Avoid `done`** — use **`intake_complete`** (P1) and **`completed`** (P3).

### 4.4 Classifier discard rule (P1)

**`discarded`** when **≥2 of 3** core fields are missing or unusable:

1. Client / organization  
2. Service / scope  
3. Deadline  

Set **`discard_reason`** (human-readable; optional `discard_rule_id: missing_core_fields`). Seed #3 (franchise inquiry) must **`discarded`**.

**No auto-retry** on misclassification in P1. **`reopen`** / re-analyze = **stretch only**.

### 4.5 Synthesizer conflicts (P1)

If workers contradict (e.g. deadline), synthesizer sets **`conflicts[]`**:

```json
{
  "field": "deadline",
  "claims": [
    { "department_id": "marketing", "value": "2026-09-01" },
    { "department_id": "operations", "value": "2026-09-15" }
  ]
}
```

Ticket may still reach **`intake_complete`**.

---

## §5 Business constraints (compliance — SSoT for P2 evaluators)

**Authority:** This section — **not** root `CONTEXT.md` (pillars only there). P2 “compliance with company guidelines” means these **rule IDs**.

| Rule ID | Requirement |
| ------- | ----------- |
| **`COMPLIANCE_DUAL_CURRENCY`** | Every price in **both COP and USD** |
| **`COMPLIANCE_BRAND_PILLARS`** | Mention all three pillars: consistent quality, warm experience, speed of service (align with root `CONTEXT.md`) |
| **`COMPLIANCE_MIN_LEAD_TIME_10_BD`** | No setup/delivery promises **< 10 business days** |
| **`COMPLIANCE_NO_COMPETITORS`** | No competitor names |
| **`COMPLIANCE_VALIDITY_30_DAYS`** | Offer validity **30 days** from issuance |
| **`COMPLIANCE_CEO_THRESHOLD_50K`** | Contracts **> $50,000 USD/year** → CEO approval before final document (P3) |

### FX constant (locked)

| Constant | Value |
| -------- | ----- |
| **`USD_COP_RATE`** | **4000** (1 USD = 4000 COP) — fictional Brasaland finance rate for tests/eval; **not** live FX |

- Classifier normalizes annual value → **`estimated_contract_value_usd`**.  
- **`requires_ceo_approval = true`** when **`estimated_contract_value_usd > 50000`**.  
- Ranges (seed #1: $60–75k/year): use **upper bound** for CEO flag.  
- Ambiguous/missing value → **`requires_ceo_approval: false`** + optional metadata warning.  
- P2 dual-currency checks use same rate (±1% tolerance OK).

---

## §6 KPIs (Milestone 9)

| KPI | Today | Target |
| --- | ----- | ------ |
| Proposal cycle time | ~9 business days | **< 2 business days** (upload → final doc; Parts 1–3) |
| Correct classification rate | — | % valid RFPs vs **`discarded`** |
| Avg iterations per section | — | **< 2** (P2; target) |
| Approval time per department | — | Time from ready → approved/rejected (P3) |

Part 1 contributes: classification accuracy, intake latency, trace completeness.

---

## §7 Seed data

### 7.1 Canonical assets (committed)

Path: **`memory-bank/historical-reference/assets/milestone-9/`**

| File | Expected P1 outcome |
| ---- | ------------------- |
| `CONTEXT-brasaland-request-1.pdf` | **`intake_complete`** — Sunset Bay Resorts; ~$60–75k USD/year; all 4 depts; **`requires_ceo_approval: true`** |
| `CONTEXT-brasaland-request-2.pdf` | **`intake_complete`** — Andes Tech; 220 employees Medellín; **`marketing`, `operations`, `procurement`** (no `training`) |
| `CONTEXT-brasaland-request-3.pdf` | **`discarded`** — franchise inquiry; missing scope/budget/deadline |

> **Seed PDFs** are committed under this directory. Tests resolve path via constant **`RFP_SEED_ASSETS_DIR`**; **no** copy under `data/raw/intakes/` (runtime uploads only).

### 7.2 Runtime uploads

- Original PDF (UI upload): **`data/raw/intakes/{ticket_id}/source.pdf`** (gitignored)  
- LangGraph checkpoints: **`data/rfp/checkpoints.db`** (gitignored)

---

## §8 Cross-part locks (defined here; implemented in P2/P3)

| Topic | Lock |
| ----- | ---- |
| P2 entry | Manual **“Start drafting”** when **`intake_complete`** |
| P2 auto-loop | **`MAX_GENERATOR_EVALUATOR_ITERATIONS = 3`** per department |
| P3 arbitration | **`MAX_ARBITRATION_ITERATIONS = 2`**; arbitrator **Camila (marketing)** |
| P3 terminal | **`completed`** |
| CEO | **Mariana Restrepo** when **`requires_ceo_approval`** |
| Auth (M9) | Any **authenticated** backoffice user; UI shows narrative dept owners |
| Approval UI | **`/rfp/[id]`** only — **not** Support chat |
| Graph | **One RFP LangGraph**; **`thread_id = rfp:{ticket_id}`**; grows in P2/P3 |

---

## §9 Out of scope vs Support Agent (context-23–26)

| Topic | M9 RFP | Support Agent |
| ----- | ------ | ------------- |
| UI | `/rfp` | `/support` |
| API | `/rfp/*` | `/agent/*` |
| Graph | `services/api/rfp/graph.py` | `services/api/agent/graph.py` |
| Checkpoints | `RFP_CHECKPOINT_DB_PATH` | `AGENT_CHECKPOINT_DB_PATH` |
| RFP tools in chat | **No** | N/A |
| RAG / KB for intake PDFs | **No** (optional P2 generator retrieve only) |
| context-25 guardrails | **No** — use §5 rule IDs | Support-only |

**Do not** merge RFP into Support graph or extend context-23–26 for Milestone 9.

### Stretch (not M9-required)

- `POST /rfp/tickets/{id}/reopen`  
- `GET /rfp/tickets/{id}/markdown`  
- `GET /rfp/tickets/{id}/source` (PDF stream)  
- Fine-grained dept RBAC  
- Celery (context-18)  
- Postgres LangGraph checkpointer (SQLite locked for P1–P3 start)  
- Optional P2 RAG retrieve for generators  

---

## Authority / supersession

| Source | Rule |
| ------ | ---- |
| context-21 **S1** | LangGraph allowed for **RFP orchestration**; no LangChain chains/agents for RFP |
| context-22 | Bare FastAPI mounts + `/api/<domain>` proxy + camelCase/snake_case |
| context-13 “ticket” | Use **`RfpTicket`** / **`/rfp`** — not incident tickets |
| Root `CONTEXT.md` | Company identity, CEO name, brand pillars — **not** compliance checklist |

---

## Locked decisions — master register

### Monorepo layout (M1–M4)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M9-M1** | API surface | **Single** FastAPI app in `services/api/` — **no** second HTTP service |
| **M9-M2** | Pipeline / graph | **`data/pipelines/rfp_intake.py`** + **`data/pipelines/rfp_intake_graph.py`**; **not** Support agent graph |
| **M9-M3** | CLI smoke | **`scripts/rfp_intake_smoke.py`** — not a second HTTP API |
| **M9-M4** | RFP persistence | **SQLModel + Postgres** (`DATABASE_URL`); **no TinyDB** for ticket data |

### Workflow & domain (decisions 1–7)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M9-1** | P1 terminal success | **`intake_complete`** |
| **M9-2** | P2 trigger | Manual **“Start drafting”** at **`intake_complete`** |
| **M9-3** | Department IDs | `marketing`, **`operations`**, `procurement`, `training` |
| **M9-4** | Seed PDFs | **`assets/milestone-9/`** only |
| **M9-5** | Upload pattern | Async + poll **`GET /rfp/tickets/{ticket_id}`** |
| **M9-6** | Product boundary | RFP-only; **no Support Agent integration** |
| **M9-7** | Discard rule | ≥2 of 3 missing (client/org, service/scope, deadline) → **`discarded`** + **`discard_reason`** |

### Routing (A1–A4)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M9-A1** | FastAPI mount | **`/rfp`** with `_protected` |
| **M9-A2** | Backoffice proxy | **`/api/rfp/:path*` → `/rfp/:path*`** |
| **M9-A3** | Backoffice pages | **`/rfp`**, **`/rfp/[id]`**; tab **“RFP”** (after Knowledge, before Support) |
| **M9-A4** | Casing | context-22 R6: API snake_case; UI camelCase in clients |

### Persistence (B1–B4, H1–H2)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M9-B1** | Markdown storage | Postgres **`rfp_tickets.markdown_text`** |
| **M9-B2** | PDF storage | **`data/raw/intakes/{ticket_id}/source.pdf`** + path + SHA-256 |
| **M9-B3** | Seeds | **`assets/milestone-9/`**; seeds are not copied into `data/raw/intakes/` |
| **M9-B4** | Database | **`DATABASE_URL` required**; no TinyDB |
| **M9-H1** | Field names | **`departments_needed`**, **`key_aspects`**, **`intake_summary`**; no **`rfp_id`** |
| **M9-H2** | Section rows | Create **`rfp_department_sections`** in P1 with **`key_aspects`** |

### Graph behavior (C1–C5)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M9-C1** | Unknown topics | **`unmapped_topics[]`**; no worker |
| **M9-C2** | Worker input | **`metadata` + `department_excerpt`** |
| **M9-C3** | Conflicts | **`conflicts[]`**; still **`intake_complete`** |
| **M9-C4** | Classifier retry | **None** in P1 |
| **M9-C5** | Graph model | One graph in **`services/api/rfp/`**; **`thread_id = rfp:{ticket_id}`** |

### Dependencies (D1–D3)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M9-D1** | Required packages | **`markitdown`**, **`py-readability-metrics`** |
| **M9-D2** | LLM env | **`GENERATION_BASE_URL`**, **`GENERATION_API_KEY`**, **`GENERATION_MODEL_ID`** |
| **M9-D3** | Orchestration | **LangGraph**; **no LangChain** for RFP |

### Auth & trace (E1–E2, F1–F2)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M9-E1** | Upload auth | Any authenticated backoffice user |
| **M9-E2** | P3 approval auth | Narrative owners on UI; any authenticated user for M9 |
| **M9-F1** | Trace shape | **`trace_events`**: `[{"node": "...", ...}]` (context-23) |
| **M9-F2** | Trace DB | **`rfp_trace_events`** from P1; dual-write with graph state |

### Cross-part & API (G1–G5, H3–H8)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M9-G1** | Workflow terminal | **`completed`** |
| **M9-G2** | P2 iter cap | **3** per department |
| **M9-G3** | P3 arbitration cap | **2** |
| **M9-G4** | CEO flag | **`requires_ceo_approval`** if **> $50k USD/year** |
| **M9-G5** | Compliance SSoT | **§5** + **`COMPLIANCE_*`** IDs |
| **M9-H3** | P1 API | **POST/GET `/rfp/tickets`**, **GET `/rfp/tickets/{ticket_id}`** |
| **M9-H4** | Markdown in GET | **`markdown_length`**, **`has_markdown`** only |
| **M9-H5** | Processing errors | **`failed`** + **`error_message`** / **`error_code`** |
| **M9-H6** | Checkpointer | **`RFP_CHECKPOINT_DB_PATH`** default **`data/rfp/checkpoints.db`** |
| **M9-H7** | Async | **FastAPI `BackgroundTasks`**; **no Celery**; PDF max **10 MB** |
| **M9-H8** | FX | **`USD_COP_RATE = 4000`** |

---

## Goal (Part 1 implementation)

1. **LangGraph** intake: convert → readability → classify → orchestrate → workers → synthesize.  
2. **Three API endpoints** under **`/rfp/tickets`**.  
3. **Backoffice `/rfp`** — upload, list, detail with poll.  
4. **Postgres** tables + **SQLite** RFP checkpoints.  
5. **Pipeline tests** with seed PDFs #1–#3 expectations.  

**Golden rules**

- Thin HTTP routes; **pipeline + LangGraph** under **`data/pipelines/`** (`rfp_intake.py`, `rfp_intake_graph.py`); ORM/repository in `services/api/rfp/`.  
- Package installs: **`cd services/api && uv add …`**.  
- Do **not** touch Support Agent graph (context-23–26).  
- RFP PDFs are **not** indexed into Knowledge base.

---

## Monorepo layout (non-negotiable)

| ID | Rule | Implementation |
| -- | ---- | -------------- |
| **M9-M1** | **Single API** | Extend existing FastAPI in `services/api/` only. Mount `/rfp` on `main.py`. **No** second HTTP service or microservice. |
| **M9-M2** | **Pipeline ownership** | RFP intake graph + helpers under **`data/pipelines/`** (`rfp_intake.py`, `rfp_intake_graph.py`). Dedicated to RFP — **not** mixed into Support/CX agent graph (`services/api/agent/graph.py`). Routers call `intake_service`, which invokes the pipeline entrypoint. |
| **M9-M3** | **CLI / smoke scripts** | Manual reprocess and smoke runs live in **`scripts/rfp_intake_smoke.py`**. **Not** exposed as a second HTTP API. |
| **M9-M4** | **Postgres persistence** | `rfp_tickets`, `rfp_department_sections` (incl. `key_aspects`), `rfp_trace_events` via **SQLModel** + `DATABASE_URL` (Supabase Postgres). **TinyDB is not acceptable** for RFP ticket data. |

### Call chain (Part 1)

```text
POST /rfp/tickets  →  services/api/rfp/routes.py
                    →  services/api/rfp/intake_service.py
                    →  data/pipelines/rfp_intake_graph.py  (invoke_rfp_intake)
                    →  data/pipelines/rfp_intake.py       (MarkItDown, classify, workers, …)
                    →  Postgres (SQLModel) + data/raw/intakes/{ticket_id}/source.pdf
```

CLI smoke (no HTTP):

```text
scripts/rfp_intake_smoke.py  →  intake_service  →  data/pipelines/rfp_intake_graph.py
```

---

## Graph state schema (Part 1 — minimal)

```python
ticket_id: str
markdown_text: str | None
metadata: dict[str, Any]
departments_needed: list[str]
unmapped_topics: list[str]
department_excerpts: dict[str, str]      # department_id → excerpt
department_key_aspects: dict[str, list[str]]
conflicts: list[dict]
intake_summary: str | None
requires_ceo_approval: bool
status: str                              # terminal P1 value written to DB
discard_reason: str | None
error_message: str | None
trace_events: list[dict]                 # Annotated append (context-23)
```

P2/P3 fields are added in companion docs on the **same graph** and **`thread_id`**.

---

## Graph nodes and edges (Part 1)

### Nodes

| Node | Responsibility |
| ---- | -------------- |
| `convert_pdf` | MarkItDown: PDF → `markdown_text`; persist B1/B2 |
| `readability` | `py-readability-metrics` → `metadata.readability_scores` |
| `classify` | Valid RFP vs **`discarded`** (M9-7); metadata; `departments_needed`; `requires_ceo_approval`; `unmapped_topics` |
| `orchestrate` | Build `department_excerpts` per selected dept |
| `worker` | Per dept (parallel): `key_aspects` from metadata + excerpt |
| `synthesize` | `intake_summary`, `conflicts[]`; persist sections |

On **`discarded`**: skip workers/sections (or do not create sections).  
On pipeline exception: **`failed`** + **`error_code`** (`pdf_conversion_failed`, `llm_unavailable`, `pipeline_error`, `storage_error`).

### Flow

```text
START → convert_pdf → readability → classify
classify → END (discarded)
classify → orchestrate → worker (parallel per dept) → synthesize → END (intake_complete)
any node fatal error → END (failed)
```

### Trace examples

```json
{"node": "convert_pdf", "markdown_length": 4200}
{"node": "classify", "departments_needed": ["marketing", "operations"], "requires_ceo_approval": true}
{"node": "worker", "department_id": "marketing", "key_aspect_count": 3}
{"node": "synthesize", "conflict_count": 0}
```

---

## Suggested file layout

| Responsibility | Location |
| -------------- | -------- |
| Graph state | `services/api/rfp/state.py` |
| **Graph + nodes** | **`data/pipelines/rfp_intake_graph.py`** |
| HTTP routes | `services/api/rfp/routes.py` |
| Intake orchestration + persistence | `services/api/rfp/intake_service.py` |
| Graph re-export (compat) | `services/api/rfp/graph.py` → `data/pipelines/rfp_intake_graph.py` |
| SQLModel tables | `services/api/rfp/models.py` |
| Repository | `services/api/rfp/repository.py` |
| Constants | `services/api/rfp/constants.py` |
| Intake pipeline helpers | `data/pipelines/rfp_intake.py` |
| **CLI smoke / reprocess** | **`scripts/rfp_intake_smoke.py`** |
| P1 tests | `services/api/tests/pipelines/test_rfp_intake.py` |
| Backoffice client | `uis/backoffice/lib/rfp.ts` |
| List/upload UI | `uis/backoffice/app/rfp/page.tsx` |
| Detail/poll UI | `uis/backoffice/app/rfp/[id]/page.tsx` |
| Nav tab | `uis/backoffice/components/backoffice-tabs.tsx` |

Register in `main.py`:

```python
app.include_router(rfp_router, prefix="/rfp", dependencies=_protected)
```

Add `"rfp"` to `[tool.hatch.build.targets.wheel] packages` in `services/api/pyproject.toml`.

Update **context-22** when `/rfp` proxy is added.

---

## Database schema (Part 1)

### `rfp_tickets`

Core columns: `ticket_id` (PK, UUID), `status`, `metadata` (JSON), `departments_needed` (JSON array), `unmapped_topics`, `conflicts`, `intake_summary`, `requires_ceo_approval`, `markdown_text`, `source_pdf_path`, `source_pdf_sha256`, `discard_reason`, `error_message`, `error_code`, `created_at`, `updated_at`.

### `rfp_department_sections`

`id`, `ticket_id` (FK), `department_id`, `key_aspects` (JSON array), nullable P2/P3 columns, **`UNIQUE(ticket_id, department_id)`**.

### `rfp_trace_events`

`id`, `ticket_id` (FK), `node`, `payload` (JSONB), `created_at`.

Create tables via SQLModel migrations or existing project pattern when `DATABASE_URL` is set.

---

## HTTP surface (Part 1 — locked)

| Method / path | Auth | Behavior |
| ------------- | ---- | -------- |
| `POST /rfp/tickets` | Authenticated | Multipart **`file`** (PDF, ≤10 MB) → 201 `{ ticket_id, status: "analyzing" }`; schedule background intake |
| `GET /rfp/tickets` | Authenticated | List summaries; query: `status`, `limit` (default 50), `offset` |
| `GET /rfp/tickets/{ticket_id}` | Authenticated | Full detail + **`sections`** with **`key_aspects`** when complete |

### `POST /rfp/tickets` errors

| Code | When |
| ---- | ---- |
| **400** | Missing file, not PDF, >10 MB |
| **503** | Missing **`DATABASE_URL`** or **`GENERATION_*`** |

Never return raw stack traces (context-23 P1-L7 spirit).

### Detail response (P1 terminal — success)

Include: `ticket_id`, `status`, `metadata`, `departments_needed`, `unmapped_topics`, `conflicts`, `requires_ceo_approval`, `intake_summary`, `markdown_length`, `has_markdown`, `sections[]`, timestamps.

Omit **`markdown_text`** from default GET (M9-H4).

### Background job

```python
background_tasks.add_task(run_intake_graph, ticket_id)
```

Guard against duplicate concurrent runs for the same **`ticket_id`**.

---

## Backoffice (Part 1)

### Proxy (`uis/backoffice/next.config.mjs`)

```javascript
{
  source: "/api/rfp/:path*",
  destination: `${apiOrigin}/rfp/:path*`,
}
```

### Client (`uis/backoffice/lib/rfp.ts`)

- Same-origin: `/api/rfp/tickets`  
- Optional: `NEXT_PUBLIC_RFP_API_BASE_URL`  
- Map camelCase ↔ snake_case per context-22  

### UI

| Page | Behavior |
| ---- | -------- |
| `/rfp` | Upload PDF; list tickets; link to detail |
| `/rfp/[id]` | Poll until `intake_complete` \| `discarded` \| `failed`; show metadata, sections, conflicts, CEO flag |

### Tab

```typescript
{ href: "/rfp", label: "RFP" }
```

Place after Knowledge, before Support Agent.

**Part 1 UI does not include** “Start drafting” (P2) or approval actions (P3).

---

## Env vars (add to `.env.example`)

```bash
# --- RFP agentic workflow (context-27 Part 1) ---
RFP_CHECKPOINT_DB_PATH=data/rfp/checkpoints.db
# Reuse generation LLM (context-21): GENERATION_BASE_URL, GENERATION_API_KEY, GENERATION_MODEL_ID
# Postgres required: DATABASE_URL
NEXT_PUBLIC_RFP_API_BASE_URL=
```

Add to `.gitignore`:

```gitignore
data/raw/intakes/*
!data/raw/intakes/.gitkeep
data/rfp/*
!data/rfp/.gitkeep
```

---

## Prerequisites

| Requirement | Part 1 |
| ----------- | ------ |
| **`DATABASE_URL`** | **Yes** |
| **`GENERATION_*`** | **Yes** (classifier/workers) |
| FastAPI + backoffice login | Yes |
| Seed PDFs in `assets/milestone-9/` | For full E2E (may pending) |
| Qdrant / RAG | **No** |

---

## Phase plan (implement in order)

### Phase 0 — Dependencies

1. `cd services/api && uv add markitdown py-readability-metrics` (if not present).  
2. Ensure `langgraph`, `langgraph-checkpoint-sqlite` available.  
3. **Gate:** imports succeed.

### Phase 1 — Data layer

1. `services/api/rfp/models.py` — tickets, sections, trace events.  
2. Repository + migrations.  
3. **Gate:** create ticket row in test DB.

### Phase 2 — Pipeline + graph

1. `data/pipelines/rfp_intake.py` — MarkItDown, readability, LLM helpers.  
2. `state.py`, `graph.py` — nodes, edges, checkpointer, trace dual-write.  
3. **Gate:** invoke graph with seed #1 fixture → `intake_complete`.

### Phase 3 — API

1. `routes.py` — POST/GET trio + BackgroundTasks.  
2. Register `/rfp` in `main.py`.  
3. **Gate:** curl upload + poll.

### Phase 4 — Backoffice

1. Proxy, `lib/rfp.ts`, `/rfp` pages, tab.  
2. **Gate:** upload seed PDF in UI; see routing on detail page.

### Phase 5 — Tests

1. `tests/pipelines/test_rfp_intake.py`:

| # | Input | Assert |
| - | ----- | ------ |
| 1 | Seed #1 PDF | `intake_complete`, 4 sections, `requires_ceo_approval: true` |
| 2 | Seed #2 PDF | `intake_complete`, 3 sections, no `training` |
| 3 | Seed #3 PDF | `discarded` + `discard_reason` |
| 4 | Mock corrupt PDF | `failed` + `error_code` |

2. Extend backoffice route tests for `/api/rfp/*`.  
3. **Gate:** `pytest tests/pipelines/test_rfp_intake.py -q`.

---

## Evaluation checklist (Part 1 acceptance)

Official rubric — verify before Part 2:

- [ ] **Monorepo layout (M9-M1–M9-M4)** — Single API; graph/pipeline under `data/pipelines/`; smoke/reprocess in `scripts/rfp_intake_smoke.py`; Postgres SQLModel (no TinyDB)
- [ ] **Single API + pipeline layout** — Same FastAPI backend only; pipeline code under `data/pipelines/`; no second HTTP service
- [ ] **Postgres persistence** — Ticket, RFP metadata, and per-department `key_aspects` in Supabase/PostgreSQL (`DATABASE_URL`)
- [ ] **PDF storage** — UI-driven uploads land under **`data/raw/intakes/{ticket_id}/source.pdf`** (gitignored)
- [ ] **P1 status machine** — `analyzing` → `intake_complete` **or** `discarded` (also `failed` for processing errors); **not** `waiting_for_approval` in Part 1
- [ ] **Async intake** — `POST /rfp/tickets` returns quickly; background pipeline; pollable ticket status
- [ ] **Classifier isolation** — Non-RFP documents **`discarded`** with reason; other tickets continue processing
- [ ] **Metadata + readability** — Stored per processed document (`metadata` + `readability_scores`)
- [ ] **Orchestrator-worker-synthesizer** — Separate graph nodes/agents on the `rfp_intake` LangGraph (not one monolithic prompt)
- [ ] **Routing output** — Per-department **`key_aspects`** + **contact** (`department_owner` from [`CONTEXT.md`](../../CONTEXT.md) §Operating context); verifiable on sample PDFs #1–#3
- [ ] **Unit tests** — Classifier agent + at least one worker agent (`tests/pipelines/test_rfp_classifier_worker.py`)
- [ ] **Domain alignment** — Departments (`marketing`, `operations`, `procurement`, `training`) and RFP format per context-27 §2–§4 and company leads in **`CONTEXT.md`**

Supporting gates (also required):

- [ ] `/rfp` UI + `/api/rfp` proxy; Support Agent unchanged
- [ ] Auth on all `/rfp/*` routes
- [ ] Seed PDFs in `assets/milestone-9/`; pipeline tests seeds #1–#3 (+ corrupt PDF → `failed`)
- [ ] Separate RFP checkpointer from Support Agent (`data/rfp/checkpoints.db`)
- [ ] Trace: `rfp_trace_events` from P1 graph nodes

---

## Explicit non-goals (Part 1)

- Part 2: generators, evaluators, **`POST .../draft`**
- Part 3: interrupt/resume, approval, final document, **`completed`**
- Support Agent integration (context-23–26)
- Indexing RFP PDFs into Knowledge base
- Celery / Redis queues
- LangChain orchestration for RFP
- Department RBAC
- Returning full `markdown_text` in default list/detail GET

---

## Part 2 pointer

Read **§1–§9** above, then **[context-27-milestone-9-rfp-response-generation-p2.md](./context-27-milestone-9-rfp-response-generation-p2.md)**.

**Gate:** Part 1 acceptance complete before P2 implementation.

---

## Verification commands

```bash
# RFP intake tests
cd services/api && uv run python -m pytest tests/pipelines/test_rfp_intake.py -q

# CLI smoke (no HTTP) — seed #1 Sunset Bay
cd services/api && uv run python ../../scripts/rfp_intake_smoke.py --seed 1

# Reprocess an existing ticket
cd services/api && uv run python ../../scripts/rfp_intake_smoke.py --reprocess TICKET_UUID

# API health
curl -s http://127.0.0.1:8000/api/health

# Upload (replace TOKEN and path)
curl -X POST http://127.0.0.1:8000/rfp/tickets \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@memory-bank/historical-reference/assets/milestone-9/CONTEXT-brasaland-request-1.pdf"
```

---

_Internal document — Brasaland · Context 27 Part 1 · Milestone 9 RFP intake & routing_
