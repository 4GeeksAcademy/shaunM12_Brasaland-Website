# Context 27 — Milestone 9 Agentic Workflow: Response Generation (Part 2)

**Ticket:** Milestone 9 Part 2 — per-department draft generation, parallel evaluation, generator–evaluator loop  
**Type:** LangGraph extension + FastAPI `/rfp` draft trigger + backoffice UI + Postgres + tests  
**Branch:** `milestone-9-agentic-workflow-rfp-generation` (suggested)  
**Status:** Implemented — **all 27 decisions confirmed (Option A)** — P2 acceptance verified 2026-08-06  
**Depends on:** [context-27-milestone-9-rfp-intake-routing-p1.md](./context-27-milestone-9-rfp-intake-routing-p1.md) (**§1–§9 + P1 merged**), [context-22-route-conventions.md](./context-22-route-conventions.md), root [`CONTEXT.md`](../../CONTEXT.md) (brand pillars only)  
**Companion:** [context-27-milestone-9-rfp-approval-document-p3.md](./context-27-milestone-9-rfp-approval-document-p3.md) (HITL approval + final document — **not Part 2 scope**)  
**Stakeholders:** Camila Ospina (Marketing — process owner); Brasaland Digital backoffice users

> **Read p1 §1–§9 before this file.** Compliance rule IDs, department IDs, status names, monorepo layout (M9-M1–M9-M4), and cross-part locks are inherited from p1.

---

## Ticket brief (Part 2)

Part 1 produces routing: metadata, `key_aspects`, and `departments_needed`. Part 2 generates a **first draft per department** and **self-evaluates** each section (readability, relevance, compliance) before human approval (Part 3).

Tech lead intent:

> Part 1 tells us what to answer; Part 2 drafts and quality-checks each department’s section. Generators and evaluators must be separate agents — not one monolithic prompt. If evaluation fails, loop back with concrete feedback, bounded by an iteration cap. The ticket must show real progress; never discard the whole RFP because one section failed QA.

### What to build

- A **generator agent per department** that receives metadata and summary from Part 1 and drafts that department’s pricing-proposal section.
- **Evaluator agents in parallel** per section: readability (`py-readability-metrics`), relevance (addresses RFP / `key_aspects`), compliance (p1 §5 rule IDs).
- **Generator–evaluator loop** with concrete failure feedback and **`MAX_GENERATOR_EVALUATOR_ITERATIONS = 3`** (p1 M9-G2).
- **`needs_human_review`** when iteration limit is exhausted without pass.
- Persist **`draft_content`** and **`evaluation_results`** in Postgres; ticket status **`drafting`** / **`under_evaluation`** during P2.
- **Extend existing backend** — `POST /rfp/tickets/{ticket_id}/draft`; pipeline under **`data/pipelines/`**; no second HTTP service.

### Acceptance criteria (handoff to Part 3)

For **every active department**, Part 2 must persist both **`draft_content`** and structured **`evaluation_results`** (pass or `needs_human_review`).

### Out of scope (reference only — do not put in implementation)

- Long essays on “guideline compliance” rationale; use p1 §5 rule IDs.
- Visual workflow diagrams (optional assets only).
- Human approval, interrupts, final document (Part 3).
- Mandatory Knowledge-base retrieve (optional stretch only).

---

## Prerequisite gate (Part 1)

Do **not** start Part 2 until Part 1 acceptance is complete:

- [ ] `POST/GET /rfp/tickets` async intake; terminal P1 statuses
- [ ] Seed PDFs #1–#3 behave per p1 §7
- [ ] `rfp_department_sections.key_aspects` populated on `intake_complete`
- [ ] P1 pytest suite green
- [ ] Monorepo layout M9-M1–M9-M4 satisfied

---

## Design questions — locked answers

