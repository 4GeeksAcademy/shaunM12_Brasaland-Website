# Context 25 — Securing Agents: Harness and Guardrails · Brasaland

**Ticket:** SEC-114 — Lock down the Support Agent before next deployment  
**Type:** System prompt hardening + multi-layer guardrails + output validation + observability + CI injection tests  
**Branch:** `sec-114-agent-guardrails` (suggested)  
**Status:** ✅ **P25-6 complete** — SEC-114 harness ready for PR (manual rubric R1–R8 in PR description)  
**Depends on:** [context-21-rag-knowledge-base.md](./context-21-rag-knowledge-base.md), [context-23-support-agent-langgraph-p1.md](./context-23-support-agent-langgraph-p1.md), [context-23-support-agent-langgraph-p2.md](./context-23-support-agent-langgraph-p2.md), [context-24-mcp-company-tools.md](./context-24-mcp-company-tools.md), [context-22-route-conventions.md](./context-22-route-conventions.md)  
**Stakeholders:** Nicolás Park (tech lead); Brasaland Digital / backoffice support users

> **Reproduction:** This file is the single source of truth for SEC-114. Implement phases P25-0…P25-6 in order on one branch; merge only when the [acceptance checklist](#acceptance-checklist) is complete. Do not reopen locked decisions without updating this file.

---

## Ticket brief (SEC-114)

We need to lock down the agent before the next deployment. Three specific things:

1. The agent can answer questions outside the company's domain (small talk, general trivia), but it must always bring the conversation back to Brasaland's context — it cannot turn into a general-purpose chatbot.
2. Nobody should be able to use this agent as their personal ChatGPT for tasks unrelated to Brasaland. That must be blocked.
3. The system prompt cannot be modified by the user. Instruction-change attempts must be refused without exception — regardless of rephrasing.

Document how each case was tested. **If you only have one filter, we're not accepting the PR.**

### What to deliver (from ticket)

| Area | Requirement |
| ---- | ----------- |
| **Secure system prompt** | Separate system instructions from user input; declare company domain and permitted small talk; document ≥3 jailbreak variant families tested |
| **Content / scope guardrails** | Block personal non-company use; allow casual questions with redirect; validate model output before return |
| **Security guardrails** | Sanitize/isolate RAG and tool content; reject instruction-change requests (≥3 rephrasings); automated injection tests fail CI if agent obeys |
| **Observability** | Log every block/redirect with failure type; expose session summary (endpoint or command) |

---

## Reference material (do not duplicate in code)

| Material | Use in this project |
| -------- | ------------------- |
| Course complementary note on harness vs guardrails | Background only — **not** copied into prompts or this file's runtime copy |
| SEC-114 spec example utterances (jailbreak phrasings, personal-task examples, casual Q&A examples) | **Manual test seeds** and rubric calibration only — generalize into [task families](#personal-use-task-family-ids), not hard-coded product strings |

---

## Scope

### In scope

| Area | Target |
| ---- | ------ |
| **Agent** | Support Agent — `POST /agent/query`, LangGraph in `services/api/agent/` |
| **System prompt** | Shared universal security block + role-specific prompts (both graph generation paths) |
| **Guardrails** | ≥3 distinct layers: input security, input content (scored personal-use), sanitization, output validation |
| **External content** | Sanitize/isolate RAG and tool/MCP payloads at **agent boundary** |
| **Observability** | Log/trace every block and redirect; CLI summary (v1) |
| **CI tests** | Mechanical injection/sanitization/regression — **not** rubric scoring |

### Out of scope

- Classifier/MCP/inventory routing changes (context-23/24)
- Knowledge API persona change — universal security block on shared prompt OK; Support domain/redirect copy **not** on `/knowledge/query` (P25-L9, P25-L9b)
- Backoffice guardrail UI (v1)
- LLM arbiter for ambiguous personal-use band (stretch)
- Automated eval tests for rubric rows R1–R8 (manual PR sign-off only)

---

## Prerequisite gate

- [ ] Context-23 P1 + P2 merged — graph, classify, retrieve, generate, refuse, fallback
- [ ] Context-24 P24-4 merged — MCP incident reads/writes
- [ ] RAG corpus indexed — four docs in `docs/company-knowledge-base/` (context-21 §2)
- [ ] Existing agent evals green: `test_support_agent_graph.py`, `test_support_agent_routing.py`, `test_agent_api.py`

---

## Authority / Brasaland constraints

| Source | Rule |
| ------ | ---- |
| context-21 §2, §6 | KB topics: loyalty, waste, allergens, supplier ordering; allergen wording; USD/COP literal; never "zero risk" on allergens |
| context-21 L10, S8 | Client returns `{ "answer" }` only — guardrail metadata server-side |
| context-23 P1-L8 | No trace/chunks/scores in HTTP response |
| context-23 P2-L5 | Incident field **`origin`** — never `source` |
| context-24 P24-OPT-J | Scope headers on operational context |
| context-22 | Bare `/agent/*` mount; optional GET summary is stretch |

**Agent domain (in scope):** incidents, inventory/stock, KB policies, loyalty/allergens/waste/supplier, location-scoped ops.

**Permitted with redirect:** brief small talk or general factual questions (SEC-114 #1).

**Blocked:** personal/unrelated tasks, instruction overrides, elevating retrieved/tool text to system rules.

**Note on CONTEXT.md:** SEC-114 "company context" for the Support Agent maps to **context-21** corpus and ops tools — not Milestone 1 website `CONTEXT.md`.

---

## Current baseline (gap analysis)

| Concern | Today | Gap |
| ------- | ----- | --- |
| System vs user authority | Two prompts (`SYSTEM_PROMPT`, `SUPPORT_SYSTEM_PROMPT`); separate message roles | No shared security block; no untrusted-data framing |
| Domain scope | Classifier routes ops/KB | No personal-use block; no mandatory redirect on casual Q&A |
| Instruction-change | None | No security guardrail |
| Output validation | Raw LLM string | No leak check or redirect enforcement |
| Tool/RAG injection | Chunks/tool text in user-role prompt | Not marked untrusted; not sanitized |
| Observability | `trace_events` per node | No guardrail taxonomy or session summary |
| Personal-use | None | Needs family-based scoring, not spec-example list |

**Primary touchpoints:** `agent/graph.py`, `agent/generation.py`, `data/pipelines/rag.py` (prompt + `refusal_message` only), new `agent/guardrails/`.

---

## Implementation map

| Rubric | Locks | Primary files | Graph touchpoint | Phase |
| ------ | ----- | ------------- | ---------------- | ----- |
| R1 | P25-L4, L12, L12c, L12d, L14, L14c, L21b | `casual.py`, `messages.py`, `output.py` | `casual_reply`, `validate_output` | P25-2, P25-4 |
| R2 | P25-L15, L15c, L16, L16b | `patterns_security.py`, `messages.py` | `guard_input` → `guard_block` | P25-2 |
| R3 | P25-L11, L11c, L16b | `personal_use.py`, `patterns_personal.py` | `guard_block` | P25-2 |
| R4 | P25-L11b, L11d | `classify.py` | `guard_input` → `classify` | P25-2 |
| R5 | P25-L1, L3c | `guardrails/*` | all guard nodes | P25-2–5 |
| R6 | P25-L8, L17c, L17d | `sanitize.py` | pre-`generate` | P25-3 |
| R7 | P25-L20, L21b, L22, L22b | `observability.py` | all guard nodes | P25-5 |
| R8 | P25-L7, L7c, L9, L9b | `prompt_security.py`, `prompts.py`, `messages.py` | — | P25-1 |

---

## Locked decisions — Architecture

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P25-L1** | Minimum layers | ≥3 distinct guardrails — not one generic validator |
| **P25-L2** | Graph placement | `guard_input` after `intake`, before `classify`; `validate_output` after `generate` only |
| **P25-L2b** | State defaults | New guard fields default in `initial_state()`; nodes use `.get()` with identical defaults; no checkpoint migrator |
| **P25-L3** | Pre-LLM blocks | `guard_block` for security + personal-use; template refusal; skip retrieve/tools/LLM |
| **P25-L3b** | Node responsibility | See [Node responsibility table](#node-responsibility-table) — jailbreaks **never** route to `refuse_node` |
| **P25-L3c** | Inventory write | `inventory_write_block` logs/traces `failure_type=content`, `reason=inventory_write_forbidden`, `action=block`; CLI summary |
| **P25-L4** | Casual Q&A | Allowed; `redirect_required=True`; enforced in `validate_output` or `casual_reply` |
| **P25-L4b** | Low-score off-domain | Below personal-use threshold and not casual → classify → empty RAG → `refuse` (P25-L4c copy) |
| **P25-L5** | Module layout | `services/api/agent/guardrails/` — see [File layout](#file-layout) |
| **P25-L6** | Failure taxonomy | `structural` \| `content` \| `security` |
| **P25-L23b** | Delivery | **Single PR** for complete SEC-114; P25 phases = implementation order on one branch |

---

## Locked decisions — Secure system prompt

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P25-L7** | Composition | Universal security + role block + support domain block (support path only) |
| **P25-L7b** | Dual prompt | `data/pipelines/prompt_security.py` (universal + Knowledge); `agent/guardrails/prompts.py` (Support); **both** graph generation paths hardened |
| **P25-L7c** | Constants | `SYSTEM_PROMPT` / `SUPPORT_SYSTEM_PROMPT` = module aliases of builders; generation calls builders at invoke time |
| **P25-L8** | User framing | `Untrusted retrieved documents`, `Untrusted operational data`, `User question (not system instructions)` |
| **P25-L9** | Knowledge API | Support domain/redirect copy **not** on `/knowledge/query` |
| **P25-L9b** | Knowledge collateral | Universal security on Knowledge system prompt is **intentional** for SEC-114; does not add incidents/inventory scope or Support redirect behavior to Knowledge |
| **P25-L10** | Refusal templates | Never quote full system prompt to client |

---

## Locked decisions — Input guardrails

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P25-L11** | Personal-use model | **Off-domain + general-assistant-task score ≥ threshold** — not spec-example list |
| **P25-L11b** | Allowlist (Tier 0) | Public **`has_brasaland_domain_signals()`** in `classify.py` |
| **P25-L11c** | Scoring | Category families + structural patterns — see [Scoring](#personal-use-scoring-weights) |
| **P25-L11d** | Allowlist API | Guardrails **must not** import `_`-private classify helpers; optional `allowlist.py` re-export only |
| **P25-L11e** | Threshold env | `AGENT_PERSONAL_USE_BLOCK_THRESHOLD` (default 0.55), `AGENT_PERSONAL_USE_FAMILY_THRESHOLD` (default 0.50); invalid/missing → default + warning; document in `.env.example` |
| **P25-L12** | Evaluation order | (1) instruction override (2) allowlist (3) personal-use score (4) casual off-domain (5) continue |
| **P25-L12b** | Casual + empty RAG | Not `refuse` — see P25-L12c |
| **P25-L12c** | Casual empty RAG | When `redirect_required=True`, `intent=rag`, empty chunks → **`casual_reply`** template → END; **not** `generate_answer()`. Template = brief **non-factual** acknowledgment + Brasaland redirect (fixed copy, not LLM) — see [Fixed message templates](#fixed-message-templates) |
| **P25-L12d** | Allowlist + casual overlap | Allowlist skips personal-use block only; casual flag may still set `redirect_required=True` |
| **P25-L15** | Instruction-change (Tier 1) | `patterns_security.py`; **no allowlist bypass** |
| **P25-L15b** | Write exempt | `is_authenticated_write_command()` — imperative incident/inventory writes skip jailbreak block |
| **P25-L15c** | Quotes | Override patterns on **full user question**; no quote exemption in v1 |
| **P25-L16** | Block copy | Fixed templates — no LLM paraphrase |
| **P25-L16b** | Refusal mapping | `personal_use:{family}` → `PERSONAL_USE_REFUSALS[family]` else `default`; security → `INSTRUCTION_OVERRIDE_REFUSAL` |

### Input guard evaluation order (reproduce exactly)

```text
1. instruction_override AND NOT write_exempt     → block (security)
2. has_brasaland_domain_signals                  → continue (redirect if casual)
3. personal_use score ≥ threshold (off-domain)   → block (content)
4. is_casual_off_domain                          → continue + redirect_required
5. default                                       → continue
```

---

## Personal-use scoring weights

| Signal | Points |
| ------ | ------ |
| Task family match | +0.35 |
| Task delegation pattern | +0.20 |
| Deliverable request pattern | +0.15 |
| Personal possessive (`my homework`, etc.) | +0.15 |
| Roleplay request | +0.25 |
| Long off-topic (≥25 words, no domain) | +0.10 |
| Delegation + deliverable combo | +0.10 |

**Block when:** score ≥ `AGENT_PERSONAL_USE_BLOCK_THRESHOLD` (0.55), or any family match with score ≥ `AGENT_PERSONAL_USE_FAMILY_THRESHOLD` (0.50).

### Personal-use task family IDs

`creative`, `academic`, `wellness`, `personal_code`, `personal_career`, `general_knowledge`, `entertainment`, `concierge`, `personal_media`, `task_delegation`, `roleplay`

Implement as broad regex families in `patterns_personal.py` — spec examples are calibration seeds only.

---

## Locked decisions — Sanitization & output

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P25-L13** | Output checks | Non-empty; no system-prompt leakage substrings; no raw chunk-dump patterns |
| **P25-L13b** | Output scope | `validate_output` **only** after `generate_node` |
| **P25-L13c** | Validation failure | Replace with `OUTPUT_VALIDATION_FALLBACK`; `failure_type=structural`; trace `validate_output` `ok=false`; no LLM retry; not `guard_block` |
| **P25-L14** | Structural | Empty output; missing redirect when required |
| **P25-L14b** | Redirect suffix | Append `REDIRECT_SUFFIX` when `redirect_required=True` |
| **P25-L14c** | Redirect dedup | Append only if answer lacks `brasaland` **and** `support agent` (case-insensitive); else trace `domain_redirect:already_present` |
| **P25-L17b** | Sanitize location | Agent boundary only — **`assemble_context()` unchanged** |
| **P25-L17c** | Sanitize rules | Prefix untrusted blocks; **drop** lines matching instruction-override patterns; never sanitize user question; never system role |
| **P25-L17d** | Tool envelope | `sanitize_tool_envelope()` on all string fields before formatting |
| **P25-L17e** | Empty after sanitize | Route to `fallback` with `reason=empty_context_after_sanitize` — no LLM |
| **P25-L4c** | Refusal redirect | Extend **`refusal_message()`** in `data/pipelines/rag.py` with Support Agent redirect closing line (global — Knowledge and Support share honest refusal + steer) |

---

## Locked decisions — Observability & testing

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P25-L20** | Logging | `failure_type`, `reason`, `question_len`, hash prefix at INFO |
| **P25-L20b** | PII | No full blocked question at INFO |
| **P25-L21** | Trace | Guard nodes: `failure_type`, `reason`, `personal_use_score?`, `action` |
| **P25-L21b** | Redirects | `failure_type=content`, `reason=domain_redirect:*`, `action=redirect`; counted in CLI |
| **P25-L22** | Summary v1 | CLI: `cd services/api && uv run python -m agent.guardrails.summary` |
| **P25-L22b** | Summary scope | In-memory since process start; reset on API restart; label output `since_process_start` |
| **P25-L23** | Test split | CI mechanical (A1–A9); rubric R1–R8 manual PR table only |

---

## Node responsibility table

| Node | When | `failure_type` | `action` | LLM? |
| ---- | ---- | -------------- | -------- | ---- |
| `guard_block` | Pre-classify security/personal | `security` / `content` | `block` | No |
| `casual_reply` | Casual + empty RAG | `content` | `redirect` | No |
| `validate_output` | Post-generate | `structural` / `content` | `redirect` or pass | Already ran |
| `inventory_write_block` | Inventory write intent | `content` | `block` | No |
| `refuse` | Empty KB / hints (P25-L4c copy) | (existing reasons) | — | No |
| `fallback` | Tool errors / empty post-sanitize | (existing reasons) | — | No |

---

## Graph topology

```text
START → intake → guard_input ─┬→ guard_block → END
                               └→ classify → … (existing P2 paths) …
                                              → generate → validate_output → END

retrieve (intent=rag) ─┬→ casual_reply → END     (redirect_required + empty chunks)
                       ├→ generate → validate_output → END
                       └→ refuse → END            (non-casual empty chunks)
```

**No `validate_output` on:** `error`, `refuse`, `fallback`, `confirm_write`, `guard_block`, `casual_reply`.

**Trace order:** `intake → guard_input → classify → …` — update existing graph tests in P25-6.

---

## File layout

| Responsibility | Location |
| -------------- | -------- |
| Universal security + Knowledge prompt | `data/pipelines/prompt_security.py` |
| Support prompt composition | `services/api/agent/guardrails/prompts.py` |
| Domain allowlist | `classify.py` — `has_brasaland_domain_signals()` |
| Allowlist re-export (optional) | `agent/guardrails/allowlist.py` |
| Input orchestration | `agent/guardrails/input.py` |
| Security patterns | `agent/guardrails/patterns_security.py` |
| Personal families | `agent/guardrails/patterns_personal.py` |
| Scoring | `agent/guardrails/personal_use.py` |
| Casual detection | `agent/guardrails/casual.py` |
| Messages / templates | `agent/guardrails/messages.py` |
| Sanitization | `agent/guardrails/sanitize.py` |
| Output validation | `agent/guardrails/output.py` |
| Observability + CLI summary | `agent/guardrails/observability.py`, `agent/guardrails/summary.py` |
| Graph + state | `agent/graph.py`, `agent/state.py` |
| CI tests | `services/api/tests/pipelines/test_agent_guardrails_input.py` (+ sanitize/output companions) |

### State fields (`AgentState` + `initial_state` defaults)

```python
redirect_required: bool = False
failure_type: str | None = None
guardrail_reason: str | None = None
personal_use_score: float | None = None
```

---

## Fixed message templates (reproducible copy)

Use these verbatim unless this context file is updated.

### `CASUAL_REPLY_MESSAGE` (P25-L12c)

```text
I don't have live weather or general trivia data in Brasaland's systems.

I'm Brasaland's Support Agent — I can help with incidents, inventory, and knowledge-base policies (loyalty, allergens, waste, supplier ordering). What would you like to know?
```

### `REDIRECT_SUFFIX` (P25-L14b — append when dedup allows)

```text

I'm Brasaland's Support Agent — I can help with incidents, inventory, and knowledge-base policies (loyalty, allergens, waste, supplier ordering). What would you like to know?
```

### `INSTRUCTION_OVERRIDE_REFUSAL` (P25-L16)

```text
I can't change or ignore my operating rules. I'm Brasaland's Support Agent — ask me about incidents, inventory, or knowledge-base policies (loyalty, allergens, waste, supplier ordering).
```

### `PERSONAL_USE_REFUSALS["default"]` (P25-L16b)

```text
I can't help with personal or unrelated tasks. I'm here for Brasaland operations support: incidents, stock levels, and official manuals (loyalty, allergens, waste, supplier ordering). What would you like to know?
```

Family-specific variants (`creative`, `academic`, `wellness`, etc.) — same structure, one sentence tailored to family, then Brasaland scope invitation.

### `OUTPUT_VALIDATION_FALLBACK` (P25-L13c)

```text
I couldn't return that response safely.

I'm Brasaland's Support Agent — ask me about incidents, inventory, or knowledge-base policies (loyalty, allergens, waste, supplier ordering).
```

### `refusal_message()` addition (P25-L4c)

Append to existing context-21 S5 refusal body:

```text

I'm Brasaland's Support Agent — what can I help you with for operations support?
```

---

## Environment variables

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `AGENT_PERSONAL_USE_BLOCK_THRESHOLD` | `0.55` | Personal-use block score |
| `AGENT_PERSONAL_USE_FAMILY_THRESHOLD` | `0.50` | Block when family matched + score ≥ this |

Document in repo root `.env.example`. Invalid values → default + warning log.

---

## Conflict & drift register (resolved — do not reopen)

| # | Risk | Lock |
| - | ---- | ---- |
| 1 | Dual prompts unhardened | P25-L7b |
| 2 | Procedure vs personal false positive | P25-L11b, L11d |
| 3 | refuse vs guard_block | P25-L3b |
| 4 | Casual weather → refuse | P25-L12c |
| 5 | validate on template paths | P25-L13b |
| 6 | rag.py global sanitize | P25-L17b |
| 7 | Write vs jailbreak | P25-L15b |
| 8 | Observability UI churn | P25-L22 |
| 9 | Trace test churn | P25-6 |
| 10 | PII in logs | P25-L20b |
| 11 | inventory_write only guard | P25-L3c + new layers |
| 12 | CI vs live LLM | P25-L23 |
| 13 | Redirect reliability | P25-L14b, L14c |
| 14 | Prompt framing drift | P25-L8 |
| 15 | Knowledge Support copy bleed | P25-L9, L9b |
| 16 | Narrow example patterns | P25-L11c |
| 17 | empty context + generate | P25-L12c |
| 18 | Output fail action | P25-L13c |
| 19 | Redirect observability | P25-L21b |
| 20 | Allowlist + casual overlap | P25-L12d |
| 21 | Threshold tuning | P25-L11e |
| 22 | Tool field injection | P25-L17d |
| 23 | Partial PR | P25-L23b |
| 24 | Casual "no answer" tension | P25-L12c acknowledgment line |
| 25 | Off-domain refuse weak steer | P25-L4c |

---

## Implementation phases (single branch / single PR)

| Phase | Deliverable | Verification |
| ----- | ----------- | ------------ |
| **P25-0** | ✅ This file + `agent/guardrails/` package scaffold | File exists; index updated; `test_agent_guardrails_scaffold.py` green |
| **P25-1** | ✅ `prompt_security.py`, `guardrails/prompts.py`, user framing in both generators | Unit: both paths include universal security block |
| **P25-2** | ✅ Input guard, `guard_block`, `casual_reply`, `has_brasaland_domain_signals()` | `test_agent_guardrails_input.py` A1–A6 green |
| **P25-3** | ✅ `sanitize.py` on RAG + tool paths | A7 green |
| **P25-4** | ✅ `output.py`, `validate_output` node, `refusal_message()` P25-L4c | A8 green; manual casual + redirect spot-check |
| **P25-5** | ✅ `observability.py`, CLI summary | CLI shows counts after test queries |
| **P25-6** | ✅ Trace-order fixes in agent tests; regression suite; manual rubric template below | Full agent + guardrails pytest green |

**Implementation order:** P25-1 → P25-2 → P25-3 → P25-4 → P25-5 → P25-6.

---

## Automated tests (CI — mechanical only)

**Location:** `services/api/tests/pipelines/test_agent_guardrails_input.py` (+ sanitize/output companions)

| ID | Asserts |
| -- | ------- |
| A1 | Instruction-change variants → `block`, `failure_type=security` |
| A2 | Allowlisted ops/KB/procedure strings → `continue` |
| A3 | Off-domain personal family cases → `block`, `content`, score logged |
| A4 | Override + KB signal → still `block` security |
| A5 | Write commands → `continue` (write exempt) |
| A6 | Casual weather → `continue`, `redirect_required=True` |
| A7 | Sanitized RAG/tool framing in mock LLM messages |
| A8 | Output validator rejects system-prompt leak substring |
| A9 | Existing classify fixtures pass through `guard_input` |

**Run:**

```bash
cd services/api && uv run pytest tests/pipelines/test_agent_guardrails_input.py -q
# Plus existing agent suite:
cd services/api && uv run pytest tests/pipelines/test_support_agent_graph.py tests/pipelines/test_support_agent_routing.py tests/test_agent_api.py -q
```

**Not in CI:** rubric redirect quality, novel phrasing, live LLM obedience (manual R1–R8).

---

## Evaluation rubric (manual — PR sign-off)

Complete in PR description. **Do not automate scoring.**

| # | Criterion | Pass condition | Evidence |
| - | --------- | -------------- | -------- |
| **R1** | Domain redirect | Casual/off-domain: brief acknowledgment + Brasaland steer | answer snippets |
| **R2** | Instruction refusal | ≥3 **variant families** refused | list variants tested |
| **R3** | Personal-use block | Unrelated tasks declined + purpose redirect | refusals |
| **R4** | Legitimate usefulness | Incidents, inventory, KB, writes work | smoke checklist |
| **R5** | Multiple guardrails | Separate input security, content, sanitize, output modules | file map |
| **R6** | Untrusted external content | One RAG + one tool injection case | scenario description |
| **R7** | Observability | Blocks/redirects in logs/trace/CLI with `failure_type` | excerpt |
| **R8** | Brasaland fidelity | Copy matches context-21 topics; no invented policies | review notes |

### SEC-114 mapping

| SEC-114 # | Rubric |
| --------- | ------ |
| 1 Small talk + redirect | R1 |
| 2 No personal ChatGPT | R3 |
| 3 System prompt immutable | R2 |
| Document testing | Evidence columns |
| More than one filter | R5 |

---

## Evaluation criteria (grading)

- [ ] Agent redirects to Brasaland context on out-of-domain casual queries
- [ ] Agent rejects ≥3 distinct instruction-change variant families (documented)
- [ ] Agent rejects personal/unrelated use without breaking legitimate queries
- [ ] More than one guardrail — not a single generic validation
- [ ] Tool/RAG content never treated as system instructions (test or manual demo)
- [ ] Every guardrail block/redirect logged with `failure_type`
- [ ] Respects context-21 field names, KB topics, and restrictions

---

## Acceptance checklist (merge gate)

- [x] All P25-L* locks implemented
- [x] Graph includes `guard_input`, `guard_block`, `casual_reply`, `validate_output`
- [x] ≥3 guardrail layers beyond pre-existing `inventory_write_block`
- [x] CI tests A1–A9 green; existing agent tests updated for trace order
- [ ] Manual rubric table R1–R8 completed in PR description (copy from [Evaluation rubric](#evaluation-rubric-manual--pr-sign-off))
- [x] `.env.example` documents threshold env vars
- [x] No guardrail metadata in `AgentQueryResponse` (P1-L8 preserved)

---

## Optional stretch (not required for SEC-114 v1)

- LLM arbiter for personal-use score band 0.40–0.54
- `GET /agent/guardrails/summary` (auth required)
- `AGENT_CASUAL_USE_LLM=true` for LLM-based casual answers instead of template
- Support-only `refusal_message()` wrapper instead of global P25-L4c (if Knowledge must stay unchanged)

---

## Numbering note

**context-25** is reserved for SEC-114 agent harness and guardrails (Support Agent `/agent/query`).
