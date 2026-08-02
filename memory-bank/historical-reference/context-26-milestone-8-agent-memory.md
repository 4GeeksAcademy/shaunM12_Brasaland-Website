# Context 26 — Agent Memory and Self-Improvement · Brasaland

**Ticket:** MEM-092 — Agent learns from interaction without uncontrolled writes  
**Type:** Persistent memory backend + explicit read/write interface + self-evaluation + user-confirmed proposals + auditable log + consolidation  
**Branch:** `mem-092-agent-memory` (suggested)  
**Status:** ✅ P26-0–P26-6 complete — MEM-092 merge-ready  
**Depends on:** [context-21-rag-knowledge-base.md](./context-21-rag-knowledge-base.md), [context-23-support-agent-langgraph-p1.md](./context-23-support-agent-langgraph-p1.md), [context-23-support-agent-langgraph-p2.md](./context-23-support-agent-langgraph-p2.md), [context-24-mcp-company-tools.md](./context-24-mcp-company-tools.md), [context-25-securing-agents-harness-guardrails.md](./context-25-securing-agents-harness-guardrails.md), [context-22-route-conventions.md](./context-22-route-conventions.md)  
**Stakeholders:** Nicolás Park (tech lead); Felipe Guerrero (Operations Director); location managers; Brasaland Digital / backoffice support users  
**Companion:** `docs/agent/memory-design.md`, `docs/agent/memory-evidence.md`

