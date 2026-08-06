# Context 27 — Milestone 9 Agentic Workflow: Approval & Document Completion (Part 3)

**Ticket:** Milestone 9 Part 3 — human-in-the-loop approval per department, interrupt/resume, arbitration, CEO gate, final document synthesis  
**Type:** LangGraph extension (`interrupt()` / `Command(resume)`) + FastAPI `/rfp` approval endpoints + backoffice UI + Postgres + tests  
**Branch:** `milestone-9-agentic-workflow-rfp-approval` (suggested)  
**Status:** Spec locked — **all 14 Part 3 decisions confirmed** — read p1 §1–§9 and p2 before implementation  
**Depends on:** [context-27-milestone-9-rfp-intake-routing-p1.md](./context-27-milestone-9-rfp-intake-routing-p1.md) (**§1–§9 + P1 merged**), [context-27-milestone-9-rfp-response-generation-p2.md](./context-27-milestone-9-rfp-response-generation-p2.md) (**P2 complete**), [context-22-route-conventions.md](./context-22-route-conventions.md), root [`CONTEXT.md`](../../CONTEXT.md) (CEO name, brand pillars only)  
**Companions:** p1 (intake), p2 (generation + evaluation) — **this file completes Milestone 9**  
**Stakeholders:** Camila Ospina (Marketing — process owner); Mariana Restrepo (CEO gate); Brasaland Digital backoffice users

> **Read p1 §1–§9 and p2 before this file.** Department IDs, compliance rule IDs, status names, monorepo layout (M9-M1–M9-M4), and cross-part locks are inherited from p1. P2 handoff fields (`draft_content`, `evaluation_results`, `draft_status`) are prerequisites.

---

## Ticket brief (Part 3)

Part 2 produces per-department drafts and self-evaluation. Part 3 adds **real human approval** before any section is treated as signed, **parallel department interrupts** (one dept waiting must not block others), **cross-dept arbitration**, optional **CEO sign-off**, and **deterministic final document merge** — one continuous workflow from Part 1 upload through **`completed`**.

Tech lead intent:

> We already generate and self-evaluate every section, but nobody signs a pricing proposal without a human from each department giving the green light. This is the last piece — it must feel like one continuous experience, not three projects taped together. Pause before irreversible actions, persist with a checkpointer, resume exactly where we left off. When something breaks in production, I need to see which agent did what and in what order.

### What to build

- **Human approval per department** — LangGraph **`interrupt()`** before a section is **`approved`**; not another automatic evaluator.
- **Checkpointer + resume** — state persisted before each interrupt; **`Command(resume=...)`** explicit entry — **not** restart from P1 START.
- **Parallel branches** — pause only the waiting department branch; other departments keep moving.
- **Arbitration node** — rule-based resolution when departments conflict; **`MAX_ARBITRATION_ITERATIONS = 2`** (p1 M9-G3); not LLM freestyle.
- **Final document** — **`ultimate_document_synthesizer`** after all gates pass; ticket → **`completed`**.
- **Traceability** — every P3 node logs **`{ node, agent, input, output, timestamp }`** to graph state and **`rfp_trace_events`**.
- **Extend `/rfp/[id]`** — per-dept approve / reject / request changes; final document download.

### Acceptance criteria (Milestone 9 terminal)

An RFP travels **P1 → P2 → P3** end to end: pauses for human approval per department without blocking others, finishes with an automatically generated final document, with full step traceability. Reproducible E2E/integration path exists (not UI-only demo).

### Out of scope (reference only — do not put in implementation)

- Long essays on guardrails vs interrupts — **one line:** guardrails = automated validation; interrupt = human judgment on irreversible sign-off.
- Visual workflow diagrams (optional assets only).
- Support Agent memory / approval patterns (context-26) — RFP uses LangGraph native **`interrupt()`**.
- Mandatory Knowledge-base retrieve.
- Department RBAC (p1 stretch).
- LLM merge or LLM arbitration.

---

## Prerequisite gate (Part 2)

Do **not** start Part 3 until Part 2 acceptance is complete:

- [ ] Every active dept has **`draft_content`** + **`evaluation_results`**
- [ ] P2 terminal ticket status **`waiting_for_approval`**
- [ ] **`POST .../draft`** + poll; **409** on repeat from non-`intake_complete`
- [ ] P2 unit tests green (`test_rfp_generation.py`, `test_rfp_evaluator.py`)
- [ ] P1 regression suite green