| Question | Lock |
| -------- | ---- |
| **What does each evaluator receive?** | **Only that department’s `draft_content`**, plus fixed context: ticket `metadata`, dept **`key_aspects`**, dept excerpt, p1 **§5 `COMPLIANCE_*` rules**. **Not** the full multi-dept document. |
| **How do parallel evaluators avoid write conflicts?** | Evaluators are **read-only** on draft. Each writes a **distinct key** (`readability`, `relevance`, `compliance`) under that dept’s evaluation result; **join node** aggregates before loop decision. |
| **Max iterations without pass — what does Camila see?** | Section: **`needs_human_review: true`**, **`draft_status: needs_human_review`**. Ticket: still → **`waiting_for_approval`** when all depts done — **not** discarded/failed. |
| **Is retry feedback specific?** | **Yes** — generator retry receives only **`failures[]` / `missing_topics[]`** from failed dimensions, not generic “try again.” |

---

## Status machine (Part 2 segment)

Inherited from p1 §4.3:

```text
intake_complete → [Start drafting] → drafting → under_evaluation → (loop) → waiting_for_approval
```

| Status | When (P2) | Notes |
| ------ | ---------- | ----- |
| `drafting` | Any section generator running | Ticket-level |
| `under_evaluation` | Any section in eval or retry loop | Ticket-level |
| `waiting_for_approval` | **P2 terminal** — all active depts have final draft + eval | **P3 entry gate** (P3 starts HITL here) |

**Trigger (p1 M9-2):** Manual **“Start drafting”** when ticket is **`intake_complete`**.

**Poll:** `GET /rfp/tickets/{ticket_id}` (same as P1).

### Per-section `draft_status` (persisted column)

`pending` → `drafting` → `evaluating` → `passed` | `needs_human_review`

| Ticket status | When |
| ------------- | ---- |
| `drafting` | Any section `drafting` |
| `under_evaluation` | Any section `evaluating` or in retry |
| `waiting_for_approval` | All sections terminal (`passed` or `needs_human_review`) |

---

## Compliance & guidelines authority

| Source | Use in P2 |
| ------ | --------- |
| **p1 §5** (`COMPLIANCE_*` rule IDs) | **Compliance evaluator** — deterministic checks |
| **Root [`CONTEXT.md`](../../CONTEXT.md)** | Brand pillars for `COMPLIANCE_BRAND_PILLARS` |
| Course “context.md” wording | Maps to **p1 §5 + `CONTEXT.md`** — not `CONTEXT-company.md` |

### Compliance rule IDs (evaluator checks)

`COMPLIANCE_DUAL_CURRENCY`, `COMPLIANCE_BRAND_PILLARS`, `COMPLIANCE_MIN_LEAD_TIME_10_BD`, `COMPLIANCE_NO_COMPETITORS`, `COMPLIANCE_VALIDITY_30_DAYS`, `COMPLIANCE_CEO_THRESHOLD_50K` (flag only; CEO gate is P3).

**FX:** `USD_COP_RATE = 4000` (±1% tolerance on dual-currency checks).

---

## `EvaluationResult` shape (locked)

Stored in **`rfp_department_sections.evaluation_results`** (JSONB):

```json
{
  "latest": {
    "iteration": 1,
    "department_id": "operations",
    "readability": {
      "passed": true,
      "flesch_kincaid_grade": 9.2,
      "threshold_max_grade": 12.0
    },
    "relevance": {
      "passed": false,
      "addresses_key_aspects": false,
      "missing_topics": ["peak season staffing"]
    },
    "compliance": {
      "passed": false,
      "failures": [
        {
          "rule_id": "COMPLIANCE_DUAL_CURRENCY",
          "message": "Section quotes USD only.",
          "suggested_fix": "Add COP equivalent using USD_COP_RATE 4000."
        }
      ]
    },
    "overall_passed": false,
    "needs_human_review": false
  },
  "history": []
}
```

### Pass / loop rules

| Rule | Value |
| ---- | ----- |
| **`overall_passed`** | `readability.passed AND relevance.passed AND compliance.passed` |
| **First iteration** | **`iteration: 1`** (1-based) |
| **Relevance pass** | **`missing_topics` is empty** (all dept `key_aspects` covered) |
| **Readability pass** | Flesch-Kincaid grade **≤ 12.0** on draft text |
| **Max iter exhausted** | Set **`needs_human_review: true`** on `latest`; sync **`draft_status: needs_human_review`** |
| **History** | Append each iteration to **`history`**; API exposes **`latest`** by default |

