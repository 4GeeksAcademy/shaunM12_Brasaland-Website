# Context 28 — Milestone 10 Real-Time Systems: SSE Notifications (Part 1)

**Ticket:** Milestone 10 Part 1 — Real-time RFP ticket notifications via Server-Sent Events  
**Type:** FastAPI SSE endpoint + in-memory pub/sub + backoffice `/rfp` UI + tests  
**Branch:** `milestone-10-real-time-systems-sse-p1`  
**Status:** Spec locked — ready for implementation  
**Depends on:** [context-27-milestone-9-rfp-intake-routing-p1.md](./context-27-milestone-9-rfp-intake-routing-p1.md) (RFP entities, `/rfp` API, `/rfp` UI), [context-22-route-conventions.md](./context-22-route-conventions.md) (routing/proxy/casing), root [`CONTEXT.md`](../../CONTEXT.md) (company identity only)  
**Companion (Part 2 — separate branch):** Context 28 Part 2 — WebSocket chat streaming for Support Agent (**not Part 1 scope**)  
**Stakeholders:** Camila Ospina (Marketing — process owner); Brasaland Digital backoffice users

> **Read this file before Part 1 implementation.** Part 2 is a separate branch and must not be mixed into this PR.

---

## Ticket brief (Part 1)

Every RFP that comes in is money on the table, and right now nobody finds out until they open the dashboard on their own. Part 1 adds a **communication layer** so the backoffice RFP dashboard shows new tickets **without manual refresh**, and reconnects gracefully after a dropped connection.

Tech lead note:

> This deliverable requires **no calls to a model or agent**. It is a notification layer on top of the existing RFP system — not a redesign of intake, generation, or approval.

Manager brief (locked intent):

> The screen should show a new RFP ticket by itself the moment it is registered. If someone's connection drops, it should reconnect without reloading the page.

### Core acceptance criteria (Part 1 — non-negotiable)

1. **SSE endpoint** — emits a named event every time a new RFP ticket is **successfully registered** (`POST /rfp/tickets` → 201).
2. **Named event + structured payload** — `event: rfp_ticket_created` with JSON `data` including **`ticket_id`** and **`status`** (not a generic `message` type).
3. **SSE headers + keep-alive** — `Content-Type: text/event-stream`; comment keep-alive frames so the connection does not close prematurely.
4. **JWT protection** — same auth as backoffice; unauthenticated clients must not receive events; client uses **`fetch` + ReadableStream** with `Authorization: Bearer` (not bare `EventSource`).
5. **Dashboard real-time UX** — `/rfp` shows new tickets without manual reload; notification is **visually distinguishable** from ordinary table data.
6. **Reconnection** — progressive backoff on disconnect; **refetch-then-SSE** recovery; **no duplicate** rows for the same `ticket_id`.
7. **Tests** — assert `text/event-stream`, named `event:`, and JSON `data` shape on the wire (not a detached dict unit test).
8. **No AI in Part 1** — no model or agent calls anywhere in this part's implementation.

### Implicit requirements (identify in PR)

- The notification must be **distinguishable** from other dashboard data (not a silent row update).
- It must indicate **which ticket arrived** and that it **needs processing** (`status: analyzing`).
- The client must **not silently stop notifying** when the connection drops — show reconnect state and recover missed tickets.

---

## §1 Introduction

Reuse the **existing Milestone 9 RFP system** unchanged in scope: same entities, same field names, same `/rfp` routes for CRUD and intake. Part 1 adds **server-push notifications** on top.

**Audience:** Camila Ospina's team (Marketing and Digital Experience) watching **`/rfp`**.

**Course wording:** Spec text may say "Sales team"; **owner = Marketing (Camila)** per context-27.

---

## §2 RFP entities (reuse — do not rename)

Authority: [context-27-milestone-9-rfp-intake-routing-p1.md](./context-27-milestone-9-rfp-intake-routing-p1.md) §4.

| Entity | Relevant fields for SSE |
| ------ | ------------------------ |
| **`rfp_tickets`** | `ticket_id`, `status`, `metadata`, `created_at`, `updated_at` |

**ID lock:** Use **`ticket_id`** (UUID string) only — **no `rfp_id`**. The course example JSON may show `rfp_id`; **live code and M9 spec win**.