---

## Design questions — locked answers

| Question | Lock |
| -------- | ---- |
| **What happens if a department rejects after the interrupt?** | **`reject`** → section **`approval_status: rejected`**; ticket **blocked** from **`completed`**. **No** P1 restart, **no** ticket discard. Recovery: explicit **`POST .../sections/{dept}/regenerate`** (dept-scoped P2 loop) then re-interrupt. **`request_changes`** auto-triggers the same dept-scoped regen. |
| **How do you namespace `thread_id`?** | Phase suffixes per ticket: **`rfp:{ticket_id}:intake`**, **`:generation`**, **`:approval`**. UUID **`ticket_id`** isolates concurrent RFPs. One **`:approval`** thread with parallel **`Send`** branches — **not** per-dept **`thread_id`** by default. Regen during approval stays on **`:approval`**, not **`:generation`**. Supersedes bare **`rfp:{ticket_id}`** wording in M9-C5; semantics unchanged. |
| **Minimum information at the approval point?** | **`prepare_approval_packet`**: metadata (client, service, deadline), dept identity + owner, **`key_aspects`**, **`draft_content`**, **`draft_status`**, **`evaluation_summary`** from **`evaluation_results.latest`**, **`requires_ceo_approval`**, **`conflicts[]`** when non-empty. **Exclude** other depts’ drafts, full PDF/markdown. |
| **Who arbitrates contradictory interdependent departments?** | **Camila (`marketing`)** — narrative arbiter. **`arbitration_node`** applies **deterministic rules** (p1 §5 compliance → strictest operational → marketing on brand/validity). **`MAX_ARBITRATION_ITERATIONS = 2`**. Not LLM negotiation. |

---

## Guardrails vs interrupts (one line)

**Guardrails** (automated): validate resume payload enum, pending interrupt exists, section has terminal **`draft_status`**, business preconditions — **400/409**, no graph resume.  
**Interrupts** (human): approve / reject / request changes at dept interrupt; CEO approve / reject — judgment on irreversible sign-off.

---

## Status machine (Part 3 segment)

Extends p1 §4.3:

```text
waiting_for_approval → [P3 auto-start] → awaiting_department_approval → …
  → (all depts approved) → detect_conflicts / arbitrating →
  → (if requires_ceo_approval) awaiting_ceo_approval →
  → ultimate_document_synthesizer → completed
```

| Status | When (P3) | Notes |
| ------ | --------- | ----- |
| `waiting_for_approval` | P2 terminal; P3 may be starting (brief) | P3 entry gate |
| `awaiting_department_approval` | ≥1 section **`awaiting_human`** | Optional but recommended for UI |
| `arbitrating` | **`arbitration_node`** running | Optional; may infer from trace |
| `awaiting_ceo_approval` | All depts approved; CEO interrupt pending | Seed #1 path |
| `completed` | Final doc persisted | **Workflow terminal** — not `done` |
| `failed` | Infra/pipeline only | **Not** human reject |

**Avoid `done`** as status code — UI label “Done” via **`STATUS_LABELS`** on **`completed`**.

**P3 entry (M9-P3-3):** **Auto-start** when P2 sets **`waiting_for_approval`** — **`BackgroundTasks`** → **`invoke_rfp_approval`**. No manual **“Start approval”** on the default path.

### Per-section `approval_status` (P3 — persisted)

Unset → **`awaiting_human`** → **`approved`** | **`rejected`** | **`changes_requested`** (transient during regen)

| Value | When |
| ----- | ---- |
| `null` / unset | Before P3 touches section |
| `awaiting_human` | At **`interrupt()`**; shown in UI |
| `approved` | Human **`approve`** |
| `rejected` | Human **`reject`** — blocks **`completed`** until recovery |
| `changes_requested` | During dept regen; clears when regen completes → **`awaiting_human`** |

**Keep P2 `draft_status` separate** — QA outcome vs human sign-off. Section with **`draft_status: needs_human_review`** may still receive human **`approve`**.

---

## Human decisions (M9-P3-6)