**Forbidden:** Unstructured free-text as the only evaluation output.

---

## Graph architecture (Part 2)

**One compiled RFP LangGraph** (p1 Decision 1 + M9-C5 superseded for location): intake nodes in **`data/pipelines/rfp_intake_graph.py`**; generation/evaluation nodes in **`data/pipelines/rfp_generation_graph.py`**; merged at compile. Same **`thread_id = rfp:{ticket_id}`**.

### P2 invoke (locked)

- **`POST .../draft`** hydrates ticket + sections from **Postgres** into graph state.
- Run **P2 nodes only** — do **not** re-run P1 convert/classify/workers on normal draft start.
- **Postgres is the poll source of truth** for API/UI; checkpoint is for graph resume/debug.

### Per-department flow

```text
generate (dept) → parallel_eval (readability | relevance | compliance)
                      ↓ join
               overall_passed? → persist section → done
               iter < 3?       → generate with failures[] / missing_topics[] feedback
               iter >= 3?      → needs_human_review → persist → continue other depts
```

### Parallelism (locked)

| Scope | Parallel? |
| ----- | --------- |
| **Across departments** | **Yes** — fan-out per `departments_needed` (LangGraph `Send` or equivalent) |
| **Within department evaluators** | **Yes** — readability, relevance, compliance, then join |
| **Across tickets** | **Yes** — separate `thread_id` / ticket rows |

### Generators (locked)

**One generator entrypoint / prompt template per `department_id`**. Shared LLM client/helpers OK; **not** one monolithic “generate all sections” agent.

---

## API (extend `/rfp`)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `POST` | `/rfp/tickets/{ticket_id}/draft` | Start P2 from **`intake_complete`**; async |
| `GET` | `/rfp/tickets/{ticket_id}` | Poll; includes `draft_content`, `evaluation_results`, `draft_status` per section |

### `POST .../draft` contract (locked)

- **201** immediately: `{ ticket_id, status: "drafting", status_label }`
- **BackgroundTasks** runs generation graph
- **409** if status ≠ `intake_complete` (idempotent — one P2 start per ticket from intake)
- **503** if `DATABASE_URL` or `GENERATION_*` missing (same as P1)
- Client polls **GET** until **`waiting_for_approval`** or **`failed`**

Auth: any authenticated backoffice user (p1 M9-E1).

---

## Monorepo layout (inherited M9-M1–M9-M4)

| Layer | Path |
| ----- | ---- |
| HTTP (thin) | `services/api/rfp/routes.py`, `draft_service.py` |
| ORM / repository | `services/api/rfp/models.py`, `repository.py` |
| **Intake graph** | `data/pipelines/rfp_intake_graph.py` |
| **Generation graph** | `data/pipelines/rfp_generation_graph.py` |
| **Pipeline helpers** | `data/pipelines/rfp_generation.py`, `data/pipelines/rfp_intake.py` (shared) |
| Graph re-export | `services/api/rfp/graph.py` → `data/pipelines/*` |
| Tests | `services/api/tests/pipelines/test_rfp_generation.py`, `test_rfp_evaluator.py` |
| Optional CLI | `scripts/rfp_draft_smoke.py` (stretch; mirror `scripts/rfp_intake_smoke.py`) |

Call chain:

```text
POST /rfp/tickets/{id}/draft → routes → draft_service
  → data/pipelines/rfp_generation_graph.py
  → data/pipelines/rfp_generation.py
  → Postgres (draft_content, evaluation_results, draft_status)
```

---

## Generator & evaluator inputs (locked)

### Generator receives

- Ticket **`metadata`**, **`intake_summary`**, dept **`key_aspects`**, dept **excerpt**
- P1 **`conflicts[]`** (read-only)
- **Not** full `markdown_text`, **not** other departments’ drafts

### Evaluator receives

