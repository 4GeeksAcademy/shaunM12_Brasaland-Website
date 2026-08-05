# Agent Memory — Evidence (MEM-092)

**Authority:** [context-26-milestone-8-agent-memory.md](../memory-bank/historical-reference/context-26-milestone-8-agent-memory.md)  
**Design:** [memory-design.md](./memory-design.md)  
**Status:** P26-6 — automated + documented evidence cycles

This document records **complete propose → classify → outcome** cycles. Automated proof lives in the cited pytest modules; steps below match what those tests exercise.

---

## Cycle A — Approved (persisted + injected later)

**Scenario:** Medellín Envigado meat supplier delivers on **Wednesdays**, not Tuesdays. Manager confirms; fact appears on a later question at the same location.

### Turn 1 — Propose

| Field | Value |
| ----- | ----- |
| **User question** | `Medellín meat supplier delivers Wednesdays not Tuesdays` |
| **thread_id** | Client-minted UUID (same session) |
| **LLM JSON** | `{ "answer": "...Want me to remember that?", "memory_proposal": { "location_id": 3, "category": "suppliers", "key": "meat_delivery_day", "value": "Meat supplier delivers on Wednesdays" } }` |

**Graph trace (suffix):**

```text
intake → guard_input → resolve_memory_proposal (noop) → read_memory → classify → retrieve → generate → validate_output
```

**Outcomes:**

- Checkpoint: `pending_proposal` set
- Audit: `proposed` row appended
- HTTP response: `{ "answer": "..." }` only (no memory metadata)

**Automated proof:** `tests/pipelines/test_agent_memory_graph.py::test_pending_proposal_survives_thread_across_invokes`

### Turn 2 — Approve only

| Field | Value |
| ----- | ----- |
| **User message** | `Yes, remember that` |
| **Classifier** | `approve` (memory intent; not bare assent) |

**Graph trace (suffix):**

```text
intake → guard_input → resolve_memory_proposal (approve) → memory_ack → END
```

**Outcomes:**

- `agent_memory_entries`: upsert `(location_id=3, category=suppliers, key=meat_delivery_day)`
- Audit: `approved` with optional `superseded_value` on re-approve
- Answer: `Got it — I'll remember that for next time.`
- `pending_proposal` cleared

**Automated proof:** `tests/pipelines/test_agent_memory_graph.py::test_memory_ack_template_on_approve_only`

### Turn 3 — Injection on later question

| Field | Value |
| ----- | ----- |
| **User question** | `When does the meat supplier deliver at Chapinero?` (or Envigado alias) |
| **read_memory** | Resolves location hint → loads approved row |
| **Generation** | `memory_context` passed to `generate_structured_rag_response` |

**Automated proof:** `tests/pipelines/test_agent_memory_consolidation.py::test_graph_injects_memory_context_into_structured_generation`

---

## Cycle B — Rejected (ambiguous assent; store unchanged)

**Scenario:** Agent proposes a supplier correction; user replies with bare `"yes"` — **not** sufficient memory intent (P26-L9b).

### Turn 1 — Propose

Same as Cycle A turn 1 (`proposed` audit + checkpoint pending).

### Turn 2 — Ambiguous reject

| Field | Value |
| ----- | ----- |
| **User message** | `yes` |
| **Classifier** | `ambiguous` / reason `bare_assent` |

**Graph trace (suffix):**

```text
intake → guard_input → resolve_memory_proposal (rejected_ambiguous) → read_memory → classify → …
```

**Outcomes:**

- Audit: `rejected_ambiguous`
- **No** row in `agent_memory_entries`
- `pending_proposal` cleared
- Graph continues on original message for normal routing (may refuse/fallback if `"yes"` is not ops-shaped)

**Automated proof:** `tests/pipelines/test_agent_memory_proposal.py::test_bare_yes_is_ambiguous`  
**Graph classifier path:** `tests/pipelines/test_agent_memory_graph.py` (pending cleared after non-approve reply)

---

## Cycle C — Rejected (topic change while pending)

**Scenario:** User ignores pending memory and asks a live ops question instead.

| Field | Value |
| ----- | ----- |
| **Pending** | Supplier delivery proposal from turn 1 |
| **User message** | `List open incidents at Miami Doral` |
| **Classifier** | `ambiguous` / reason `topic_change` |

**Outcomes:**

- Audit: `rejected_ambiguous` (reason `topic_change`)
- No memory write
- Full user message proceeds to `classify` → incident path

**Automated proof:** `tests/pipelines/test_agent_memory_proposal.py::test_topic_change_while_pending_is_ambiguous`

---

## Cycle D — Rejected (denylist at write gate)

**Scenario:** User explicitly approves, but edited value contains payroll — blocked at `write_memory()`.

| Field | Value |
| ----- | ----- |
| **Proposal value** | Contains payroll pattern |
| **Outcome** | `rejected_denylist` |

**Automated proof:** `tests/pipelines/test_agent_memory.py::test_write_memory_rejects_denylist`

---

## Regression gate (P26-6)

Full Support Agent + memory suite:

```bash
cd services/api && uv run pytest \
  tests/pipelines/test_agent_memory_regression.py \
  tests/pipelines/test_agent_memory.py \
  tests/pipelines/test_agent_memory_generation.py \
  tests/pipelines/test_agent_memory_graph.py \
  tests/pipelines/test_agent_memory_proposal.py \
  tests/pipelines/test_agent_memory_rate_limit.py \
  tests/pipelines/test_agent_memory_consolidation.py \
  tests/pipelines/test_support_agent_graph.py \
  tests/pipelines/test_support_agent_routing.py \
  tests/pipelines/test_agent_guardrails_regression.py \
  tests/test_agent_api.py \
  -q
```

**Merge gate checklist:** see [memory-design.md §16](./memory-design.md#16-merge-gate-checklist-p26-6).

---

## Boundaries verified

| Lock | Evidence |
| ---- | -------- |
| P26-L23 Knowledge API unchanged | `test_agent_memory_regression.py::test_knowledge_generate_answer_signature_unchanged` |
| P1-L8 response shape | `test_agent_memory_regression.py::test_agent_query_response_is_answer_only` |
| P26-L10 trace order | `test_agent_memory_regression.py::test_support_agent_trace_includes_memory_nodes` |
| P26-L21 env vars | Documented in repo root `.env.example` |
