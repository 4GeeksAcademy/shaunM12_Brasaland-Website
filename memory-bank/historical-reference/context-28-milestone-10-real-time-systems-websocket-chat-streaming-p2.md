# Context 28 — Milestone 10 Real-Time Systems: WebSocket Chat Streaming (Part 2)

**Ticket:** Milestone 10 Part 2 — Real-time Support Agent chat via WebSockets  
**Type:** FastAPI WebSocket + session orchestrator + in-memory pub/sub + Postgres chat persistence + backoffice `/support` UI + tests  
**Branch:** `milestone-10-real-time-systems-websocket-chat-streaming-p2`  
**Status:** Spec locked — ready for implementation  
**Depends on:** [context-23-support-agent-langgraph-p1.md](./context-23-support-agent-langgraph-p1.md), [context-23-support-agent-langgraph-p2.md](./context-23-support-agent-langgraph-p2.md), [context-22-route-conventions.md](./context-22-route-conventions.md), [context-26-milestone-8-agent-memory.md](./context-26-milestone-8-agent-memory.md), root [`CONTEXT.md`](../../CONTEXT.md) (company identity only)  
**Companion (Part 1 — separate branch):** [context-28-milestone-10-real-time-systems-sse-p1.md](./context-28-milestone-10-real-time-systems-sse-p1.md) — RFP SSE notifications (**not Part 2 scope**)  
**Stakeholders:** Location managers / Brasaland backoffice support users; Nicolás Park (tech lead)

> **Read this file before Part 2 implementation.** Part 1 SSE is a separate branch and must not be mixed into this PR.

---

## Ticket brief (Part 2)

The support agent already works — **do not change its tools, memory logic, or graph routing**. What changes is **how it talks to the user**: token-by-token streaming, mid-response **interrupt/redirect**, and reconnect that **rehydrates the same conversation thread**.

Tech lead note (RFI → ticket):

> Build the channel so the agent's response arrives **token by token**, and the user can **interrupt mid-response and redirect** without waiting for completion. The channel must be **bidirectional**, tokens must stream as generated, and interruption must **genuinely abort** ongoing generation — not ignore the response once it arrives.

### Core acceptance criteria (non-negotiable)

1. **Bidirectional channel** — client sends messages and abort signals while server streams tokens.
2. **Token streaming** — assistant text arrives as **`token_chunk`** events, not one blob at end.
3. **Abort** — interrupt **stops** further tokens for that generation; partial message **kept** and marked **interrupted**; next reply is a **new turn**.
4. **Reconnect** — same **`session_id`** restores transcript + checkpoint thread (not empty chat).
5. **Pub/sub decoupling** — agent producer separated from WebSocket consumers; in-memory OK for v1.
6. **Named structured events** — not a generic message type.
7. **Field names** — match **`ChatSession`** / wire contract in §2–§3.

### Implicit requirements (identify in PR)

- SSE (Part 1) is **not enough** — client must talk back while server keeps sending data.
- Token streaming and **abort** must coexist on the same channel without stepping on each other.
- Connection must recover like Part 1, but **in both directions** — reattach to the **same chat thread**.

---

## §1 Introduction

Part 2 adds a **real-time chat transport** for the existing **Manager support agent** on **`/support`**. The LangGraph workflow, tools, guardrails, and memory store remain unchanged — only **orchestration, persistence, and UI** around streaming change.

**Agent identity (locked):** expose the existing support graph as **`agent_id: manager_support`**.

**Transport split (permanent for Milestone 10):**

| Surface | Transport |
| ------- | --------- |
| RFP dashboard `/rfp` | **SSE** (Part 1) |
| Support chat `/support` | **WebSocket** (Part 2) |

---

## §2 Chat entities (locked)

Authority: course Part 2 entity names; aligned with existing **`thread_id`** checkpoint usage in `agent/graph.py`.

### 2.1 ID model