- That dept’s **`draft_content`** only
- Same fixed context: `metadata`, `key_aspects`, §5 rules, excerpt (relevance)
- Evaluators **do not** write to `draft_content`

---

## Evaluator implementation (locked)

| Evaluator | Implementation |
| --------- | -------------- |
| **Readability** | `py-readability-metrics`; pass if FK grade **≤ 12.0** |
| **Relevance** | **Structured** vs dept **`key_aspects`** → `missing_topics[]` |
| **Compliance** | **Rule-based** on p1 §5 **`COMPLIANCE_*`** IDs → `failures[]` with `rule_id`, `message`, `suggested_fix` |

---

## Failure modes (locked)

| Case | Behavior |
| ---- | -------- |
| **QA failure** (eval doesn’t pass) | Retry loop; then per-section **`needs_human_review`** |
| **Infra failure** (LLM down, uncaught pipeline error) | Ticket → **`failed`** + `error_code` / `error_message` (P1 pattern) |
| **Whole ticket on QA fail** | **Never** `discarded` |

**No template draft fallback** when LLM unavailable — ticket **`failed`**, not silent success.

---

## P3 columns — do not touch in P2

Do **not** set in Part 2: **`approval_status`**, **`approver`**, **`approved_at`** (Part 3 only).

---

## Optional stretch (P2-OPT)

- **`RFP_GENERATION_USE_RAG=false`** by default; when **`true`**, generator may call **`retrieve()`** from `data/pipelines/rag.py` before draft.
- Not required for Part 2 acceptance; CI passes without Qdrant.

---

## Locked decisions — master register

**Review date:** 2026-08-06  
**Outcome:** All **27** Part 2 decisions approved as **Option A** (recommended choice in each review). Do not re-open without explicit tech-lead sign-off.

### Core (Decisions 1–10)

| ID | Topic | Choice | Status |
| -- | ----- | ------ | ------ |
| **M9-P2-1** | Graph layout | **One compiled graph**; P2 modules in `data/pipelines/rfp_generation_graph.py`, merged with intake at compile; same `thread_id` | ✅ A |
| **M9-P2-2** | P2 terminal status | **`waiting_for_approval`** when all depts done | ✅ A |
| **M9-P2-3** | Max-iter / partial fail | Per-section **`needs_human_review`**; ticket **not** discarded | ✅ A |
| **M9-P2-4** | Draft trigger | **`POST .../draft` only from `intake_complete`**; **409** on repeat | ✅ A |
| **M9-P2-5** | `evaluation_results` | `{ "latest": EvaluationResult, "history": [...] }` | ✅ A |
| **M9-P2-6** | Compliance evaluator | **Rule-based** on p1 §5 | ✅ A |
| **M9-P2-7** | Readability | FK grade **≤ 12.0** | ✅ A |
| **M9-P2-8** | Generator / evaluator inputs | Dept-scoped; no full doc / cross-dept drafts | ✅ A |
| **M9-P2-9** | Progress | Ticket status + persisted **`draft_status`** per section | ✅ A |
| **M9-P2-10** | Optional RAG | Off by default; **`RFP_GENERATION_USE_RAG=true`** to enable | ✅ A |

### Extended (Decisions 11–19)

| ID | Topic | Choice | Status |
| -- | ----- | ------ | ------ |
| **M9-P2-11** | `overall_passed` | All three dimensions must pass | ✅ A |
| **M9-P2-12** | Relevance | Structured vs **`key_aspects`** → `missing_topics[]` | ✅ A |
| **M9-P2-13** | `draft_status` storage | **Persisted column** on `rfp_department_sections` | ✅ A |
| **M9-P2-14** | P2 invoke | Same **`thread_id`**; hydrate from Postgres; P2 nodes only | ✅ A |
| **M9-P2-15** | Dept parallelism | **Parallel fan-out** per department | ✅ A |
| **M9-P2-16** | `POST .../draft` | **201** + async poll | ✅ A |
| **M9-P2-17** | Infra vs QA failure | QA → `needs_human_review`; infra → ticket **`failed`** | ✅ A |
| **M9-P2-18** | Generators | **One agent/prompt per `department_id`** | ✅ A |
| **M9-P2-19** | Compliance test anchor | **`COMPLIANCE_DUAL_CURRENCY`** in unit tests | ✅ A |