> **Reproduction:** This file is the single source of truth for MEM-092. Implement phases P26-0…P26-6 in order on one branch; merge only when the [acceptance checklist](#acceptance-checklist) is complete. Do not reopen locked decisions without updating this file.

---

## Ticket brief (MEM-092)

From: Tech Lead — Ticket #MEM-092

The agent already knows the company (RAG), calls tools through the MCP Server, and stays inside its guardrail. But every conversation starts from zero: it doesn't remember that we resolved a similar escalation yesterday, or that someone already corrected a piece of data last week. I need the agent to learn from interaction, without that meaning it starts making things up or piling junk into its memory forever.

You don't need a new graph or a multi-agent architecture for this — it's the same agent as always, with one extra self-evaluation step:

1. When the agent detects, within its own response, something worth remembering, it **proposes** it to the user in the same conversation ("want me to remember this for next time?") instead of writing straight to memory.
2. That decision — yes, no, or an edit — can't be a fuzzy interpretation of the next message. It must be **explicitly classified** against the pending proposal and **logged**: what was proposed, what the user decided, and when. If the decision can't be determined with reasonable confidence, the proposal is **discarded by default** — approval is never assumed from silence or ambiguity.
3. Only what's approved and logged gets consolidated into the persistent store; what's rejected is discarded, but the record that it was proposed and rejected stays.

I won't accept a memory that grows without limit, that self-edits without the user knowing, or a memory write with no trace of who authorized it.

### What to deliver (from ticket)

| Area | Requirement |
| ---- | ----------- |
| **Memory architecture** | Choose persistent backend; document why; explicit read/write interface — not system-prompt accumulation |
| **Self-evaluation** | Structured output: user `answer` + optional `memory_proposal`; explicit criteria; ≥3 non-proposal examples documented |
| **User confirmation** | Classify approve/reject/edit; one pending at a time; silence/ambiguity → reject; auditable log |
| **Consolidation** | Bounded growth; documented cleanup/expiration policy |
| **Evidence** | ≥2 complete cycles: one approved (reflected later), one rejected (unchanged) |

---

## Reference material (do not duplicate in code or prompts)

| Material | Use in this project |
| -------- | ------------------- |
| Course complementary note on memory architectures (episodic / vector / graph / fine-tuning) | **Background only — excluded** from this file's runtime copy and from prompts |
| Generic "why guardrails before memory" sprint narrative | **Background only — excluded**; dependency captured via prerequisite gate on context-25 |

---

## Why this memory matters for Brasaland

Your agent already knows Brasaland's 14 locations (Colombia and Florida), queries the Incidents Manager and inventory through the MCP Server, and stays inside its guardrail. The problem Felipe Guerrero (Operations Director) reports: the same location managers repeat the same corrections week after week — "the Medellín meat supplier delivers on Tuesdays, not Mondays," "the Miami location closes at 10pm on Fridays, not 9pm" — and the agent keeps treating them as brand-new questions every time.

---

## What IS worth remembering

- **Recurring operational corrections per location**: real opening/closing hours, specific supplier delivery days, local exceptions to a standard procedure.
- **Context from a resolved escalation**: if a "no sales in 2 hours" alert at a location turned out to be a known issue (e.g., a scheduled power outage in that area), it's worth remembering so it isn't re-escalated.
- **A location manager's communication preferences**: if Carlos Jiménez (senior supervisor) always wants reports in a specific format, that's memorable.

---

## What must NEVER enter memory

- Brasa Points customer personal data beyond what's strictly operational (that doesn't need agent memory — it lives in the CRM).
- Payroll figures or individual staff compensation across the 14 locations.
- Anything that only applies to a one-off conversation with no repeatable pattern (a single customer complaint on a single day isn't memorable).

**Cross-reference (context-21 / context-25 — also non-negotiable via P26-L2):**

- Official KB policy facts belong in RAG corpus reindex, **not** agent memory.
- Never store wording that implies **"zero risk"** on allergens.
- Never store instruction-override payloads or untrusted RAG/tool text as durable memory.
- Operational telemetry snapshots (yesterday's average ticket, live stock counts) belong in telemetry/inventory APIs — **not** agent memory.

---

## Self-evaluation examples (proposal vs no proposal)

### Should generate a memory proposal

1. "Actually the vegetable supplier in Zaragoza... wait, I mean Medellín, delivers on Wednesdays, not Tuesdays like you said before."
2. "The Miami Beach location now closes at 11pm on weekends, that changed last month."
3. "That zero-sales alert at location 7 was because of a power outage, not a POS error — it's happened twice this month already."

### Should NOT generate a proposal

1. "What was yesterday's average ticket in Bogotá?" (one-off query; data lives in the telemetry pipeline).
2. "Thanks, that answers my question." (conversation closing; nothing new to remember).
3. "Can you translate this into English for Ashley's report?" (single-use task; no lasting value).

Implementation must document **≥3 examples of each type** in `docs/agent/memory-design.md` (these three are minimum seeds).

---

## Company constraints

- Brasaland operates across two currencies (COP/USD) and two languages.
- If the agent supports bilingual operation, the memory proposal and user confirmation must work in the chosen base language — don't assume the user will always correct it in Spanish.
- Location identifiers align with `packages/shared/restaurant_locations.py` (ids 1–14) when a memory entry is location-scoped.

---

## Prerequisite gate

- [ ] Context-25 SEC-114 merged — guardrails live on `/agent/query` (`guard_input`, sanitization, output validation)
- [ ] Context-23 P1 + P2 merged — LangGraph, classifier, MCP incidents, inventory reads
- [ ] Context-24 P24-4 merged — incidents via MCP; inventory direct HTTP unchanged
- [ ] Context-21 RAG indexed — Qdrant corpus for policy answers (memory ≠ RAG)
- [ ] Existing agent evals green: `test_support_agent_graph.py`, `test_support_agent_routing.py`, `test_agent_api.py`, guardrails suite

---

## Authority / supersession

| Source | Rule | context-26 |
| ------ | ---- | ---------- |
| context-23 **P1-L8** | Response `{ "answer" }` only | **Unchanged** |
| context-23 **P1-L4**, P2 core #7 | Request `{ "question" }` | **Extended** — optional `thread_id` on request (P26-L16) |
| context-23 P1 **non-goals** | No multi-turn / `thread_id` in HTTP | **Superseded** — optional **request-only** `thread_id` for pending proposals (not chat history) |
| context-23 P2 | HTTP excludes `thread_id` | **Superseded** for optional request field; still excluded from **response** |
| context-25 **P25-L2** | `guard_input` → `classify` | **Superseded prefix** — memory nodes after guard (P26-L10) |
| context-23 **P2-L22** | `classify` must not mutate `question` | **Scoped** — only `resolve_memory_proposal` may rewrite `question` (P26-L14) |
| context-21 signatures | `generate_answer() -> str` | **Unchanged** for Knowledge API; Support uses agent wrapper (P26-L8) |
| context-21 golden rule | RAG ≠ conversational memory | **Unchanged** for KB; agent memory is separate Postgres store (P26-L23) |
| context-24 **P24-L20** | Read routing after `classify` | **Unchanged** — only pre-`classify` prefix added |
| context-25 **P25-L8** | RAG/tool = untrusted framing | **Unchanged**; memory = separate **trusted** block post-approval (P26-L4f) |
| context-21 faithfulness KPI | Numeric data from chunks only | Applies to **`test_rag.py` / Knowledge**; Support uses labeled approved memory (P26-L4f) |

---

## Conflict & drift register (resolved — do not reopen)

| # | Risk | Lock |
| - | ---- | ---- |
| 1 | P1 "no thread_id" read as no session | P26-L16 request-only; client-minted UUID |
| 2 | P2-L22 vs question rewrite | P26-L14 scoped to `resolve_memory_proposal` only |
| 3 | Breaking `generate_answer()` / Knowledge API | P26-L8 wrapper in `agent/generation.py`; P26-L23 |
| 4 | Guardrails bypass | P26-L10 order + P26-L4a |
| 5 | Untrusted memory in prompt | P26-L4f trusted label + approve gate |
| 6 | Trace/eval churn | P26-L10e; P26-6 updates graph tests |
| 7 | Policy overridden by memory | P26-L4f — RAG wins on KB policy conflicts |
| 8 | Knowledge API gets memory | P26-L23 |
| 9 | Mock tests patch wrong generate hook | Patch `agent/generation` wrapper, not Knowledge `query()` |
| 10 | Postgres confused with Postgres checkpointer | P26-L1c — SQLite checkpoint unchanged |

---

## Supersession rationale (why prior contexts appear to conflict)

Prior milestones (P1 stateless agent, P2 classify purity, P25 guardrails) did not include MEM-092. Entries in [Authority / supersession](#authority--supersession) are **intentional evolutions**, not corrections of mistakes in earlier context files. Do not revert P26 locks to satisfy a literal reading of an older rule when this section and the Authority table scope the override.

### What must stay in effect (unchanged)

| Prior rule | Why it stays |
| ---------- | ------------ |
| context-23 **P1-L8** — `{ "answer" }` only | API stability, privacy, course alignment |
| context-25 guardrails-first | Memory sprint depends on SEC-114; P26-L4a reinforces rather than replaces |
| context-23 **P2-L22** inside `classify.py` | Classifier stays deterministic and testable |
| context-21 **`/knowledge/query`** and `generate_answer() -> str` | Separate Knowledge product (P26-L23) |
| context-24 routing **after** `classify` | Intent/tool paths unchanged; only a pre-`classify` prefix added |
| context-23 P1 minimal state — no `messages[]` chat history | Still true; P26 adds pending proposal only, not a chat log |
| context-23 **P1-L9** SQLite checkpointer | Still the session/thread store (P26-L1c); Postgres is for memory **tables**, not checkpointer |

### Why each supersession exists — and why it must stay for MEM-092

**`thread_id` on request (supersedes P1 non-goals / P2 HTTP exclusion)**

P1 excluded a multi-turn **chat product** and `thread_id` in HTTP (meaning no session metadata in responses). MEM-092 requires propose → user's **next message** → classify. That needs a stable LangGraph checkpoint thread. P26-L16 adds optional **request-only** `thread_id` (client-minted); response remains `{ "answer" }` only. Reverting this breaks pending proposals. This is **not** full chat history — no `messages[]` in state.

**Pre-`classify` memory nodes (supersedes context-25 P25-L2 prefix)**

SEC-114 locked `guard_input → classify` before memory existed. MEM-092 inserts `resolve_memory_proposal → read_memory` **after** guardrails and **before** classify (P26-L10) — the same evolution class as context-25 inserting `guard_input` before `classify`. Routing **after** `classify` is unchanged (context-24 P24-L20). Reverting order either bypasses guardrails or fails memory resolution.

**Question rewrite (scoped override of P2-L22)**

P2-L22 forbids the **`classify` node** from mutating `question` so routing tests stay pure. MEM-092 requires "Yes, remember that — list open incidents" in **one invoke**: close memory first, then classify the ops remainder. Only **`resolve_memory_proposal`** may replace `state["question"]` with `continued_question` (P26-L14) — analogous to **`intake`** trimming whitespace. P2-L22 **still applies to `classify.py`**.

**Structured generation wrapper (scoped override of P1 generate-node wording)**

P1 locked the graph to call `generate_answer()` from `rag.py` returning a plain string. context-21 keeps that contract for Knowledge. P2 already set precedent with **`generate_support_answer()`** without breaking Knowledge (P2-L35). P26-L8 adds a Support-only wrapper in `agent/generation.py` that parses JSON `{ answer, memory_proposal }` server-side; **`/knowledge/query` and `generate_answer()` signatures unchanged** (P26-L23). Reverting forces a choice: fail MEM-092 self-evaluation or break Knowledge API.

**Trusted memory block vs P25-L8 untrusted RAG/tool framing**

context-25 labels RAG and MCP payloads **untrusted** so injection cannot become system rules. Approved memory is **intentionally influential** — but only after user confirm + audit. P26-L4f adds a **fourth prompt section** labeled user-confirmed operational memory; RAG/tool framing **unchanged**. P26-L4f also requires **RAG to win on KB policy conflicts** so memory cannot override allergen/loyalty manuals. Removing trusted framing makes memory useless; merging it with untrusted content removes the approve gate.

**Agent memory vs context-21 "RAG is not conversational memory"**

context-21 excludes using Qdrant or chat as memory for the **Knowledge product**. MEM-092 adds a **separate Postgres store** for ops corrections — not Qdrant, not chat log (P26-L1, P26-L23). The context-21 golden rule **remains in effect for `/knowledge/query`**. Merging agent memory into RAG would violate both context-21 and P26-L1.

**Faithfulness KPI (context-21 §4) vs Support memory injection**

context-21 faithfulness applies to **Knowledge evals** (`test_rag.py`): no numeric data absent from retrieved chunks. The Support Agent already uses **live tools** (context-23 P2) — not chunk-only answers. Approved memory is a **labeled, user-confirmed** source with explicit conflict rules (P26-L4f). Faithfulness KPI scope **unchanged for Knowledge**; Support behavior documented in `docs/agent/memory-design.md`.

**Postgres memory tables vs P1 "Postgres checkpointer" non-goal**

P1 non-goal **"Postgres checkpointer"** means LangGraph must not move off SQLite for checkpointing. P26-L1 uses Postgres for **`agent_memory_entries` / audit only**; **`AGENT_CHECKPOINT_DB_PATH` SQLite unchanged** (P26-L1c, register #10). No conflict when scoped correctly.

### Precedent: how earlier milestones already superseded prior rules

| Evolution | Prior rule | How it was handled |
| --------- | ---------- | ------------------- |
| LangGraph (context-23 P1) | context-21 S1 no agent frameworks | **Superseded for `/agent` orchestration only** |
| `guard_input` before `classify` (context-25) | P2 graph started at `classify` | **Prefix nodes**; routing after classify unchanged |
| `generate_support_answer` (context-23 P2) | P1 `generate_answer` only in graph | **Second generator**; Knowledge path unchanged |

MEM-092 follows the same pattern: **extend Support Agent; leave Knowledge API and classify routing intact.**

---

## Scope

### In scope

| Area | Target |
| ---- | ------ |
| **Agent** | Support Agent — `POST /agent/query`, LangGraph in `services/api/agent/` |
| **Memory store** | Postgres structured episodic + audit log (P26-L1) |
| **Self-evaluation** | JSON `{ answer, memory_proposal }` single LLM call (P26-L8) |
| **User confirmation** | Rule-first classifier (P26-L9) |
| **Consolidation** | Upsert, cap, TTL (P26-L3) |
| **Evidence** | `docs/agent/memory-evidence.md` — approved + rejected cycles |
| **Design doc** | `docs/agent/memory-design.md` |

### Out of scope

- Multi-agent architecture (P26-L5)
- Writing to RAG / Qdrant from conversation (use reindex)
- Memory on `/knowledge/query` (P26-L23)
- Returning memory metadata in HTTP response (P1-L8)
- Backoffice memory admin UI (v1)
- Fine-tuning / parametric memory
- Per-location write ACL (P26-L7f — future hardening)
- LLM approval arbiter (P26-L9e)

---

## Current baseline (gap analysis)

| Concern | Today | Gap |
| ------- | ----- | --- |
| Persistent memory | None | No durable store for location corrections |
| Conversation continuity | New `thread_id` per invoke unless passed | UI/API don't send `thread_id` |
| Self-evaluation | Plain string generation | No `memory_proposal` |
| User confirmation | Incident `confirm_write` only | No general memory approve flow |
| Audit trail | Guardrail in-process logs | No durable proposal/decision log |
| Consolidation | N/A | Unbounded growth risk |

---

## Design decisions — locked with rationale

Workshop closed **2026-08-01**. Maps to course design questions and `P26-L*` locks.

### 1. Memory architecture

**Decision:** Postgres structured episodic store (`agent_memory_entries` + `agent_memory_audit_log`); explicit `read_memory()` / `write_memory()` / `log_proposal()`. SQLite checkpoint = session/pending only.

**Ruled out:** Qdrant (RAG), knowledge graphs, fine-tuning, prompt-stuffing.

**Why:** Felipe's repeat-correction problem is sparse location-scoped facts with per-write audit — not semantic search. Postgres upsert/TTL/cap on the existing stack. Qdrant stays KB-only.

### 2. What must never enter memory

**Decision:** Denylist in `agent/memory/denylist.py`; category allowlist only: `hours` | `suppliers` | `known_incidents` | `preferences`. Dual enforcement at proposal and write gates.

**Why:** Memory is repeatable ops exceptions — not CRM, HR, telemetry, or official manuals. Category allowlist keeps consolidation predictable.

### 3. Forgetting, consolidation, pending expiry

**Decision:** Upsert on `(location_id, category, key)`; max 12 entries/location; category TTLs; pending ambiguous → reject; 24h idle → `expired_no_response`; one pending at a time.

**Why:** Without consolidation, 14 locations × weekly corrections becomes junk. Silence ≠ consent per MEM-092.

### 4. Poisoning prevention

**Decision:** Defense in depth — guardrails first, propose-only, rule classifier, denylist at write, trusted read framing, rate limit 3 proposals/user/24h.

**Why:** Guardrails protect one conversation; memory makes mistakes cumulative. Visible proposal + classified approve + JWT audit closes false-correction paths.

### 5. Why not multi-agent

**Decision:** Same graph; structured `memory_proposal` field; `resolve_memory_proposal` node; deterministic consolidation code.

**Why:** Self-evaluation is structured output, not a second agent. Approval is classification against a fixed pending object — same pattern as `evaluate_input_guard()`.

### 6. Conversation continuity

**Decision:** Optional `thread_id` on request; client-minted UUID in `sessionStorage`; pending in checkpoint only; response `{ "answer" }` only.

**Why:** MEM-092 requires propose → next message → classify. Checkpoint exists; minimal API change.

### 7. Memory scope

**Decision:** Hybrid — global ops facts per `location_id`; `preferences` per `user_id`; max 8 rows injected per turn.

**Why:** Different managers must share location corrections; communication prefs stay personal.

### 8–16. Implementation locks (summary)

| # | Decision | Lock |
| - | -------- | ---- |
| 8 | Structured JSON generation | P26-L8 |
| 9 | Rule-first proposal classifier | P26-L9 |
| 10 | Graph node order | P26-L10 |
| 11 | `user_id` via invoke config | P26-L11 |
| 12 | Memory on both generation paths | P26-L12 |
| 13 | SQLModel bootstrap | P26-L13 |
| 14 | Approve + continue same message | P26-L14 |
| 15 | English storage, bilingual UX | P26-L15 |
| 16 | Client `thread_id` contract | P26-L16 |

### 17–23. Smaller locks (summary)

| # | Decision | Lock |
| - | -------- | ---- |
| 17 | Key allowlist | P26-L17 |
| 18 | `location_id` 1–14 validation | P26-L18 |
| 19 | No-proposal routes | P26-L19 |
| 20 | Checkpoint vs Postgres split | P26-L20 |
| 21 | Env tunables | P26-L21 |
| 22 | Doc/test paths | P26-L22 |
| 23 | Support Agent only | P26-L23 |

---

## Locked decisions — Architecture (P26-L1)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L1** | Durable memory backend | **Postgres** — structured episodic store |
| **P26-L1a** | Tables | `agent_memory_entries` + `agent_memory_audit_log` |
| **P26-L1b** | Rejected backends | Qdrant, knowledge graph, fine-tuning, prompt-stuffing |
| **P26-L1c** | Checkpoint scope | SQLite (`AGENT_CHECKPOINT_DB_PATH`) = session/pending only |
| **P26-L1d** | Interface | `services/api/agent/memory/store.py` — `read_memory()`, `write_memory()`, `log_proposal()` |
| **P26-L1e** | Entry shape | `location_id`, `category`, `key`, `value`, `source`, `approved_by`, `approved_at`, optional `expires_at` |
| **P26-L1f** | Retrieval | Exact lookup by location + category/key — not semantic search |

---

## Locked decisions — Denylist (P26-L2)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L2** | Denylist module | `agent/memory/denylist.py` |
| **P26-L2a** | Allowed categories | `hours` \| `suppliers` \| `known_incidents` \| `preferences` |
| **P26-L2b** | Enforcement | Proposal gate + write gate |
| **P26-L2c** | Brasa Points / PII | Never |
| **P26-L2d** | Payroll / compensation | Never |
| **P26-L2e** | One-off noise | Never |
| **P26-L2f** | Live operational snapshots | Never — tools/telemetry |
| **P26-L2g** | KB-canonical policy | Never — RAG reindex |
| **P26-L2h** | Security / guardrails content | Never |
| **P26-L2i** | Allergen "zero risk" | Never |
| **P26-L2j** | Rejected / unapproved | Never in entries — audit/checkpoint only |
| **P26-L2k** | Unstructured blobs | Never — must match P26-L1e |
| **P26-L2l** | Denylist rejection | Audit `rejected_denylist` + reason |
| **P26-L2m** | Security patterns | Reuse context-25 override families (shared import) |

---

## Locked decisions — Lifecycle (P26-L3)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L3** | Ambiguous / topic change | **Reject** — `rejected_ambiguous` |
| **P26-L3a** | Pending idle | **24h** → `expired_no_response`; never auto-approve |
| **P26-L3b** | Concurrent proposals | **One pending** at a time |
| **P26-L3c** | Consolidation | **Upsert** on `(location_id, category, key)` |
| **P26-L3d** | Growth cap | **Max 12 entries per `location_id`** |
| **P26-L3e** | TTL defaults | `hours`/`suppliers`/`preferences` **365d**; `known_incidents` **180d** |
| **P26-L3f** | Expired rows | Excluded from `read_memory()`; re-approve resets TTL |
| **P26-L3g** | Purge | Optional nightly delete rows expired **>30 days** (stretch OK) |
| **P26-L3h** | Rejected proposals | Audit only |

### Audit outcome taxonomy

| Outcome | Memory write? |
| ------- | ------------- |
| `approved` | Yes |
| `approved_edited` | Yes |
| `rejected` | No |
| `rejected_ambiguous` | No |
| `expired_no_response` | No |
| `rejected_denylist` | No |
| `rejected_cap_exceeded` | No |

---

## Locked decisions — Poisoning (P26-L4)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L4** | Strategy | Defense in depth (5 layers) |
| **P26-L4a** | Guardrails order | `guard_input` before memory resolution every turn |
| **P26-L4b** | Write path | No auto-write — only classified approve/edit |
| **P26-L4c** | Classifier | `classify_memory_decision()` — no naive `"yes"` |
| **P26-L4d** | Accountability | `approved_by` = JWT user id + audit |
| **P26-L4e** | Write gate | P26-L2 even after user approve |
| **P26-L4f** | Read framing | User-confirmed block; **RAG wins** on KB policy conflicts |
| **P26-L4g** | Blocked routes | Force `memory_proposal: null` |
| **P26-L4h** | Rate limit | **Max 3 proposals/user/24h** |
| **P26-L4i** | Upsert forensics | Audit optional `superseded_value` |

---

## Locked decisions — Single agent (P26-L5)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L5** | Architecture | **No multi-agent** — extend existing graph |
| **P26-L5a** | Self-evaluation | Same LLM call → `answer` + optional `memory_proposal` |
| **P26-L5b** | Resolution | `resolve_memory_proposal` + rule classifier |
| **P26-L5c** | Consolidation | Deterministic `write_memory()` — not LLM |
| **P26-L5d** | Scope | No second graph or memory persona |
| **P26-L5e** | Trace | Memory nodes in same run's `trace_events` |

---

## Locked decisions — Continuity (P26-L6)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L6** | Model | Optional **`thread_id`** on `POST /agent/query` |
| **P26-L6a** | Server | Reuse client `thread_id` or new UUID |
| **P26-L6b** | Pending store | **Checkpoint only** (v1) |
| **P26-L6c** | UI | `sessionStorage` key `brasaland_support_thread_id` |
| **P26-L6d** | UI stretch | "New conversation" clears thread |
| **P26-L6e** | Expiry | Enforced in `resolve_memory_proposal` |
| **P26-L6f** | HTTP response | **`{ "answer" }` only** |

---

## Locked decisions — Scope (P26-L7)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L7** | Model | **Hybrid** — global ops + per-user preferences |
| **P26-L7a** | Global | `hours`, `suppliers`, `known_incidents` — `(location_id, category, key)`, `user_id NULL` |
| **P26-L7b** | Personal | `preferences` — `(user_id, category, key)` |
| **P26-L7c** | Global write | Any authenticated user (v1); audit `approved_by` |
| **P26-L7d** | Preferences write | Bound to approver's `user_id` |
| **P26-L7e** | Injection cap | **Max 8 rows** per generation turn |
| **P26-L7f** | Location write ACL | **Out of scope v1** |

---

## Locked decisions — Generation (P26-L8)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L8** | Output | JSON `{ answer, memory_proposal }` parsed in Python |
| **P26-L8a** | Default | `memory_proposal: null` on most turns |
| **P26-L8b** | Validation | P26-L1e + P26-L2 before pending |
| **P26-L8c** | Parse failure | Null proposal + trace; return usable `answer` |
| **P26-L8d** | Client/guardrails | Only **`answer`** → `validate_output` / HTTP |
| **P26-L8e** | Pending exists | Suppress new proposal |

---

## Locked decisions — Proposal classifier (P26-L9)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L9** | Classifier | **Rule-first** — no LLM v1 |
| **P26-L9a** | Outcomes | `approve` \| `reject` \| `edit` \| `ambiguous` + `reason` |
| **P26-L9b** | Approve bar | Assent + memory intent; bare `"yes"`/`"ok"` → ambiguous |
| **P26-L9c** | Order | Expiry → reject → edit → approve → ambiguous |
| **P26-L9d** | Modules | `agent/memory/proposal.py`, `patterns_proposal.py` |
| **P26-L9e** | LLM arbiter | Out of scope v1 |

---

## Locked decisions — Graph (P26-L10)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L10** | Order | `guard_input` → `resolve_memory_proposal` → `read_memory` → `classify` |
| **P26-L10a** | Resolve | No-op when no pending |
| **P26-L10b** | `memory_context` | Set by `read_memory`; not checkpointed |
| **P26-L10c** | New pending | Only from `generate` → `validate_output` |
| **P26-L10d** | Blocked paths | No proposals (see P26-L19) |
| **P26-L10e** | Trace | Memory nodes in eval trace order |

### Graph topology

```text
START → intake → guard_input ─┬→ guard_block → END
                               └→ resolve_memory_proposal → read_memory → classify → …
                                      (existing P2/P24/P25 paths)
                                      … → generate → validate_output → END

approve-only (no continued question):
  resolve_memory_proposal → memory_ack → END
```

**No `validate_output` on:** `guard_block`, `casual_reply`, `refuse`, `fallback`, `confirm_write`, `memory_ack`, `error`.

---

## Locked decisions — Auth (P26-L11)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L11** | Identity | Route passes `user_id=current_user.id` to invoke |
| **P26-L11a** | Storage | `config["configurable"]["user_id"]` only |
| **P26-L11b** | Audit | int `user_id` — not email/name |
| **P26-L11c** | Access | `get_config()` in nodes |
| **P26-L11d** | Missing on write | Refuse + trace |

---

## Locked decisions — Injection (P26-L12)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L12** | Scope | All paths reaching `generate_node` |
| **P26-L12a** | Paths | `generate_answer` (rag) + `generate_support_answer` (tool/both) |
| **P26-L12b** | Framing | P26-L4f block; omit if empty |
| **P26-L12c** | `read_memory` | Location hint + user preferences |
| **P26-L12d** | Structured gen | One wrapper in `agent/generation.py` |

---

## Locked decisions — Schema (P26-L13)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L13** | ORM | SQLModel in `agent/memory/models.py` |
| **P26-L13a** | Bootstrap | `ensure_agent_memory_schema(session)` — telemetry pattern |
| **P26-L13b** | Tables | `agent_memory_entries`, `agent_memory_audit_log` |
| **P26-L13c** | Uniqueness | Global vs preferences keys per P26-L7 |
| **P26-L13d** | Mutability | Audit append-only; entries upsert |
| **P26-L13e** | Database | Existing `DATABASE_URL` |

---

## Locked decisions — Same-turn approve (P26-L14)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L14** | Order | Resolve before classify; may replace `question` |
| **P26-L14a** | Classifier | Returns `continued_question` |
| **P26-L14b** | Approve + ops | Write then normal graph on remainder |
| **P26-L14c** | Approve only | `memory_ack` template → END |
| **P26-L14d** | Ambiguous + ops | Reject memory; continue on message |
| **P26-L14e** | Required eval | Approve + incident question in one invoke |

### `memory_ack` template (reproducible)

```text
Got it — I'll remember that for next time.
```

---

## Locked decisions — Language (P26-L15)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L15** | Stored `value` | **English** |
| **P26-L15a** | Proposal schema | `memory_proposal.value` must be English |
| **P26-L15b** | Injection | English `memory_context` |
| **P26-L15c** | UX | Proposal/answer in user's language |
| **P26-L15d** | Prompt | Answer in user language; memory block English |

---

## Locked decisions — Client contract (P26-L16)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L16** | API | Optional `thread_id` on request |
| **P26-L16a** | Server | `body.thread_id or uuid4()` |
| **P26-L16b** | Minting | Client generates UUID |
| **P26-L16c** | UI storage | `sessionStorage` |
| **P26-L16d** | Client | `askSupportAgent(question, threadId?)` |
| **P26-L16e** | Tests | Fixed `thread_id` across two invokes |
| **P26-L16f** | Audit | Optional `thread_id` on audit rows |

---

## Locked decisions — Keys (P26-L17)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L17** | Keys | `snake_case` + per-category allowlist in `agent/memory/keys.py` |

### Category key allowlist (v1)

| Category | Allowed keys |
| -------- | ------------ |
| `hours` | `weekday_open`, `weekday_close`, `weekend_open`, `weekend_close`, `friday_close`, `special_hours` |
| `suppliers` | `meat_delivery_day`, `vegetable_delivery_day`, `general_delivery_day` |
| `known_incidents` | `zero_sales_pattern`, `pos_outage_pattern`, `power_outage_pattern` |
| `preferences` | `report_format`, `language_preference`, `summary_style` |

---

## Locked decisions — Validation & routes (P26-L18–L23)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P26-L18** | `location_id` | Required **1–14** for global categories via `get_location()` |
| **P26-L19** | No-proposal routes | `MEMORY_PROPOSAL_DISABLED_ROUTES`: `guard_block`, `casual_reply`, `error`, `refuse`, `fallback`, `confirm_write`, `inventory_write_block`, `memory_ack`, generation provider fallback |
| **P26-L20** | State split | Checkpoint: `pending_proposal`, `pending_proposal_at`; not `memory_context` |
| **P26-L21** | Env vars | Document in `.env.example` (see below) |
| **P26-L22** | Artifacts | `docs/agent/memory-design.md`, `docs/agent/memory-evidence.md`, `tests/pipelines/test_agent_memory.py` |
| **P26-L23** | Boundary | Support Agent only — `/knowledge/query` unchanged |

---

## Graph state fields (extend `AgentState`)

Add to `services/api/agent/state.py` (defaults in `initial_state()` per P25-L2b):

```python
memory_context: str
pending_proposal: dict[str, Any] | None
pending_proposal_at: str | None          # ISO timestamp
last_memory_outcome: str | None          # optional debug/trace
```

**Checkpoint persists:** `pending_proposal`, `pending_proposal_at` only (P26-L20).

**Invoke config (not state):** `user_id`, `auth_header`, `thread_id`.

---

## File layout

| Responsibility | Location |
| -------------- | -------- |
| SQLModel + schema bootstrap | `services/api/agent/memory/models.py` |
| Store + read/write | `services/api/agent/memory/store.py` |
| Denylist | `services/api/agent/memory/denylist.py` |
| Key allowlist | `services/api/agent/memory/keys.py` |
| Proposal classifier | `services/api/agent/memory/proposal.py`, `patterns_proposal.py` |
| Pydantic schemas | `services/api/agent/memory/schemas.py` |
| Structured generation wrapper | `services/api/agent/generation.py` |
| Graph nodes | `services/api/agent/graph.py` |
| HTTP + invoke | `services/api/agent/routes.py`, `schemas.py` |
| Backoffice client | `uis/backoffice/lib/agent.ts`, `app/support/page.tsx` |
| Tests | `services/api/tests/pipelines/test_agent_memory.py` |
| Design + evidence | `docs/agent/memory-design.md`, `docs/agent/memory-evidence.md` |

---

## Environment variables

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `AGENT_MEMORY_CAP_PER_LOCATION` | `12` | P26-L3d |
| `AGENT_MEMORY_PENDING_TTL_HOURS` | `24` | P26-L3a |
| `AGENT_MEMORY_PROPOSAL_RATE_LIMIT` | `3` | P26-L4h |
| `AGENT_MEMORY_PROPOSAL_RATE_WINDOW_HOURS` | `24` | P26-L4h |
| `AGENT_MEMORY_INJECT_MAX_ROWS` | `8` | P26-L7e |
| `AGENT_MEMORY_TTL_HOURS` | `8760` | Default category TTL (365d) |
| `AGENT_MEMORY_KNOWN_INCIDENTS_TTL_HOURS` | `4320` | 180d |

Invalid/missing → default + warning log (P25-L11e pattern). Document in repo root `.env.example`.

---

## Implementation phases (single branch / single PR)

| Phase | Deliverable | Verification |
| ----- | ----------- | ------------ |
| **P26-0** | ✅ This file + `docs/agent/memory-design.md` scaffold | Spec review |
| **P26-1** | ✅ SQLModel schema + `store.py` + denylist/keys | `test_agent_memory.py` green |
| **P26-2** | ✅ Structured generation wrapper + P26-L8 validation | `test_agent_memory_generation.py` green |
| **P26-3** | ✅ Graph nodes + checkpoint pending + `thread_id` API/UI | `test_agent_memory_graph.py` green |
| **P26-4** | ✅ Proposal classifier polish + audit log + rate limit | `test_agent_memory_proposal.py`, `test_agent_memory_rate_limit.py` green |
| **P26-5** | ✅ Consolidation upsert/TTL/cap + `read_memory` injection polish | `test_agent_memory_consolidation.py` green |
| **P26-6** | ✅ Evidence doc + graph trace regression gate | `test_agent_memory_regression.py` + full agent pytest green |

**Order:** P26-1 → P26-2 → P26-3 → P26-4 → P26-5 → P26-6.

---

## Evaluation criteria (grading)

- [x] Memory architecture justified in `docs/agent/memory-design.md` and matches implementation
- [x] Explicit read/write interface — not system-prompt accumulation
- [x] ≥3 documented examples each: memorable vs non-memorable interactions
- [x] Proposal communicated in same conversational answer
- [x] No write without classified approve/edit — not naive `"yes"`
- [x] One pending proposal; silence/ambiguity → reject
- [x] Every proposal/outcome in audit log (approved and rejected)
- [x] Functional consolidation/cleanup documented
- [x] ≥2 evidence cycles in `docs/agent/memory-evidence.md`
- [x] Denylist and context-21/25 restrictions honored
- [x] Guardrails prerequisite — memory after SEC-114

---

## Acceptance checklist (merge gate)

- [x] All `P26-L*` locks implemented
- [x] `docs/agent/memory-design.md` complete with Q1–Q5 + rejected architecture rationale
- [x] `docs/agent/memory-evidence.md` — approved + rejected cycles
- [x] Graph includes `resolve_memory_proposal`, `read_memory`, `memory_ack`
- [x] Optional `thread_id` on API + UI sessionStorage
- [x] No memory metadata in `AgentQueryResponse` (P1-L8)
- [x] `/knowledge/query` unchanged (P26-L23)
- [x] Guardrails + agent evals green; trace order updated (P26-6)
- [x] `.env.example` documents P26-L21 vars

---

## Numbering note

**context-26** is reserved for MEM-092 agent memory and self-improvement (Support Agent `/agent/query`, Milestone 8).

---

_Internal document — Brasaland · Context 26 · Agent Memory and Self-Improvement_