| Lock | Rule |
| ---- | ---- |
| **`session_id`** | Primary chat identifier (UUID string) |
| **LangGraph `thread_id`** | **Same value as `session_id`** |
| Wire + WS URL | Use **`session_id`** |
| Checkpointer | Keyed by **`session_id`** / `thread_id` |

### 2.2 ChatSession (Postgres — `agent_chat_sessions`)

| Field | Type | Notes |
| ----- | ---- | ----- |
| **`session_id`** | string (PK) | UUID |
| **`agent_id`** | string | **`manager_support`** |
| **`user_id`** | int | Owner; from JWT |
| **`location_id`** | int \| null | **Nullable** at create |
| **`status`** | string | **`active` \| `interrupted` \| `closed`** |
| **`created_at`** | datetime | UTC |

### 2.3 ChatMessage (Postgres — `agent_chat_messages`)

| Field | Type | Notes |
| ----- | ---- | ----- |
| **`message_id`** | string (PK) | **Server-minted UUID v4** (canonical string form, 36 chars) |
| **`session_id`** | string (FK) | → `agent_chat_sessions` |
| **`role`** | string | **`user` \| `assistant`** |
| **`content`** | text | Accumulated visible text |
| **`status`** | string | **`complete` \| `interrupted` \| `streaming`** |
| **`sequence`** | int | Last token sequence for assistant stream |
| **`created_at`** | datetime | UTC |

User messages always persist with **`status: complete`**.

### 2.4 Schema bootstrap (locked)

| Lock | Choice |
| ---- | ------ |
| Pattern | **`ensure_agent_chat_schema(session)`** in `agent/chat_models.py` |
| Startup | Call from **`main.py`** alongside `ensure_rfp_schema` |
| Tests | Call in WS test fixtures |
| Alembic | **Not used in v1** (repo convention) |

### 2.5 Session access (locked)

| Lock | Rule |
| ---- | ---- |
| Connect | **Owner-only** — JWT **`user_id`** must match `agent_chat_sessions.user_id` |
| **Session row create** | On **first successful WS connect** for a client-minted **`session_id`** — call **`create_session_on_connect()`** in `chat_repository.py` (idempotent upsert on reconnect) |
| Multi-tab | **Same user**, multiple WebSocket connections on one `session_id` |
| Cross-user supervisor | **Out of scope v1** |
| Reject | Close socket / **4403** if session owned by another user |

### 2.6 Authority / supersession

| Source | Rule |
| ------ | ---- |
| context-23 P1 “client unchanged `{ question → answer }`” | **Superseded for `/support` transport only** |
| **`POST /agent/query`** | **Keep** for regression tests — UI uses WebSocket |
| Part 1 SSE | **Do not modify** on this branch |
| LangGraph SQLite checkpoint | **Unchanged** — separate from Postgres UI transcript |

---

## §3 WebSocket contract (locked)

### 3.1 Endpoint & routing

| Layer | Path |
| ----- | ---- |
| FastAPI | **`WS /agent/chat/ws`** |
| Browser (default) | **`WS /api/agent/chat/ws`** |
| Direct API (`NEXT_PUBLIC_AGENT_API_BASE_URL`) | **`WS {base}/agent/chat/ws`** |

**Query params (handshake — required):**

| Param | Purpose |
| ----- | ------- |
| **`session_id`** | Binds socket to conversation |
| **`access_token`** | JWT — browsers cannot set `Authorization` on WebSocket upgrade |

Use **`ws:`** on localhost, **`wss:`** when page is HTTPS. Document query-token tradeoff; prefer short-lived access tokens.

### 3.2 Frame format

Each WebSocket **text** message is JSON:

```json
{ "event": "<name>", "data": { ... } }
```

**Do not** use a single generic `message` type.

### 3.3 Server → client events

| Event | When | Required `data` keys |
| ----- | ---- | -------------------- |
| **`session_sync`** | Immediately after connect / reconnect | **`session_id`**, **`messages`** |
| **`token_chunk`** | During generation | **`session_id`**, **`message_id`**, **`token`**, **`sequence`** |
| **`generation_completed`** | Turn finished | **`session_id`**, **`message_id`** |
| **`generation_interrupted`** | Abort succeeded | **`session_id`**, **`message_id`** |
| **`error`** | Failure | **`session_id`**, **`code`**, **`message`** |

