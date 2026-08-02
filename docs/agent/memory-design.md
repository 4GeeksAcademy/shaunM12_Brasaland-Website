# Agent Memory — Design Document (MEM-092)

**Authority:** [context-26-milestone-8-agent-memory.md](../memory-bank/historical-reference/context-26-milestone-8-agent-memory.md)  
**Status:** P26-0–P26-6 complete — MEM-092 merge-ready  
**Evidence companion:** `docs/agent/memory-evidence.md` (P26-6)

---

## 1. Problem

Location managers repeat the same operational corrections (supplier days, hours exceptions, known incident patterns). The Support Agent treats each question as new. MEM-092 adds **user-approved persistent memory** with audit — not RAG reindex, not chat log, not system-prompt stuffing.

---

## 2. Architecture choice (P26-L1)

| Choice | Decision |
| ------ | -------- |
| **Backend** | Postgres (`agent_memory_entries`, `agent_memory_audit_log`) |
| **Session pending** | LangGraph SQLite checkpoint (`pending_proposal` only) |
| **Interface** | `read_memory()`, `write_memory()`, `log_proposal()` in `agent/memory/store.py` |

### Ruled out

| Option | Why rejected |
| ------ | ------------ |
| **Qdrant / vector** | Already serves KB (context-21); corrections are sparse keyed facts, not semantic search |
| **Knowledge graph** | Flat location → category → fact; no relationship traversal need |
| **Fine-tuning** | No selective forget; no per-write audit |
| **Prompt stuffing** | Unbounded; no authorization trail |
| **Postgres checkpointer** | P26-L1c — SQLite checkpoint unchanged |

---

## 3. Data model

### `agent_memory_entries`

| Field | Notes |
| ----- | ----- |
| `location_id` | 1–14 for global categories; NULL for user `preferences` |
| `user_id` | NULL for global; set for `preferences` |
| `category` | `hours` \| `suppliers` \| `known_incidents` \| `preferences` |
| `key` | snake_case allowlist per category |
| `value` | English-normalized text (P26-L15) |
| `source` | `user_confirmed` |
| `approved_by` | JWT user id |
| `approved_at` | UTC timestamp |
| `expires_at` | Category TTL (P26-L3e) |

**Uniqueness:** upsert on global `(location_id, category, key)` or preferences `(user_id, category, key)`.

### `agent_memory_audit_log`

Append-only: `proposal_json`, `outcome`, `reason`, `user_id`, optional `thread_id`, `user_message`, `superseded_value`.

---

## 4. Denylist (P26-L2)

Never store: PII/CRM, payroll, one-off noise, live metrics, KB-canonical policy, guardrail-blocked text, instruction overrides, allergen "zero risk", secrets.

Enforced at **proposal validation** and **`write_memory()`**.

---

## 5. Lifecycle (P26-L3)

- Upsert replaces same key; max **12 entries per location**
- TTL: hours/suppliers/preferences **365d**; known_incidents **180d**
- Pending: ambiguous → reject; **24h** idle → `expired_no_response`; one pending at a time

---

## 6. Poisoning (P26-L4)

Guardrails first → propose only → rule classifier approve/reject/edit → denylist at write → trusted read block (RAG wins on policy).

---

## 7. Scope (P26-L7)

- **Global:** hours, suppliers, known_incidents (per location)
- **Per-user:** preferences
- **Injection cap:** 8 rows per generation turn

---

## 8. Examples — memorable vs not (MEM-092 grading)

### Should propose (≥3)

| # | User context | Proposed key | Why memorable |
| - | ------------ | ------------ | ------------- |
| 1 | Medellín supplier delivers **Wednesdays**, not Tuesdays | `suppliers.meat_delivery_day` @ location 3 | Recurring delivery correction |
| 2 | Miami Beach closes **11pm weekends** (changed last month) | `hours.weekend_close` @ location 8 | Stable hours exception |
| 3 | Location 7 zero-sales = **power outage pattern**, not POS error | `known_incidents.zero_sales_pattern` @ location 7 | Repeat escalation context |
| 4 | Chapinero closes late on **Fridays only** | `hours.friday_close` @ location 4 | Location-specific hours |

### Should NOT propose (≥3)

| # | User message | Why skip |
| - | ------------ | -------- |
| 1 | Yesterday's average ticket in Bogotá | Live telemetry — not durable |
| 2 | Thanks, that answers my question | Conversation closing |
| 3 | Translate this for Ashley's report | One-off task / preferences without approval pattern |
| 4 | How many points for Gold tier? | KB-canonical policy — use RAG reindex, not memory |
| 5 | Current stock for beef at Chapinero | Live inventory API data |

Proposal is communicated in the **same** `answer` string (P26-L8d); user confirms on a **later** message in the same `thread_id`.

---

## 9. Design questions (Q1–Q5)

| Q | Question | Answer (see sections) |
| - | -------- | ------------------- |
| **Q1** | What persistent backend and interface? | Postgres episodic + audit; explicit `read_memory` / `write_memory` / `log_proposal` — §2 |
| **Q2** | What must never enter memory? | Denylist + category allowlist — §4 |
| **Q3** | How do we forget / consolidate? | Upsert, 12/location cap, category TTLs, pending expiry — §5, §14 |
| **Q4** | How do we prevent poisoning? | Guardrails → propose → classify → denylist → trusted read framing → rate limit — §6, §13 |
| **Q5** | Why not multi-agent? | Same graph + structured field + rule classifier — §2 ruled-out + context-26 decision 5 |

---

## 10. Supersession summary