### Implementation micro-locks (M1–M8)

| ID | Topic | Choice | Status |
| -- | ----- | ------ | ------ |
| **M9-P2-M1** | Poll source of truth | **Postgres** for GET/poll; checkpoint for resume only | ✅ A |
| **M9-P2-M2** | P3 columns | Do not set approval fields in P2 | ✅ A |
| **M9-P2-M3** | Section sync | Set **`draft_status`** and **`latest.needs_human_review`** together | ✅ A |
| **M9-P2-M4** | Relevance pass | **`passed` when `missing_topics` is empty** | ✅ A |
| **M9-P2-M5** | Iteration numbering | First eval is **`iteration: 1`** | ✅ A |
| **M9-P2-M6** | P2 start | Keep **`key_aspects`**; initialize **`draft_status`** from `pending` | ✅ A |
| **M9-P2-M7** | No template fallback | LLM unavailable → ticket **`failed`** | ✅ A |
| **M9-P2-M8** | p1 M9-C5 note | Compiled graph lives under **`data/pipelines/`** (supersedes p1 path wording) | ✅ A |

### Inherited from p1 (do not re-open)

| ID | Topic |
| -- | ----- |
| **M9-2** | Manual Start drafting at `intake_complete` |
| **M9-G2** | `MAX_GENERATOR_EVALUATOR_ITERATIONS = 3` |
| **M9-G5** | Compliance SSoT p1 §5 |
| **M9-H7** | BackgroundTasks; no Celery |
| **M9-M1–M9-M4** | Monorepo + Postgres SQLModel |

---

## Locked decisions — confirmed review log

Each row records the decision question, locked choice (**Option A**), rationale, rubric alignment, and rejected alternatives.

### Core

| ID | Question | Locked choice (A) | Rationale | Rubric | Rejected |
| -- | -------- | ----------------- | --------- | ------ | -------- |
| **M9-P2-1** | Where do P2 nodes live and how do they connect to P1? | One compiled graph; P2 in `rfp_generation_graph.py`; merged at compile; same `thread_id` | Single workflow arc; checkpoint continuity; p1 §8 one-graph model | #2, #3 | B: two compiled graphs; C: P2-only graph |
| **M9-P2-2** | P2 terminal ticket status? | **`waiting_for_approval`** when all active depts terminal | Clean P2→P3 handoff; p1 status machine; distinct from P1 `intake_complete` | #3, #4 | B: `draft_complete`; C: stay `under_evaluation` |
| **M9-P2-3** | After max iter without pass? | Section **`needs_human_review`**; ticket still → **`waiting_for_approval`** | Partial QA fail must not discard whole RFP; other depts continue | #2, #3, #4 | B/C: ticket `failed`/`discarded`; D: auto-accept last draft |
| **M9-P2-4** | When can `POST .../draft` run? | Only from **`intake_complete`**; **409** on any other status | Manual trigger (M9-2); idempotent; P3 owns regen path | #4 | B: 200 no-op; C: auto-start; D: retry from `failed` in P2 |
| **M9-P2-5** | `evaluation_results` JSON shape? | `{ "latest": EvaluationResult, "history": [...] }` | Current state for poll; full retry audit; append-only history | #3, #4, #5 | B: flat overwrite; C: array-only; D: separate table |
| **M9-P2-6** | Compliance evaluator approach? | **Rule-based** on p1 §5 `COMPLIANCE_*` IDs | Deterministic; CI-friendly; structured `failures[]` with `rule_id` | #5, #6, #7 | B: LLM judge; C: hybrid; D: monolithic eval |
| **M9-P2-7** | Readability pass threshold? | Flesch-Kincaid grade **≤ 12.0** on `draft_content` | Locked numeric gate; reuses `py-readability-metrics`; persist `threshold_max_grade` | #1, #5 | B: ≤10; C: ≤14; D: LLM subjective |
| **M9-P2-8** | Generator/evaluator input scope? | Dept-scoped: metadata, `key_aspects`, excerpt; not full doc or cross-dept drafts | Isolation per rubric; parallel-safe; P3 owns merge | #1, #2, #5 | B: full markdown; C: metadata only; D: all dept drafts |
| **M9-P2-9** | Progress visibility? | Ticket `status` + persisted **`draft_status`** per section | Dual-level poll; badges; aggregate ticket rules in status machine | #4 | B: eval JSON only; C: ticket stays `intake_complete`; D: WebSocket |
| **M9-P2-10** | RAG in generation? | **`RFP_GENERATION_USE_RAG=false`** default; optional `retrieve()` when true | CI passes without Qdrant; enrichment only, not a gate | #7 | B: always on; C: prod-only on; D: no hook |