### 3.4 `session_sync.messages[]` item shape (locked)

Each element:

| Field | Type |
| ----- | ---- |
| **`message_id`** | string (UUID v4) |
| **`role`** | `user` \| `assistant` |
| **`content`** | string |
| **`status`** | `complete` \| `interrupted` \| `streaming` |
| **`created_at`** | string (ISO 8601 UTC) |

Order: **oldest → newest**. Client **replaces** local message list from this frame before handling new tokens. Empty `messages: []` is valid.

On reconnect mid-stream: include in-progress assistant row as **`streaming`** with content so far; resume **`token_chunk`** with continued **`sequence`**.

### 3.5 Client → server events

| Event | When | Required `data` keys |
| ----- | ---- | -------------------- |
| **`user_message`** | User sends chat (idle / not streaming) | **`session_id`**, **`content`** |
| **`interrupt_requested`** | User redirects mid-stream | **`session_id`**, **`new_input`** |

### 3.6 Example frames

```json
{"event":"session_sync","data":{"session_id":"550e8400-e29b-41d4-a716-446655440000","messages":[]}}
{"event":"token_chunk","data":{"session_id":"550e8400-e29b-41d4-a716-446655440000","message_id":"7c9e6679-7425-40de-944b-e07fc1f90ae7","token":"For","sequence":12}}
{"event":"interrupt_requested","data":{"session_id":"550e8400-e29b-41d4-a716-446655440000","new_input":"wait, I asked about the Miami location"}}
{"event":"generation_interrupted","data":{"session_id":"550e8400-e29b-41d4-a716-446655440000","message_id":"7c9e6679-7425-40de-944b-e07fc1f90ae7"}}
{"event":"generation_completed","data":{"session_id":"550e8400-e29b-41d4-a716-446655440000","message_id":"7c9e6679-7425-40de-944b-e07fc1f90ae7"}}
```

---

## §4 Architecture (locked)

### 4.1 Pub/sub per session

- Channel namespace: **`chat.<session_id>`**
- **In-memory** subscriber registry (single uvicorn worker; **Redis** = future scale note only)
- **One orchestrator per `session_id`** runs/cancels generation
- WebSocket handlers **subscribe only** — **never** invoke graph directly
- Multiple connections (same owner): **one agent run**, fan-out **`token_chunk`** to all subscribers

### 4.2 Turn pipeline (orchestrator)

1. Receive **`user_message`** or **`interrupt_requested`**
2. If **`user_message`** while turn busy (and not streaming interrupt path) → **`error`** code **`turn_in_progress`**
3. If streaming → **cancel** LLM stream task → persist partial → **`generation_interrupted`**
4. Persist user message
5. **`graph.invoke()`** unchanged (routing/tools/guardrails/memory)
6. **Short-circuit paths** (refuse, fallback, memory ack): chunk final **`answer`** → **`generation_completed`** (see §4.3)
7. **Live LLM paths**: cancellable **`stream=True`** task → **`token_chunk`** → **`generation_completed`**
8. Publish all events via session pub/sub

**Do not use LangGraph `interrupt()` for stream abort** — that is RFP approval HITL only.

### 4.3 Streaming vs structured JSON (locked)

| Path | Behavior |
| ---- | -------- |
| **`answer` already in state** after `graph.invoke()` | Emit **`token_chunk`** as word-sized or single chunk(s), then **`generation_completed`** |
| **Live LLM prose** | **`stream=True`** on new helpers in `generation.py` (same prompts as `generate_node`) |
| **Structured JSON completions** | **Parse first**; stream/publish **decoded user-visible answer text only** |
| **Never** | Stream raw JSON (`{"answer":...`) to the client |

### 4.4 Abort semantics (locked)