**Metadata keys** (when present on ticket): `client_name`, `location`, `service_type`, `scope`, `deadline`, `budget_range`, `departments_needed`.

---

## §3 SSE event contract (locked)

### 3.1 Event name

| Wire | Value |
| ---- | ----- |
| SSE `event:` | **`rfp_ticket_created`** |

### 3.2 Payload (`data:` JSON)

Required keys on every emit:

| Field | Type | Notes |
| ----- | ---- | ----- |
| `ticket_id` | string | Primary identifier |
| `status` | string | **`analyzing`** at registration emit |
| `created_at` | string (ISO 8601 UTC) | From ticket row |

Optional keys (include in schema; **nullable** until intake extracts metadata):

| Field | Type |
| ----- | ---- |
| `client_name` | string \| null |
| `location` | string \| null |
| `service_type` | string \| null |

Do **not** include: full PDF content, per-department sections, trace events, `status_label`.

### 3.3 Example wire frame

```text
event: rfp_ticket_created
data: {"ticket_id":"550e8400-e29b-41d4-a716-446655440000","status":"analyzing","created_at":"2026-07-24T14:32:00Z","client_name":null,"location":null,"service_type":null}

: keep-alive

```

### 3.4 When to emit (locked)

| Moment | Emit? |
| ------ | ----- |
| Successful **`POST /rfp/tickets`** (201, PDF stored, `status: analyzing`) | **Yes — once** |
| Intake completes (`intake_complete`, `discarded`, `failed`) | **No** |
| Failed upload / storage error | **No** |
| Ticket deleted | **No** |

**Rationale:** Notification = "work item registered." Metadata backfills via existing `GET /rfp/tickets` / detail. Course example with full metadata describes post-intake richness; emit timing follows **registration**.

---

## §4 Architecture (locked)

### 4.1 Connection model

- **Each browser tab** opens its **own independent** authenticated SSE connection.
- Server uses a **shared in-process broadcaster** (subscriber registry) so one publish fan-outs to all connections.
- **Single uvicorn worker** assumed for course/local dev; **Redis pub/sub** documented as future horizontal scale-out only.

### 4.2 Recovery model

**Strategy: refetch-then-SSE** (not Last-Event-ID replay in v1).

On reconnect after backoff:

1. `GET /rfp/tickets` (same filters as dashboard).
2. Merge rows by **`ticket_id`** using client **`Set<ticket_id>`** dedupe.
3. Reopen SSE stream for live events.

Do **not** refetch the full list on every SSE event.

### 4.3 Why SSE, not WebSockets (PR answer — locked)

| Need | Tool |
| ---- | ---- |
| Server → client "ticket arrived" alert | **SSE** |
| JWT via custom headers on long-lived stream | **`fetch` + ReadableStream** |
| User actions (upload, open, delete) | **Existing REST** (`/rfp/tickets`) |
| Bidirectional same-channel while streaming (interrupt, chat tokens) | **WebSockets (Part 2)** |

WebSockets become appropriate when the client must **send data on the same live channel** while the server is still streaming — e.g. interrupting an agent mid-response. That is Part 2 scope, not Part 1.

### 4.4 Call chain

```text
POST /rfp/tickets
  → services/api/rfp/routes.py::create_rfp_ticket
  → create_ticket_analyzing + store PDF + commit
  → services/api/rfp/sse.py::publish_rfp_ticket_created(ticket)
  → in-memory broadcaster fan-out
  → all GET /rfp/events/stream subscribers receive event
  → background_tasks.add_task(run_intake_background_task)
  → return 201

GET /rfp/events/stream
  → services/api/rfp/routes.py (or sse.py router)
  → JWT via get_current_user
  → StreamingResponse(text/event-stream)
  → subscribe to broadcaster; write event: + data: frames + keep-alive comments
```

**Publish hook lock:** Emit **only** from the successful create route **after** DB persistence — **never** from repository, intake graph, or background intake task.

---

## §5 HTTP and routing (locked)

| Layer | Path |
| ----- | ---- |
| FastAPI | **`GET /rfp/events/stream`** |
| Browser (proxy) | **`GET /api/rfp/events/stream`** |
| Auth | **`Depends(get_current_user)`** — 401 without JWT |
| Mount | Existing `app.include_router(rfp_router, prefix="/rfp", dependencies=_protected)` |