### Extended

| ID | Question | Locked choice (A) | Rationale | Rubric | Rejected |
| -- | -------- | ----------------- | --------- | ------ | -------- |
| **M9-P2-11** | `overall_passed` definition? | `readability.passed AND relevance.passed AND compliance.passed` | Strict QA exit; partial passes visible but loop continues | #3, #5, #6 | B: 2 of 3; C: compliance-only; D: weighted score |
| **M9-P2-12** | Relevance evaluator design? | Structured vs dept **`key_aspects`** → **`missing_topics[]`** | Concrete retry feedback; test #2 maps to relevance fail | #5, #6, #3 | B: LLM pass independent of list; C: free-text; D: any aspect |
| **M9-P2-13** | Where does `draft_status` live? | **Persisted column** on `rfp_department_sections` | Fast poll/filter; UI badges; independent of eval JSON shape | #4 | B: derive from eval only; C: checkpoint only; D: new table |
| **M9-P2-14** | P2 graph invoke pattern? | Same **`thread_id`**; hydrate Postgres; **P2 entry only** (skip P1 nodes) | No re-PDF/re-classify; continuous checkpoint; M1 poll from DB | #2, #4 | B: full graph from START; C: new thread_id; D: no LangGraph |
| **M9-P2-15** | Cross-dept execution? | **Parallel fan-out** per `department_id` (LangGraph `Send`) | Rubric #2; P1 workers are sequential — P2 upgrades; test #5 isolation | #1, #2 | B: sequential; C: parallel gen / serial eval; D: one mega-call |
| **M9-P2-16** | `POST .../draft` HTTP contract? | **201** + BackgroundTasks; poll GET until terminal | Matches P1 intake async pattern (M9-H7); non-blocking | #4 | B: 202; C: sync 200; D: SSE |
| **M9-P2-17** | QA vs infra failure? | QA → section **`needs_human_review`**; infra → ticket **`failed`** | Operator vs Camila paths; no conflation of outage and weak draft | #3, #4 | B: ticket `failed` on any eval miss; C: infra as section flag; D: `discarded` |
| **M9-P2-18** | How many generators? | **One prompt/entrypoint per `department_id`** (`GENERATORS` registry) | Rubric #1 explicit; dept-specific tone; active depts only | #1, #2 | B: single shared prompt; C: one call all sections; D: dynamic orchestrator |
| **M9-P2-19** | Compliance unit-test anchor? | **`COMPLIANCE_DUAL_CURRENCY`** (USD-only draft fixture) | Deterministic; seed #1 pricing context; pairs with test #2 relevance | #6, #7 | B: `NO_COMPETITORS`; C: `BRAND_PILLARS`; D: rotate rules |

### Micro-locks