| Lock | Rule |
| ---- | ---- |
| Mechanism | **`asyncio.Task.cancel()`** on active LLM stream task |
| Partial message | **Kept** in DB + UI; **`status: interrupted`** |
| Further tokens | **None** for that **`message_id`** after abort |
| Next turn | **New** **`message_id`**; **`graph.invoke()`** with new question — do not overwrite interrupted row |

### 4.5 Reconnect (locked)

- Client: exponential backoff (1s → 2s → 4s … cap **30s**), same **`session_id`** + **`access_token`**
- Server: first frame **`session_sync`** from Postgres messages
- Graph checkpoint: same **`session_id`** as LangGraph **`thread_id`**

### 4.6 Concurrency (locked)

| Lock | Rule |
| ---- | ---- |
| Active turns | **At most one** per `session_id` |
| Overlapping **`user_message`** | **`error: turn_in_progress`** |
| Submit while assistant **`streaming`** | **`interrupt_requested`** (not parallel run) |
| Queue / parallel turns | **Not in v1** |

---

## §5 Backoffice UI (locked)

| Topic | Choice |
| ----- | ------ |
| Page | **`/support`** only |
| Client module | **`uis/backoffice/lib/agent-chat-ws.ts`** |
| REST client | Keep **`lib/agent.ts`** (`POST /agent/query`) for regression |
| WS URL helper | **`resolveAgentChatWsUrl(sessionId, accessToken)`** |
| Session storage | **`sessionStorage`** key **`brasaland_support_session_id`** |
| Message model | Role-based list with **`streaming` / `complete` / `interrupted`** |
| Streaming UX | Append **`token_chunk`** to active assistant bubble |
| Interrupt | Form submit while **`streaming`** → **`interrupt_requested`** |
| Partial message | Visible + interrupted styling — **no overwrite** |
| Connection UX | **Live / Reconnecting…** badge |
| Memory coaching | Keep **`support-memory-coaching.ts`** on message list |
| New conversation | Mint new **`session_id`**; optional mark prior session **`closed`** |

---

## §6 Out of scope (Part 2)

| Topic | Notes |
| ----- | ----- |
| New agent / tools / memory schema | **Forbidden** |
| Graph node/edge changes | **Forbidden** |
| RFP SSE / `/rfp` changes | **Forbidden** |
| Redis / multi-worker pub/sub | Future note only |
| LangGraph **`interrupt()`** for chat abort | **Forbidden** |
| Shared `realtime/` package | **Not in v1** |
| Cross-user shared sessions | **Not in v1** |
| Optional extras beyond rubric | **Skip** |

---

## §7 PR design questions — locked answers

Document these verbatim in the Part 2 PR description.

### Q1 — Why WebSockets instead of Part 1 SSE?

> Part 1 only needed **server → client** RFP alerts (`rfp_ticket_created`). Support chat needs a **bidirectional** channel: the client sends **`user_message`** and **`interrupt_requested`** while the server is still streaming **`token_chunk`** events. SSE cannot send client commands on the same live connection; abort requires cancelling the server generation task, not ignoring a completed HTTP response. WebSockets fit; RFP notifications stay on SSE.

### Q2 — Multiple clients on the same chat session?

> Each **`session_id`** has one **orchestrator** that owns the active generation task. WebSocket connections are **subscribers only** to an in-memory **`chat.<session_id>`** channel. When tokens are produced, the orchestrator **publishes once** and every connected client receives the same events — **no duplicate agent invocations**. In v1, multiple clients means **the same owner, multiple tabs**.

### Q3 — Stream abort vs LangGraph `interrupt()`?

> **Stream abort** cancels the active **LLM streaming task** and stops **`token_chunk`** for that **`message_id`**. The partial assistant message stays in the transcript with **`interrupted`** status. **LangGraph `interrupt()` is not used** for chat (reserved for RFP approval HITL). After abort, **`interrupt_requested`** starts a **new assistant turn** (new **`message_id`**) via a fresh **`graph.invoke()`** + stream — the interrupted message is not overwritten.

---

## §8 Locked decisions — master register