| Decision | Section | Graph | Ticket |
| -------- | ------- | ----- | ------ |
| **`approve`** | **`approved`**, set **`approver`**, **`approved_at`** | Resume branch → join path | Unchanged until all gates pass |
| **`request_changes`** | **`changes_requested`** → regen → **`awaiting_human`** | Dept-scoped P2 loop → re-interrupt | Stays in approval flow; other depts unaffected |
| **`reject`** | **`rejected`** | Branch stops; join blocker | **Cannot** reach **`completed`** until explicit **`regenerate`** recovery |

**Never:** P1 restart, full-ticket **`POST .../draft`** from approval phase, ticket **`discarded`** / **`failed`** on human reject.

---

## Regeneration (M9-P3-7)

**Dept-scoped only.**

| Trigger | Path |
| ------- | ---- |
| **`request_changes`** | Graph auto-runs P2 **`generate_eval_dept`** for that dept after resume |
| **`reject` recovery** | **`POST /rfp/tickets/{ticket_id}/sections/{department_id}/regenerate`** |

**Regen steps:**

1. Reset section: **`draft_status → drafting`**; clear **`approval_status`**, **`approver`**, **`approved_at`**
2. Pass human **`comment`** + prior **`failures[]` / `missing_topics[]`** into generator retry (P2 pattern)
3. Run P2 loop for **one dept**; persist draft + eval
4. Re-enter **same dept’s approval interrupt** on **`rfp:{ticket_id}:approval`**

**Never** switch to **`:generation`** checkpoint thread mid-approval.

---

## Graph architecture (Part 3)

**One compiled RFP LangGraph** — P3 nodes in **`data/pipelines/rfp_approval_graph.py`**, merged at compile with intake + generation (M9-P2-1 pattern).

### Entry router (extend P2)

| `invoke_mode` | Entry node |
| ------------- | ---------- |
| `intake` | `convert_pdf` |
| `generation` | `draft_start` |
| `approval` | `approval_start` |

### P3 flow

```text
approval_start
  → Send(dept_approval_branch) × len(departments_needed)
       prepare_approval_packet
       → interrupt("dept_approval", packet)
       → validate_human_response          (guardrail)
       → route_decision:
             approve           → mark_dept_approved → END (branch)
             request_changes   → dept_regen → re-interrupt (loop)
             reject            → mark_dept_rejected → END (branch)
  → approval_join (all branches terminal)
  → detect_conflicts
  → IF conflicts: arbitration_node (loop, max 2)
  → IF requires_ceo_approval: ceo_approval_interrupt → validate_ceo_response
  → ultimate_document_synthesizer
  → approval_finalize → END (completed)
```

### Parallelism (M9-P3-4)

| Scope | Parallel? |
| ----- | --------- |
| **Across departments (approval)** | **Yes** — **`Send`** per dept; **`interrupt()`** inside each branch |
| **One dept waiting** | **Must not block** other depts from interrupt/resume |
| **Across tickets** | **Yes** — separate **`thread_id`** / ticket rows |

**Mandatory test:** approve dept **B** while dept **A** remains **`awaiting_human`** — prove via Postgres + **`rfp_trace_events`**.

### Invoke / resume (M9-P3-9)

| Operation | Function | When |
| --------- | -------- | ---- |
| **Start** | **`invoke_rfp_approval(state)`** | P3 auto-start; recovery **`POST .../approval/start`** |
| **Resume** | **`resume_rfp_approval(ticket_id, payload)`** | Human decision POST → **`Command(resume=payload)`** |

**Never** **`graph.invoke(initial_state)`** from START for resume.

**Order on decision POST:** validate → persist Postgres + trace → **`Command(resume)`**.

---

## Checkpoint `thread_id` (M9-P3-10)

| Phase | `thread_id` |
| ----- | ----------- |
| P1 intake | `rfp:{ticket_id}:intake` |
| P2 generation | `rfp:{ticket_id}:generation` |
| P3 approval | `rfp:{ticket_id}:approval` |

**Note:** P2 implementation may use bare **`rfp:{ticket_id}`** for intake today — align to **`:intake`** suffix when touching intake invoke (optional migration; dev checkpoints may orphan).

**Poll SSoT (inherited M9-P2-M1):** Postgres for GET/UI; checkpoint for resume/debug only.

---

## Approval packet (M9-P3-16)

### Department packet (at interrupt)