| ID | Question | Locked choice (A) | Rationale | Rubric | Rejected |
| -- | -------- | ----------------- | --------- | ------ | -------- |
| **M9-P2-M1** | Poll source of truth? | **Postgres** for GET/UI; checkpoint for resume/debug only | Single SSoT; matches P1 persist pattern; no SQLite in API reads | #4 | B: checkpoint primary; C: dual merge; D: in-memory |
| **M9-P2-M2** | P3 approval columns in P2? | **Do not set** `approval_status`, `approver`, `approved_at` | Phase boundary; P3 owns HITL; `waiting_for_approval` ≠ approved | — | B: `pending`; C: auto-approve on pass; D: set `approver` early |
| **M9-P2-M3** | Human-review handoff sync? | **`draft_status`** and **`latest.needs_human_review`** in one persist | No UI/API drift; same rule on pass (`passed` + `false`) | #3, #4 | B/C: single field only; D: allow mismatch |
| **M9-P2-M4** | `relevance.passed` rule? | **`passed = (len(missing_topics) == 0)`**; `addresses_key_aspects` mirrors | Deterministic; empty `key_aspects` → pass with optional trace warning | #5, #6, #3 | B: LLM bool independent; C: 80% coverage; D: any aspect |
| **M9-P2-M5** | Iteration numbering? | **1-based**; first eval **`iteration: 1`**; stop retry when **`iteration >= 3`** | Matches JSON example and M9-G2; UI “Attempt 1 of 3” | #3 | B: 0-based; C: 4 attempts; D: dual counters |
| **M9-P2-M6** | P2 start initialization? | **Keep P1 `key_aspects`**; init **`draft_status`** from **`pending`** → **`drafting`** | P1→P2 handoff; relevance baseline stable; no re-routing | #4, #7 | B: re-extract aspects; C: clear aspects; D: duplicate into eval JSON |
| **M9-P2-M7** | LLM unavailable? | **No template fallback** — ticket **`failed`**, no placeholder draft | Honest outage signal; eval loop never runs on fake text | #3, #4 | B: static template; C: empty draft + eval; D: infinite retry |
| **M9-P2-M8** | Graph file location? | **`data/pipelines/`** (`rfp_intake_graph.py` + `rfp_generation_graph.py`); re-export via `services/api/rfp/graph.py` | M9-M2 monorepo layout; P1 already moved graph; supersedes **M9-C5 path only** | — | B: `services/api/rfp/`; C: split across layers; D: `scripts/` |

**Note on M9-C5:** p1 locked “one graph + `thread_id`” under `services/api/rfp/`. P1 implementation and P2 extend **`data/pipelines/`** — the **one-graph / thread_id** semantics are unchanged; only directory wording is superseded.

---

## Backoffice UI (Part 2)

Extend **`/rfp/[id]`**:

- **“Start drafting”** when `status === intake_complete`
- Per department: draft text, evaluation history (`iteration`, pass/fail, `failures[]`)
- Badges: **`draft_status`**, **`needs_human_review`**
- Ticket badges: **Drafting**, **Under evaluation**, **Waiting for approval**

**Out of scope:** approve/reject (P3), final document download (P3).

---

## Database changes (Part 2)

Add to **`rfp_department_sections`**:

| Column | Type | Notes |
| ------ | ---- | ----- |
| **`draft_status`** | `varchar(32)` | `pending` \| `drafting` \| `evaluating` \| `passed` \| `needs_human_review` |

Existing columns used: **`draft_content`**, **`evaluation_results`**.

---

## Testing requirements

### Unit tests (`services/api/tests/pipelines/`)

| # | Test | Assert |
| - | ---- | ------ |
| 1 | **Success** | Generator produces draft; all evaluators pass; `overall_passed: true`; `draft_status: passed` |
| 2 | **Generic evaluation failure** | Relevance fail (`missing_topics`) → retry with feedback; `iteration` increments |
| 3 | **Context-anchored compliance failure** | USD-only draft → `COMPLIANCE_DUAL_CURRENCY` in `compliance.failures` |
| 4 | **Max iterations** | After 3 failures → `needs_human_review: true`; ticket not discarded |
| 5 | **Dept isolation** | One dept failing does not wipe another dept’s draft |

Mock LLM in CI where needed. Generic failure = **relevance**; compliance anchor = **`COMPLIANCE_DUAL_CURRENCY`**.

### API / integration