### Scope and branch (M10-P2-S)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M10-P2-S1** | Branch scope | Agent transport + chat persistence + `/support` UI only |
| **M10-P2-S2** | PR isolation | Separate branch/PR from Part 1 SSE |
| **M10-P2-S3** | Shared realtime lib | **No** in v1 |
| **M10-P2-S4** | REST fallback | Keep **`POST /agent/query`**; UI uses WebSocket |
| **M10-P2-S5** | Context file | **`context-28-milestone-10-real-time-systems-websocket-chat-streaming-p2.md`** before code |
| **M10-P2-S6** | Branch base | **`main` after Part 1 merges** |

### Entities (M10-P2-E)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M10-P2-E1** | Session ID | **`session_id` = LangGraph `thread_id`** |
| **M10-P2-E2** | Tables | **`agent_chat_sessions`**, **`agent_chat_messages`** |
| **M10-P2-E3** | `agent_id` | **`manager_support`** |
| **M10-P2-E4** | `location_id` | **Nullable** at create |
| **M10-P2-E5** | Session access | **Owner-only** (`user_id`) |
| **M10-P2-E6** | `session_sync` | Ordered **`messages[]`** with locked item shape |
| **M10-P2-E7** | Session create | **`create_session_on_connect()`** on first successful WS connect (idempotent reconnect) |
| **M10-P2-E8** | `message_id` | **Server-minted UUID v4** via **`new_message_id()`** — never client-supplied |

### Transport (M10-P2-T)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M10-P2-T1** | Endpoint | **`WS /agent/chat/ws`** |
| **M10-P2-T2** | Proxy | **`/api/agent/chat/ws`** |
| **M10-P2-T3** | Auth | JWT **`access_token`** query param |
| **M10-P2-T4** | Wire | JSON **`{ event, data }`** named events |
| **M10-P2-T5** | Pub/sub | In-memory **`chat.<session_id>`** |
| **M10-P2-T6** | Agent runs | **Orchestrator only** — not per-socket |
| **M10-P2-T7** | Streaming | **`graph.invoke()`** + cancellable LLM **`stream=True`** |
| **M10-P2-T8** | Abort | Task cancel — **not** LangGraph **`interrupt()`** |
| **M10-P2-T9** | JSON answers | User-visible text only — never raw JSON chunks |
| **M10-P2-T10** | Concurrency | **`turn_in_progress`** error; interrupt wins |
| **M10-P2-T11** | Router mount | **`agent_chat_router`** at **`/agent`** **without** `_protected` — WS uses query **`access_token`**, not bearer dependency |

### UI (M10-P2-U)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M10-P2-U1** | Tokens | Incremental append — not end-of-turn swap |
| **M10-P2-U2** | Interrupt | Form submit while **`streaming`** |
| **M10-P2-U3** | Reconnect | Backoff + **`session_sync`** rehydrate |
| **M10-P2-U4** | Connection badge | **Live / Reconnecting…** |
| **M10-P2-U5** | Coaching | Keep memory coaching on message list |

### Testing (M10-P2-X)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M10-P2-X1** | Backend tests | **`services/api/tests/test_agent_chat_ws.py`** |
| **M10-P2-X2** | Frontend tests | **`uis/backoffice/tests/agent-chat-ws.test.ts`** |
| **M10-P2-X3** | Manual | Stream, abort, reconnect, multi-tab in PR plan |

---

## §9 Suggested file layout

| Responsibility | Location |
| -------------- | -------- |
| WS route + handshake | **`services/api/agent/chat_routes.py`** (or extend `routes.py`) |
| Session orchestrator + abort | **`services/api/agent/chat_orchestrator.py`** |
| In-memory pub/sub | **`services/api/agent/chat_pubsub.py`** |
| DB models + `ensure_agent_chat_schema` | **`services/api/agent/chat_models.py`** + repository |
| Session create on connect | **`create_session_on_connect()`** in **`chat_repository.py`** (called from **`chat_routes.py`**) |
| Router registration | **`services/api/main.py`** — import **`agent.chat_models`**, **`ensure_agent_chat_schema`** in lifespan, mount **`agent_chat_router`** at **`/agent`** without **`_protected`** |
| Stream helpers (add only) | **`services/api/agent/generation.py`** |
| WS client | **`uis/backoffice/lib/agent-chat-ws.ts`** |
| UI | **`uis/backoffice/app/support/page.tsx`** |
| Tests | **`test_agent_chat_ws.py`**, **`agent-chat-ws.test.ts`** |