See context-26 **Supersession rationale** — Support Agent evolves P1/P2/P25; Knowledge API unchanged.

---

## 11. Implementation phases

| Phase | Status |
| ----- | ------ |
| P26-0 | ✅ context-26 + this scaffold |
| P26-1 | ✅ SQLModel + store + denylist/keys + unit tests |
| P26-2 | ✅ Structured generation + JSON parse/validate + mock LLM tests |
| P26-3 | ✅ Graph nodes + checkpoint pending + thread_id API/UI + two-turn tests |
| P26-4 | ✅ Classifier polish + proposed/rejected audit + rate limit |
| P26-5 | ✅ Read injection polish + consolidation (TTL/cap/purge) |
| P26-6 | ✅ Evidence doc + merge-gate regression tests |

---

## 12. Structured generation (P26-L8, P26-2)

Support Agent generation returns one JSON object per LLM call:

```json
{"answer": "...", "memory_proposal": null | { "location_id", "category", "key", "value", "reason" }}
```

| Module | Role |
| ------ | ---- |
| `agent/generation.py` | `generate_structured_support_response()`, `generate_structured_rag_response()` — **Support only**; Knowledge `generate_answer()` unchanged |
| `agent/memory/structured_generation.py` | Parse JSON, coerce failures (P26-L8c), suppress proposal when pending (P26-L8e) |
| `agent/guardrails/prompts.py` | `support_system_prompt_with_memory()`, trusted memory block in user prompt (P26-L4f) |

Graph wiring is **P26-3** — `resolve_memory_proposal`, `read_memory`, and `memory_ack` nodes are live in `agent/graph.py`.

---

## 13. Graph integration (P26-L10, P26-3)

```text
guard_input → resolve_memory_proposal → read_memory → classify → … → generate → validate_output
approve-only: resolve_memory_proposal → memory_ack → END
```

| Node | Role |
| ---- | ---- |
| `resolve_memory_proposal_node` | Classify pending reply; write on approve/edit; may rewrite `question` (P26-L14) |
| `read_memory_node` | `read_memory()` + `format_memory_context()` using location hint + user preferences |
| `memory_ack_node` | Terminal ack template after approve-only |
| `validate_output_node` | Promotes `memory_proposal_candidate` → checkpointed `pending_proposal` |

**Client continuity:** optional `thread_id` on `POST /agent/query`; UI stores UUID in `sessionStorage` (`brasaland_support_thread_id`).

---

## 14. Proposal classifier, audit, rate limit (P26-L9, P26-L4h, P26-4)

| Module | Role |
| ------ | ---- |
| `agent/memory/proposal.py` | Rule-first `classify_memory_decision()` — reject → edit → approve → ambiguous |
| `agent/memory/patterns_proposal.py` | English + basic Spanish assent/reject/edit patterns |
| `agent/memory/store.py` | `check_proposal_rate_limit()`, `count_recent_proposed()`, audit via `log_proposal()` |

**Audit outcomes (append-only):** `proposed`, `approved`, `approved_edited`, `rejected`, `rejected_ambiguous`, `rejected_rate_limit`, `rejected_denylist`, `rejected_cap_exceeded`, `expired_no_response`.

**Rate limit:** max `AGENT_MEMORY_PROPOSAL_RATE_LIMIT` (default 3) `proposed` rows per user per `AGENT_MEMORY_PROPOSAL_RATE_WINDOW_HOURS` (default 24). Enforced in `validate_output_node` before checkpointing pending.

---

## 15. Read injection and consolidation (P26-L3, P26-L12, P26-5)

| Module | Role |
| ------ | ---- |
| `agent/memory/location_hint.py` | `resolve_injection_location_id()` — city/alias, inventory hints, pending proposal |
| `agent/memory/store.py` | Priority read (location globals → preferences), expired exclusion, cap counts active rows only |
| `agent/memory/store.py` | `purge_stale_entries()` — optional delete of rows expired >30 days (P26-L3g stretch) |

**Injection priority (max 8 rows):** non-expired global facts for resolved `location_id` first; remaining slots filled with the user's `preferences`.

**Consolidation rules enforced:**
- Upsert same `(location_id, category, key)` or preference key — TTL reset on re-approve (P26-L3e)
- Cap per location counts **non-expired** rows only (P26-L3d)
- Expired rows excluded from `read_memory()` (P26-L3f)

---

## 16. Merge gate checklist (P26-6)

| Item | Status |
| ---- | ------ |
| All `P26-L*` locks implemented | ✅ Phases P26-0…P26-6 |
| `memory-design.md` Q1–Q5 + ruled-out architectures | ✅ §2, §9 |
| `memory-evidence.md` approved + rejected cycles | ✅ Cycles A–D |
| Graph: `resolve_memory_proposal`, `read_memory`, `memory_ack` | ✅ `test_agent_memory_regression.py` |
| Optional `thread_id` API + UI `sessionStorage` | ✅ P26-3 |
| `AgentQueryResponse` = `{ answer }` only | ✅ regression test |
| `/knowledge/query` + `generate_answer()` unchanged | ✅ regression test |
| Guardrails + agent evals green | ✅ full pytest gate below |
| `.env.example` memory vars | ✅ `AGENT_MEMORY_*` |

**Regression command:**

```bash
cd services/api && uv run pytest \
  tests/pipelines/test_agent_memory_regression.py \
  tests/pipelines/test_agent_memory*.py \
  tests/pipelines/test_support_agent_graph.py \
  tests/pipelines/test_support_agent_routing.py \
  tests/pipelines/test_agent_guardrails_regression.py \
  tests/test_agent_api.py -q
```

---