- `POST .../draft` from `intake_complete` → poll until `waiting_for_approval`
- **409** on second draft POST
- P1 regression suite stays green

---

## Evaluation checklist (Part 2 acceptance — official rubric)

Verify before Part 3:

- [x] Each department has its own **generator agent**, clearly separated from the others
- [x] **Evaluators run in parallel** and don’t block execution across other departments
- [x] The system correctly applies the **generator–evaluator loop**, including the **iteration limit** and **`needs_human_review`** handoff when exhausted
- [x] The **ticket accurately reflects** generation and evaluation progress in real time
- [x] Evaluation output follows the **`EvaluationResult`** shape (structured **readability / relevance / compliance** — not unstructured free text)
- [x] Unit tests cover **success**, a **generic evaluation-failure** case, and **one context-anchored compliance failure** (`COMPLIANCE_DUAL_CURRENCY`)
- [x] The implementation uses the **guidelines and formats** defined in **`CONTEXT.md`** (pillars) and **p1 §5** (compliance rule IDs)

Supporting gates:

- [x] `POST /rfp/tickets/{id}/draft` + poll via existing GET
- [x] P2 handoff: every dept has `draft_content` + `evaluation_results`
- [x] Monorepo: single API; pipeline under `data/pipelines/`; Postgres SQLModel
- [x] P1 tests still green; Support Agent unchanged

---

## Explicit non-goals (Part 2)

- Human approval / LangGraph `interrupt()` (Part 3)
- Final merged document (Part 3)
- CEO approval workflow execution (Part 3)
- Second `POST .../draft` from non-`intake_complete` (P3 reject → regen path)
- Celery / second HTTP service
- Merging RFP into Support Agent graph
- Mandatory RAG / Qdrant for acceptance

---

## Phase plan (implement in order)

### Phase 0 — Schema

1. Add **`draft_status`** column; extend schemas/API section responses.
2. **Gate:** migration applies; GET returns new fields.

### Phase 1 — Pipeline helpers

1. `data/pipelines/rfp_generation.py` — per-dept generators, evaluators, loop helpers.
2. **Gate:** unit tests for evaluators (compliance + relevance + readability) pass with mocks.

### Phase 2 — Graph

1. `data/pipelines/rfp_generation_graph.py` — merge with intake graph; parallel dept fan-out.
2. **Gate:** invoke from fixture ticket reaches `waiting_for_approval` in test DB.

### Phase 3 — API + service

1. `POST /rfp/tickets/{ticket_id}/draft`; `draft_service.py`; BackgroundTasks.
2. **Gate:** API test: draft → poll terminal; 409 on repeat.

### Phase 4 — Backoffice

1. Start drafting button; section draft/eval UI; status badges.
2. **Gate:** manual E2E on seed #1 ticket after intake.

### Phase 5 — Tests + regression

1. Full P2 unit + API tests; P1 suite green.
2. **Gate:** evaluation checklist above all checked.

---

## Part 3 pointer

Read p1 §1–§9, then **[context-27-milestone-9-rfp-approval-document-p3.md](./context-27-milestone-9-rfp-approval-document-p3.md)** (**14 decisions locked 2026-08-06**).

**Gate:** Part 2 acceptance complete before P3 implementation.

---

## Verification commands

```bash
# Part 1 regression (must stay green)
cd services/api && uv run python -m pytest \
  tests/pipelines/test_rfp_intake.py \
  tests/pipelines/test_rfp_classifier_worker.py \
  tests/test_rfp_api.py \
  tests/test_rfp_models.py -q

# Part 2 unit tests (after implementation)
cd services/api && uv run python -m pytest \
  tests/pipelines/test_rfp_generation.py \
  tests/pipelines/test_rfp_evaluator.py -q
```

---

## Part 1 companion

Shared spec + Part 1 detail: [context-27-milestone-9-rfp-intake-routing-p1.md](./context-27-milestone-9-rfp-intake-routing-p1.md)

---

_Internal document — Brasaland · Context 27 Part 2 · Milestone 9 RFP response generation & evaluation_