**Do not touch:** `services/api/rfp/sse.py`, agent graph nodes/edges, tools, memory store logic.

**Do not create** a shared `realtime/` package on this branch.

---

## §10 Implementation phases

### Phase 1 — Backend core

1. **`ensure_agent_chat_schema`** + repositories
2. **`chat_pubsub.py`** — `chat.<session_id>` fan-out
3. **`chat_orchestrator.py`** — turn pipeline, abort, streaming
4. **`WS /agent/chat/ws`** — auth, owner check, **`session_sync`**
5. Stream helpers in **`generation.py`**
6. **`services/api/tests/test_agent_chat_ws.py`**

### Phase 2 — Frontend client

1. **`uis/backoffice/lib/agent-chat-ws.ts`** — connect, parse, backoff, reducers
2. Refactor **`app/support/page.tsx`** — tokens, interrupt, Live badge
3. **`uis/backoffice/tests/agent-chat-ws.test.ts`**

### Phase 3 — Manual verification + PR

1. Run pytest + vitest
2. Manual: tokens stream incrementally
3. Manual: interrupt mid-stream → partial kept → new turn
4. Manual: offline → online → **`session_sync`** restores thread
5. Manual: two tabs same session → same tokens
6. Paste **§7 PR design questions** into PR body

---

## §11 Testing specification

### Automated — `services/api/tests/test_agent_chat_ws.py`

| Test | Assert |
| ---- | ------ |
| `test_agent_chat_ws_requires_auth` | Missing/invalid token → connection rejected |
| `test_agent_chat_ws_owner_only` | Wrong `user_id` for `session_id` → rejected |
| `test_agent_chat_ws_event_wire_format` | Frames match `{event, data}` + required keys |
| `test_token_chunk_sequence_increments` | `sequence` monotonic per `message_id` |
| `test_interrupt_stops_token_chunks` | After `interrupt_requested`, no more chunks for that `message_id` |
| `test_generation_interrupted_partial_persisted` | Partial content + `interrupted` status in DB |
| `test_session_sync_on_connect` | Reconnect payload includes prior messages |
| `test_pubsub_fanout_single_run` | Two subscribers → same events, one orchestrator/LLM mock call |
| `test_turn_in_progress_error` | Overlapping `user_message` → `error` |

Mock LLM stream in CI — do not require live OpenAI.

### Automated — `uis/backoffice/tests/agent-chat-ws.test.ts`

| Test | Assert |
| ---- | ------ |
| WS URL | **`resolveAgentChatWsUrl`** → `/api/agent/chat/ws` same-origin |
| Frame parser | Handles `token_chunk`, `generation_interrupted`, `session_sync` |
| Reducer | Appends tokens; marks interrupted; replaces on sync |

### Manual — PR test plan checklist

- [ ] Assistant text appears **token by token**, not all at once
- [ ] Submit new message mid-stream → **no further tokens** from old generation; partial row **interrupted**; new answer is **new bubble**
- [ ] DevTools offline → online → **Reconnecting…** → **`session_sync`** → conversation restored
- [ ] Two tabs, same user, same **`session_id`** → both receive same **`token_chunk`** events
- [ ] Invalid/missing token → WebSocket rejected

---

## §12 Evaluation criteria mapping

Official rubric → implementation mapping:

| Criterion | Satisfied by |
| --------- | ------------ |
| Chat shows response tokens as they’re generated | **`token_chunk`** + LLM **`stream=True`** (§4.3); short-circuit paths chunk final answer |
| Interrupt mid-response aborts generation; partial kept; next turn reflects new input | §4.4 abort + **`generation_interrupted`** + new **`message_id`** (M10-P2-T8, M10-P2-U2) |
| WebSocket reconnects with same **`session_id`** / thread; thread not lost | **`session_sync`** + same checkpoint key (§4.5, M10-P2-E1) |
| Events named and structured between agent, pub/sub, and clients | §3 wire contract (M10-P2-T4) |
| Field and entity names match Part 2 | §2 entities (M10-P2-E*) |
| Pub/sub decoupling evaluated | §4.1 orchestrator + **`chat.<session_id>`** (M10-P2-T5, M10-P2-T6) |

---

## §13 Golden rules

- Thin WS handlers; orchestration in **`chat_orchestrator.py`**; pub/sub in **`chat_pubsub.py`**.
- **Do not** change Support Agent graph/tools/memory logic.
- **Do not** modify Part 1 RFP SSE on this branch.
- **Do not** use LangGraph **`interrupt()`** for chat stream abort.
- **Do not** stream raw model JSON to the client.
- Package installs (if any): **`cd services/api && uv add …`** only.
- Precedence: **this file + live code** over course marketing copy when they conflict.

---

## §14 Backend implementation notes

### Orchestrator sketch

```python
# chat_orchestrator.py — responsibilities only

async def handle_user_message(session_id: str, content: str, user_id: int) -> None: ...
async def handle_interrupt(session_id: str, new_input: str, user_id: int) -> None: ...
async def _run_turn(session_id: str, question: str, ...) -> None:
    # 1. graph.invoke(...) — unchanged
    # 2. if answer in state: chunk + generation_completed
    # 3. else: asyncio.Task(stream_llm(...)) with cancel support
    # 4. publish via chat_pubsub.publish(session_id, frame)
```

### Pub/sub sketch

```python
# chat_pubsub.py — mirror rfp/sse.py pattern, different module

class AgentChatPubSub:
    async def subscribe(self, session_id: str) -> asyncio.Queue[str]: ...
    async def unsubscribe(self, session_id: str, queue: asyncio.Queue[str]) -> None: ...
    def publish(self, session_id: str, frame: str) -> None: ...
```

### WebSocket auth sketch

```python
# Validate access_token query param with decode_access_token + get_user_record
# Load session; assert session.user_id == current_user.id
# create_session_on_connect(session_id, user_id)  # first connect only; idempotent on reconnect
# Emit session_sync as first outbound frame
```

### `main.py` router registration (locked)

```python
# HTTP agent routes keep bearer auth via _protected:
app.include_router(agent_router, prefix="/agent", dependencies=_protected)
# WebSocket chat must NOT use _protected (OAuth2 bearer fails WS upgrade):
app.include_router(agent_chat_router, prefix="/agent")
# Register ORM + schema bootstrap alongside ensure_rfp_schema:
import agent.chat_models  # noqa: F401
ensure_agent_chat_schema(session)
```

---

## §15 Frontend implementation notes

### `agent-chat-ws.ts` requirements

- Build URL via **`resolveAgentChatWsUrl(sessionId, getAccessToken())`**
- Protocol **`ws`/`wss`** from `window.location.protocol`
- Parse JSON frames; dispatch by **`event`**
- Exponential backoff reconnect (cap 30s)
- On reconnect: same **`session_id`**; apply **`session_sync`** (replace messages)

### Support page requirements

- Replace **`askSupportAgent`** POST flow with persistent WS while on page
- **`aria-live="polite"`** on streaming assistant bubble
- Interrupted rows: distinct border/background (similar visual language to RFP arrival highlight)
- **Live / Reconnecting…** in header when WS connected

---

## Changelog

| Date | Change |
| ---- | ------ |
| 2026-08-07 | Initial spec locked from Context 28 Part 2 decision walkthrough (Decisions 1–7, 8a–8g) |
| 2026-08-07 | Mechanical locks: **`create_session_on_connect`**, **`message_id` = UUID v4**, **`main.py`** router registration note (M10-P2-E7/E8/T11) |