**Client:** `uis/backoffice/lib/rfp-sse.ts` (new) using **`authorizedFetch`** from `lib/http.ts` — **not** `EventSource`.

**Response headers (minimum):**

- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`

**Keep-alive:** SSE comment lines `: keep-alive\n\n` every **15–30 seconds**.

**No `id:` field** in v1 (recovery is refetch-based, not Last-Event-ID).

---

## §6 Dashboard UI behavior (locked)

File: `uis/backoffice/app/rfp/page.tsx`

| Behavior | Lock |
| -------- | ---- |
| SSE | Insert/highlight **new** ticket; show toast/banner ("New RFP ticket — needs processing") |
| Full refetch | **Not** on every SSE event |
| Polling | **Keep** existing 5s `shouldPollRfpTicketList` poll for **in-flight status** updates |
| Refresh button | **Keep** as manual fallback |
| Dedupe | Client **`Set<ticket_id>`** on SSE handler and refetch merge |
| Connection UX | **Live** / **Reconnecting…** indicator; progressive backoff on drop |
| Distinguishable | Row highlight + notification chrome — not indistinguishable table refresh |

---

## §7 Optional notifications — out of scope

Do **not** implement in Part 1:

- `sales_drop_alert`
- `location_inactivity_alert`
- Agent escalation events

Part 1 delivers **`rfp_ticket_created` only**.

---

## §8 Out of scope (Part 1)

| Topic | Notes |
| ----- | ----- |
| Model / agent calls | **Forbidden** in Part 1 |
| WebSockets | Part 2 |
| Support Agent / `/support` | No changes |
| Last-Event-ID server replay buffer | Use refetch-then-SSE |
| Unified notifications hub | `/rfp` only |
| New RFP intake logic | Reuse context-27 |
| Optional SSE event types | Skipped |
| Redis backplane | Document as future scale note only |

---

## §9 Authority / supersession

| Source | Rule |
| ------ | ---- |
| context-27 §4 | **`ticket_id` only**; metadata field names |
| context-22 | Bare FastAPI `/rfp/*`; browser `/api/rfp/*`; snake_case API |
| context-27 M9-H7 | Intake stays async via `BackgroundTasks` — SSE does not replace poll on detail page |
| Course example `rfp_id` | **Superseded** by M9 `ticket_id` lock |
| Part 2 WebSocket chat | **Separate branch** — do not implement here |

---

## Locked decisions — master register

### Scope and branch (M10-P1-S)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M10-P1-S1** | Branch scope | RFP SSE only; **no** Support Agent / WebSocket files |
| **M10-P1-S2** | PR isolation | Separate branch/PR from Part 2 |
| **M10-P1-S3** | Optionals | **Skip all** optional alert event types |

### Entities and payload (M10-P1-E)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M10-P1-E1** | Primary ID | **`ticket_id` only** — no `rfp_id` |
| **M10-P1-E2** | Event name | **`rfp_ticket_created`** |
| **M10-P1-E3** | Required `data` keys | **`ticket_id`, `status`, `created_at`** |
| **M10-P1-E4** | Optional `data` keys | **`client_name`, `location`, `service_type`** — nullable at registration |
| **M10-P1-E5** | Payload shape | Flat keys in `data` (not nested `metadata: {}`) |
| **M10-P1-E6** | `status_label` | **Not in SSE** — UI uses existing list helpers |

### Emit and publish (M10-P1-P)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M10-P1-P1** | Emit timing | Once on successful **`POST /rfp/tickets`** |
| **M10-P1-P2** | Status at emit | **`analyzing`** |
| **M10-P1-P3** | Publish location | **`routes.py` after commit**, before intake background task |
| **M10-P1-P4** | Publish module | **`services/api/rfp/sse.py`** |
| **M10-P1-P5** | Failed create | **No emit** |

### SSE transport (M10-P1-T)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M10-P1-T1** | Endpoint | **`GET /rfp/events/stream`** |
| **M10-P1-T2** | Proxy | **`/api/rfp/events/stream`** |
| **M10-P1-T3** | Client | **`fetch` + ReadableStream** + Bearer JWT |
| **M10-P1-T4** | Fan-out | Independent connections; **in-memory broadcaster** |
| **M10-P1-T5** | Keep-alive | Comment frames every **15–30s** |
| **M10-P1-T6** | Recovery | **Refetch-then-SSE**; dedupe **`Set<ticket_id>`** |
| **M10-P1-T7** | Last-Event-ID | **Not used** in v1 |

### UI (M10-P1-U)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M10-P1-U1** | SSE UX | Insert/highlight + toast; no full refetch per event |
| **M10-P1-U2** | Polling | **Keep** 5s status poll when `shouldPollRfpTicketList` |
| **M10-P1-U3** | Refresh | **Keep** manual button |
| **M10-P1-U4** | Reconnect UI | **Live / Reconnecting…** indicator |

### Testing (M10-P1-X)

| ID | Topic | Choice |
| -- | ----- | ------ |
| **M10-P1-X1** | Test file | **`services/api/tests/test_rfp_sse.py`** |
| **M10-P1-X2** | Wire tests | Headers, `event:`, `data:` JSON shape, 401, emit-on-POST |
| **M10-P1-X3** | Reconnect | Manual checklist in PR test plan |

---

## PR design questions — locked answers

Document these verbatim in the Part 1 PR description.

### Q1 — Multiple dashboard viewers

> Each dashboard client opens its **own SSE connection**. When a ticket is registered, the server **publishes once** to an in-memory subscriber registry and **every active connection** receives the same `rfp_ticket_created` event. With ~50 concurrent viewers on a single API process, this is acceptable (mostly idle connections + occasional events + keep-alive comments). For multi-worker or very large scale, we would add Redis pub/sub.

### Q2 — Recovery and deduplication

> We chose **refetch-then-SSE**. After disconnect (with exponential backoff), the client calls **`GET /rfp/tickets`**, merges by **`ticket_id`**, then reopens the SSE stream. Duplicates are prevented with a client-side **`Set<ticket_id>`** updated by both the refetch merge and SSE handler.

### Q3 — SSE vs WebSockets

> SSE fits Part 1 because Camila's team only needs a **one-way alert** that a ticket was registered. User actions stay on REST. We use **`fetch` with ReadableStream** so we can attach the same JWT as the rest of the backoffice. WebSockets would be required for **bidirectional** interaction on the same channel while data is still streaming (Part 2 support chat).

---

## Suggested file layout

| Responsibility | Location |
| -------------- | -------- |
| Broadcaster + stream handler | **`services/api/rfp/sse.py`** (new) |
| Publish hook | **`services/api/rfp/routes.py`** (`create_rfp_ticket`) |
| SSE route registration | **`services/api/rfp/routes.py`** or **`sse.py`** included from routes |
| SSE client + parser | **`uis/backoffice/lib/rfp-sse.ts`** (new) |
| Dashboard integration | **`uis/backoffice/app/rfp/page.tsx`** |
| Existing list API | **`uis/backoffice/lib/rfp.ts`** (`listRfpTickets`) |
| Tests | **`services/api/tests/test_rfp_sse.py`** (new) |

**Do not create** a shared `realtime/` package on this branch.

---

## Implementation phases

### Phase 1 — Backend SSE core

1. Add **`services/api/rfp/sse.py`**:
   - `RfpSseBroadcaster` (subscribe / unsubscribe / publish)
   - `build_rfp_ticket_created_payload(ticket) -> dict`
   - `publish_rfp_ticket_created(ticket)`
   - `async def rfp_events_stream(request)` → `StreamingResponse` with keep-alive loop
2. Register **`GET /rfp/events/stream`** on RFP router with **`get_current_user`**.
3. Call **`publish_rfp_ticket_created`** from **`create_rfp_ticket`** after successful persistence.
4. **`services/api/tests/test_rfp_sse.py`**: auth, headers, wire format, emit-on-create.

### Phase 2 — Frontend client

1. Add **`uis/backoffice/lib/rfp-sse.ts`**:
   - Parse SSE frames from `ReadableStream`
   - Backoff reconnect
   - `onTicketCreated` callback
2. Integrate in **`rfp/page.tsx`**:
   - `knownTicketIds` Set
   - Connect on mount; disconnect on unmount
   - On reconnect: refetch list → merge → resume SSE
   - Toast/highlight for new tickets
   - Live / Reconnecting indicator

### Phase 3 — Manual verification + PR

1. Run pytest `test_rfp_sse.py`.
2. Manual: open `/rfp` in two tabs; upload PDF in tab A; both show new ticket.
3. Manual: DevTools offline → upload → online → one row, no duplicate.
4. Paste **§ PR design questions** into PR body.

---

## Backend implementation notes

### `sse.py` responsibilities

```python
# services/api/rfp/sse.py — responsibilities only; not copy-paste complete

def ticket_created_payload(ticket: RfpTicket) -> dict:
    meta = ticket.metadata_json or {}
    return {
        "ticket_id": ticket.ticket_id,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat(),
        "client_name": meta.get("client_name"),
        "location": meta.get("location"),
        "service_type": meta.get("service_type"),
    }

def format_sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"

def format_keep_alive() -> str:
    return ": keep-alive\n\n"
```

### Stream handler requirements

- Subscribe on connect; unsubscribe in `finally` on disconnect.
- Loop: wait on broadcaster queue with timeout → emit keep-alive on timeout.
- Handle client disconnect (`CancelledError` / broken pipe) without crashing process.

### Thread/async note

`POST /rfp/tickets` may run sync route code; broadcaster must be safe when publish is called from sync context into async SSE tasks (use `asyncio.get_event_loop().call_soon_threadsafe` or an asyncio.Queue per subscriber created in the async stream handler).

---

## Frontend implementation notes

### SSE client requirements (`rfp-sse.ts`)

- Use **`authorizedFetch('/api/rfp/events/stream', { headers: { Accept: 'text/event-stream' } })`**.
- Read **`response.body.getReader()`**; buffer lines until `\n\n`.
- Parse `event:` and `data:` lines.
- Exponential backoff: **1s → 2s → 4s → 8s** (cap **30s**) before reconnect.
- On reconnect: caller runs **`listRfpTickets`** first, then opens stream.

### Dashboard merge pseudocode

```typescript
const knownTicketIds = useRef(new Set<string>());

function mergeTicket(ticket: RfpTicketSummary, source: "sse" | "refetch") {
  if (knownTicketIds.current.has(ticket.ticket_id)) return;
  knownTicketIds.current.add(ticket.ticket_id);
  // prepend row + showNewArrivalUi(ticket)
}
```

---

## Testing specification

### Automated — `services/api/tests/test_rfp_sse.py`

| Test | Assert |
| ---- | ------ |
| `test_rfp_sse_requires_auth` | GET stream without JWT → **401** |
| `test_rfp_sse_content_type` | Authenticated stream → **`text/event-stream`** |
| `test_rfp_ticket_created_event_shape` | After POST ticket, stream frame has **`event: rfp_ticket_created`** and **`data:`** JSON with **`ticket_id`, `status`, `created_at`** |
| `test_publish_not_on_failed_upload` | Invalid POST → **no** SSE event (if testable with concurrent stream) |

Use **`httpx`/`TestClient`** streaming response or async client pattern appropriate for SSE in your test suite.

### Manual — PR test plan checklist

- [ ] `/rfp` shows **Live** when SSE connected
- [ ] Upload PDF → new row appears **without** clicking Refresh
- [ ] New row has **visible highlight/toast** distinct from poll updates
- [ ] DevTools → Offline → create ticket (other session) → Online → **Reconnecting…** → refetch → **one** new row
- [ ] Two tabs open → ticket created → **both** tabs notified
- [ ] Anonymous/cleared token → stream returns **401**

---

## Evaluation criteria mapping

| Criterion | Satisfied by |
| --------- | ------------ |
| Dashboard shows new tickets automatically | Phase 2 UI + SSE insert |
| Reconnect + backoff + no duplicates | M10-P1-T6, M10-P1-U4, dedupe Set |
| JWT via fetch, not EventSource | M10-P1-T3 |
| Named event + structured payload + wire tests | §3, M10-P1-X |
| No model/agent calls | §8 |
| Field names match context | §2, M10-P1-E |

---

## Golden rules

- Thin HTTP; broadcaster in **`rfp/sse.py`**; **do not** emit from intake pipeline.
- **Do not** touch Support Agent (`services/api/agent/`) or `/support`.
- **Do not** implement Part 2 WebSockets on this branch.
- **Do not** use `rfp_id`.
- Package installs (if any): **`cd services/api && uv add …`** only.
- Precedence: **this file + live code** over course marketing copy when they conflict.

---

## Changelog

| Date | Change |
| ---- | ------ |
| 2026-08-07 | Initial spec locked from Context 28 Part 1 decisions |