| Field | Source |
| ----- | ------ |
| `ticket_id`, `department_id`, `department_label`, `department_owner` | Ticket + constants |
| `client_name`, `service_type` / `scope`, `deadline` | **`metadata`** |
| `key_aspects[]` | Section |
| `draft_content` | Section |
| `draft_status` | Section |
| `evaluation_summary` | Derived from **`evaluation_results.latest`** |
| `requires_ceo_approval` | Ticket |
| `conflicts[]` | Ticket (when non-empty) |

**`evaluation_summary` shape (derived):**

```json
{
  "iteration": 2,
  "overall_passed": false,
  "needs_human_review": true,
  "readability_passed": true,
  "relevance_passed": false,
  "compliance_passed": true,
  "missing_topics": ["peak season staffing"],
  "compliance_failures": [{ "rule_id": "COMPLIANCE_DUAL_CURRENCY", "message": "..." }]
}
```

**Excluded:** full **`markdown_text`**, source PDF, other depts’ **`draft_content`**.

### CEO packet (M9-P3-11)

Adds: **`estimated_contract_value_usd`**, threshold reason, **per-dept approved excerpts** (~300 chars each), **`arbitration_resolutions[]`**, remaining **`conflicts[]`** (should be empty post-arbitration).

Packet is: interrupt value, GET detail UI source, trace **`input`** (use length + preview for large drafts in trace).

---

## Arbitration (M9-P3-12)

**Placement:** After **`approval_join`**, before CEO gate.

**Triggers:**

1. Non-empty P1 **`conflicts[]`** on ticket  
2. P3 **`detect_conflicts`** — deterministic scan of **approved** drafts (lead times, dual-currency pairs, validity language, etc.)

**Resolution precedence (deterministic — not LLM):**

1. p1 §5 **`COMPLIANCE_*`** rules  
2. **Strictest operational constraint** (longest lead time, highest cost floor, etc.)  
3. **`marketing`** claim wins on brand / exclusivity / validity language  
4. Still tied → **`arbitration_unresolved`** — counts toward iteration cap  

**Output example:**

```json
{
  "field": "deadline",
  "winning_department_id": "operations",
  "resolved_value": "2026-09-15",
  "rule_id": "ARBITRATION_STRICTEST_OPERATIONAL",
  "iteration": 1
}
```

**Cap:** **`MAX_ARBITRATION_ITERATIONS = 2`** — distinct from P2 **`MAX_GENERATOR_EVALUATOR_ITERATIONS = 3`**.

**After exhaustion:** **`arbitration_exhausted: true`**; block **`completed`**; recovery via dept **`request_changes`** / **`regenerate`**.

**Tests:** inject **`conflicts[]`** — do not rely on seed PDFs alone (P1 synthesizer may return empty conflicts).

---

## CEO gate (M9-P3-11)

When **`requires_ceo_approval`** (p1 §5, **`COMPLIANCE_CEO_THRESHOLD_50K`**):

- **After** all dept **`approved`** + arbitration clear  
- **Before** **`ultimate_document_synthesizer`**  
- **`ceo_approval_interrupt`** — ticket-level  
- Decisions: **`approve`** \| **`reject`** only (no **`request_changes`**)  
- Narrative owner: **Mariana Restrepo** (p1 §8, root **`CONTEXT.md`**)  
- **E2E:** seed #1 must exercise CEO path  

When **`requires_ceo_approval: false`** (seed #2): skip CEO node.

---

## Final document (M9-P3-13)

**Node:** **`ultimate_document_synthesizer`** in **`data/pipelines/rfp_final_document.py`**.

**Hard prerequisites (all required):**

- Every active section **`approval_status: approved`**
- No blocking **`rejected`**
- Not **`arbitration_exhausted`**
- CEO **`approve`** if **`requires_ceo_approval`**

**Merge:** **Deterministic template** — **not** LLM.

1. Header: client, service, location, deadline, generated timestamp  
2. **`intake_summary`**  
3. Department sections in fixed order: **`marketing` → `operations` → `procurement` → `training`** (only active depts)  
4. Each section: approved **`draft_content`**  
5. Appendix: **`arbitration_resolutions[]`** if any  
6. Footer: validity line per **`COMPLIANCE_VALIDITY_30_DAYS`**

**Storage:**

| Column | Table |
| ------ | ----- |
| `final_document_markdown` | **`rfp_tickets`** (TEXT) |
| `final_document_generated_at` | **`rfp_tickets`** |

Optional file mirror: **`data/raw/intakes/{ticket_id}/final_proposal.md`** (gitignored).

**Ticket status:** **`completed`**.

**Idempotency:** same inputs → same output; overwrite columns on retry; log in trace.

---

## Trace shape (M9-P3-14)

Every P3 node via **`_trace_p3()`**:

```json
{
  "node": "dept_approval_interrupt",
  "agent": "human_approval_gate",
  "input": { "department_id": "operations", "draft_status": "passed" },
  "output": { "status": "awaiting_human" },
  "timestamp": "2026-08-06T19:06:00.000Z"
}
```

Dual-write: graph **`trace_events`** + **`rfp_trace_events`**.

### Agent mapping

| Node | `agent` |
| ---- | ------- |
| `approval_start`, `prepare_approval_packet`, `approval_join`, `approval_finalize` | `approval_orchestrator` |
| `dept_approval_interrupt` | `human_approval_gate` |
| `validate_human_response`, `validate_ceo_response` | `approval_guardrail` |
| `mark_dept_approved`, `mark_dept_rejected` | `approval_orchestrator` |
| `dept_regen` | `department_generator` |
| `detect_conflicts` | `conflict_detector` |
| `arbitration_node` | `arbitration_node` |
| `ceo_approval_interrupt` | `ceo_approval_gate` |
| `ultimate_document_synthesizer` | `document_synthesizer` |

Large **`draft_content`**: trace **`draft_content_length`** + **`draft_content_preview`** (first ~200 chars), not full text.

E2E: trace chain spans P1 + P2 + P3 nodes in order for one **`ticket_id`**.

---

## API (extend `/rfp`)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `POST` | `/rfp/tickets/{ticket_id}/sections/{department_id}/decision` | Human **`approve`** \| **`reject`** \| **`request_changes`** |
| `POST` | `/rfp/tickets/{ticket_id}/sections/{department_id}/regenerate` | Reject recovery; dept-scoped regen |
| `POST` | `/rfp/tickets/{ticket_id}/ceo/decision` | CEO **`approve`** \| **`reject`** |
| `POST` | `/rfp/tickets/{ticket_id}/approval/start` | **Recovery-only** idempotent P3 start |
| `GET` | `/rfp/tickets/{ticket_id}/final-document` | Full merged markdown |
| `GET` | `/rfp/tickets/{ticket_id}` | Poll; extended approval + final doc metadata |

### `POST .../sections/{department_id}/decision`

Request:

```json
{
  "decision": "approve",
  "comment": "Optional — recommended for reject / request_changes"
}
```

- **200** on success  
- **400** invalid enum / body  
- **404** ticket or section not found  
- **409** no pending interrupt / wrong phase / already decided  

### `GET .../final-document`

- **200** — `{ ticket_id, final_document_markdown, generated_at }`  
- **404** — no final doc yet  

### GET detail extensions

- Section: **`approval_status`**, **`approver`**, **`approved_at`** (already in schema)  
- Ticket: **`has_final_document`**, **`final_document_length`**, **`arbitration_exhausted`** (when applicable)  

Auth: any authenticated backoffice user (p1 M9-E1, M9-E2).

---

## Graph state extensions (Part 3)

Add to **`RfpGraphState`**:

```python
# P3 approval (parallel branches merge via reducers)
department_approval_statuses: Annotated[dict[str, str], merge_dicts]
arbitration_round: int
arbitration_resolutions: Annotated[list[dict[str, Any]], operator.add]
arbitration_exhausted: bool
ceo_approved: bool
final_document_markdown: str | None
```

---

## Monorepo layout (inherited M9-M1–M9-M4)

| Layer | Path |
| ----- | ---- |
| HTTP (thin) | `services/api/rfp/routes.py`, `approval_service.py` |
| ORM / repository | `services/api/rfp/models.py`, `repository.py` |
| **Approval graph** | `data/pipelines/rfp_approval_graph.py` |
| **Arbitration** | `data/pipelines/rfp_arbitration.py` |
| **Final document** | `data/pipelines/rfp_final_document.py` |
| **Graph invoke** | `data/pipelines/rfp_intake_graph.py` — `invoke_rfp_approval`, `resume_rfp_approval` |
| Graph re-export | `services/api/rfp/graph.py` |
| Tests | `test_rfp_approval.py`, `test_rfp_arbitration.py`, `test_rfp_final_document.py`, `test_rfp_e2e.py` |
| CLI | `scripts/rfp_e2e_smoke.py` |

Call chain:

```text
P2 generation_finalize → BackgroundTasks → approval_service.run_approval_background_task
  → invoke_rfp_approval (invoke_mode=approval, thread :approval)
  → interrupt per dept → poll GET

POST .../decision → approval_service → persist Postgres → resume_rfp_approval(Command(resume=...))
  → graph continues → eventual completed + final_document
```

---

## Backoffice UI (Part 3)

Extend **`/rfp/[id]`** — replace P3 placeholder (“later milestone Part 3”):

- When section **`awaiting_human`**: show approval packet + **Approve / Request changes / Reject** (+ optional comment)
- Banner when **`needs_human_review`**: “Automated QA did not pass — you may still approve.”
- When **`awaiting_ceo_approval`**: CEO panel (**Approve / Reject**)
- When **`completed`**: **Download final proposal** → **`GET .../final-document`**
- Extend polling for **`awaiting_department_approval`**, **`awaiting_ceo_approval`**, until **`completed`**
- Client: extend **`uis/backoffice/lib/rfp.ts`**

**Out of scope:** Support chat approvals (p1 §9).

---

## Database changes (Part 3)

### `rfp_tickets`

| Column | Type | Notes |
| ------ | ---- | ----- |
| `final_document_markdown` | TEXT, nullable | Merged proposal |
| `final_document_generated_at` | TIMESTAMP, nullable | Set at synthesis |

### `rfp_department_sections`

Use existing columns (P1/P2 prepared):

| Column | P3 use |
| ------ | ------ |
| `approval_status` | **`awaiting_human`**, **`approved`**, **`rejected`**, **`changes_requested`** |
| `approver` | Authenticated user display on decision |
| `approved_at` | UTC timestamp on decision |

Add **`ensure_rfp_schema`** additive migrations for new ticket columns (same pattern as P2 **`draft_status`**).

---

## Locked decisions — master register

**Review date:** 2026-08-06  
**Outcome:** All **14** Part 3 decisions approved. Do not re-open without explicit tech-lead sign-off.

| ID | Topic | Choice | Status |
| -- | ----- | ------ | ------ |
| **M9-P3-3** | P3 entry | **Auto-start** on **`waiting_for_approval`** via BackgroundTasks | ✅ |
| **M9-P3-4** | Graph shape | Parallel **`Send`** + per-dept **`interrupt()`**; join when all terminal | ✅ |
| **M9-P3-6** | Human decisions | **`approve`** \| **`reject`** \| **`request_changes`** | ✅ |
| **M9-P3-7** | Regen | Dept-scoped P2 loop; **`POST .../regenerate`** for reject recovery | ✅ |
| **M9-P3-9** | Resume | **`Command(resume)`** on **`:approval`**; decision POST endpoints | ✅ |
| **M9-P3-10** | Checkpoints | Phase suffixes **`:intake`**, **`:generation`**, **`:approval`** | ✅ |
| **M9-P3-11** | CEO gate | After depts + arbitration; Mariana; **`approve`** \| **`reject`** only | ✅ |
| **M9-P3-12** | Arbitration | Rule-based; max **2** iter; Camila narrative | ✅ |
| **M9-P3-13** | Final doc | Deterministic merge → Postgres; **`completed`** | ✅ |
| **M9-P3-14** | Trace | **`{ node, agent, input, output, timestamp }`** per P3 node | ✅ |
| **M9-P3-15** | Status + E2E | Full enum table; integration + **`rfp_e2e_smoke.py`** | ✅ |
| **M9-P3-16** | Approval packet | Minimum fields at dept + CEO interrupt | ✅ |

### Inherited from p1/p2 (do not re-open)

| ID | Topic |
| -- | ----- |
| **M9-G3** | **`MAX_ARBITRATION_ITERATIONS = 2`** |
| **M9-G2** | **`MAX_GENERATOR_EVALUATOR_ITERATIONS = 3`** (P2 regen only) |
| **M9-G1** | Terminal **`completed`** |
| **M9-G4** | **`requires_ceo_approval`** if **> $50k USD/year** |
| **M9-P2-M1** | Postgres poll SSoT |
| **M9-P2-M2** | P3 owns **`approval_status`**, **`approver`**, **`approved_at`** |
| **M9-H7** | BackgroundTasks; no Celery |
| **M9-M1–M9-M4** | Monorepo + Postgres SQLModel |

---

## Locked decisions — review log (summary)

| ID | Question | Locked choice | Rejected |
| -- | -------- | ------------- | -------- |
| **M9-P3-3** | P3 start trigger? | Auto-start on **`waiting_for_approval`** | Manual “Start approval” as default |
| **M9-P3-4** | Parallel interrupts? | **`Send`** + per-branch **`interrupt()`** | Sequential dept approval; ticket-level interrupt |
| **M9-P3-6** | Human decision set? | Three enums with distinct graph paths | Binary approve/reject only |
| **M9-P3-7** | Reject / changes regen? | Dept-scoped P2; no P1 restart | Full ticket draft; new ticket |
| **M9-P3-9** | Resume mechanism? | **`Command(resume)`** + explicit POST | Full graph invoke from START |
| **M9-P3-10** | **`thread_id`**? | Phase suffixes per ticket | Single thread all phases |
| **M9-P3-11** | CEO placement? | After depts + arbitration, before synthesis | CEO before depts; after final doc |
| **M9-P3-12** | Arbitration? | Rule-based node, max 2 iter | LLM negotiation; unlimited loop |
| **M9-P3-13** | Final document? | Deterministic template, Postgres storage | LLM merge; file-only storage |
| **M9-P3-14** | Trace? | Full envelope on every P3 node | **`node`** only |
| **M9-P3-15** | E2E proof? | **`test_rfp_e2e.py`** + smoke script | Manual UI only |
| **M9-P3-16** | Approval UI data? | Structured packet per dept | Full PDF / merged doc at interrupt |

---

## Testing requirements (M9-P3-15)

### Unit tests (`services/api/tests/pipelines/`)

| File | Coverage |
| ---- | -------- |
| **`test_rfp_approval.py`** | Interrupt + resume; **`validate_human_response`**; parallel non-blocking (approve B while A waiting); CEO skip/path |
| **`test_rfp_arbitration.py`** | Injected **`conflicts[]`**; precedence rules; **`MAX_ARBITRATION_ITERATIONS`** exhaustion |
| **`test_rfp_final_document.py`** | Deterministic merge; gates block synth when unapproved |
| **`test_rfp_e2e.py`** | P1 intake → P2 draft → simulated approvals → **`completed`** |

| # | Rubric test | Assert |
| - | ----------- | ------ |
| 1 | **Interrupt + resume approve** | Checkpoint exists; resume continues from interrupt; section **`approved`** |
| 2 | **Parallel non-blocking** | Approve ops while marketing **`awaiting_human`**; ticket ≠ **`completed`** |
| 3 | **Iteration limit** | Arbitration exhausted after **2** rounds; not P2 gen-eval cap |
| 4 | **Arbitration on disagreement** | Injected conflict → **`arbitration_node`** → deterministic resolution |

### E2E paths

**Seed #2 (fast — no CEO):** intake → draft → approve all depts → **`completed`** + **`has_final_document`**.

**Seed #1 (CEO):** intake → draft → approve 4 depts → **`awaiting_ceo_approval`** → CEO approve → **`completed`**.

**CLI mirror:** **`scripts/rfp_e2e_smoke.py`** (simulated decision POSTs).

Use **`reset_graph_cache()`** / isolated checkpoint DB in tests (agent memory test pattern).

### Handoff assertions

| Handoff | Assert |
| ------- | ------ |
| P2 → P3 | All depts terminal **`draft_status`**; **`draft_content`** + **`evaluation_results`** present |
| P3 → **`completed`** | All depts **`approved`**; final doc length > 0; status monotonic |
| Full trace | P1 + P2 + P3 nodes in **`rfp_trace_events`** order |

P1 + P2 regression suites stay green.

---

## Evaluation checklist (Part 3 acceptance — official rubric)

- [ ] Flow pauses before each dept approval and persists state (checkpointer)
- [ ] Pause affects only that dept branch — other depts proceed (test: approve B while A interrupted)
- [ ] Resume from interrupt point — not full restart
- [ ] **`thread_id`** namespaced by ticket + phase suffix; concurrent tickets isolated
- [ ] **`MAX_ARBITRATION_ITERATIONS = 2`** verifiable in code
- [ ] Arbitration fires on conflict; rule-based — not LLM freestyle
- [ ] Every node logs **agent, input, output, timestamp**
- [ ] Final doc only after all approvals (+ CEO if required)
- [ ] Ticket **`completed`** + final document accessible
- [ ] Reproducible E2E/fixture path exists
- [ ] P1→P2→P3 trace with no state jumps or inconsistent messages
- [ ] Unit tests: interrupt/resume, arbitration limit, arbitration on conflict

---

## Explicit non-goals (Part 3)

- Merging RFP into Support Agent graph
- Support Agent memory propose/confirm (context-26)
- LLM arbitration or LLM final document merge
- Celery / second HTTP service
- Department RBAC
- **`done`** as status code
- Full **`markdown_text`** in default GET detail
- Mandatory RAG / Qdrant

---

## Phase plan (implement in order)

### Phase 0 — Schema

1. Add **`final_document_markdown`**, **`final_document_generated_at`** to **`rfp_tickets`**; extend schemas/API.
2. Add P3 status constants (**`awaiting_department_approval`**, etc.) and **`approval_status`** enum helpers.
3. **Gate:** migration applies; GET returns new fields.

### Phase 1 — Pipeline helpers

1. **`rfp_arbitration.py`**, **`rfp_final_document.py`**, **`_trace_p3()`**.
2. **Gate:** unit tests for arbitration rules + merge template pass.

### Phase 2 — Graph

1. **`rfp_approval_graph.py`** — merge with compiled graph; **`invoke_mode=approval`** router.
2. **`invoke_rfp_approval`**, **`resume_rfp_approval`** in **`rfp_intake_graph.py`**.
3. Hook P2 finalize → auto-start approval background task.
4. **Gate:** fixture ticket reaches dept interrupts in test DB.

### Phase 3 — API + service

1. Decision + regenerate + CEO + final-document routes; **`approval_service.py`**.
2. **Gate:** API tests for 200/400/409 paths.

### Phase 4 — Backoffice

1. Approval actions per section; CEO panel; final doc download; polling extensions.
2. **Gate:** manual walkthrough on seed #1 after P2.

### Phase 5 — E2E + regression

1. **`test_rfp_e2e.py`**, **`scripts/rfp_e2e_smoke.py`**; P1 + P2 green.
2. **Gate:** evaluation checklist above all checked.

---

## Verification commands

```bash
# Part 1 + Part 2 regression (must stay green)
cd services/api && uv run python -m pytest \
  tests/pipelines/test_rfp_intake.py \
  tests/pipelines/test_rfp_classifier_worker.py \
  tests/pipelines/test_rfp_generation.py \
  tests/pipelines/test_rfp_evaluator.py \
  tests/test_rfp_api.py \
  tests/test_rfp_models.py -q

# Part 3 unit + E2E (after implementation)
cd services/api && uv run python -m pytest \
  tests/pipelines/test_rfp_approval.py \
  tests/pipelines/test_rfp_arbitration.py \
  tests/pipelines/test_rfp_final_document.py \
  tests/pipelines/test_rfp_e2e.py -q

# CLI E2E smoke (after implementation)
cd services/api && uv run python ../../scripts/rfp_e2e_smoke.py --seed 2
cd services/api && uv run python ../../scripts/rfp_e2e_smoke.py --seed 1
```

---

## Part 1 & Part 2 companions

- Shared spec + Part 1: [context-27-milestone-9-rfp-intake-routing-p1.md](./context-27-milestone-9-rfp-intake-routing-p1.md)  
- Generation + evaluation: [context-27-milestone-9-rfp-response-generation-p2.md](./context-27-milestone-9-rfp-response-generation-p2.md)

**Gate:** Part 2 acceptance complete before Part 3 implementation.

---

_Internal document — Brasaland · Context 27 Part 3 · Milestone 9 RFP approval & document completion_
