# CONTEXT — Brasaland · Telemetry Phase 2: Frontend Capture

## AI Engineering - 4Geeks Academy

> **Repository index:** `context-15-telemetry-frontend-capture.md`  
> **Companion docs:** `memory-bank/historical-reference/context-15-telemetry-plan.md`, `docs/telemetry/telemetry-plan.md`, `docs/telemetry/event-schemas.json`  
> **Related context:** `context-12-milestone-5-backoffice-inventory-interface.md`  
> **Type:** Frontend telemetry capture + temporary backend verification endpoint  
> **Status:** 🟢 Implemented (frontend capture + stub/storage endpoint)

> **Authority rule:** Milestone 5 contexts are the runtime source of truth. This telemetry context only adds observability and must not redefine inventory API contracts.

---

## Your Company

**Brasaland** is a grilled food restaurant chain with 14 locations across Colombia and Florida.  
You are part of **Brasaland Digital**, the internal technology team. The backoffice is used daily by location managers and operations supervisors to register ingredient supply orders and consumption orders.

This phase instruments the backoffice with the events designed in Phase 1 and verifies payload shape end-to-end before persistence is introduced.

---

## Scope of This Phase

This context defines implementation requirements for:

1. A **temporary FastAPI stub endpoint** to receive telemetry batches and confirm payload shape.
2. A centralized **TelemetryService** in the backoffice with queue, batching, retry, and unload flush behavior.
3. **Inventory and authentication flow instrumentation** through a single public `track()` function.

This phase is verification-focused. Persistence and strict server-side event validation are completed in later phases.

---

## Locked Decisions

- Event names and property keys **must match** `docs/telemetry/event-schemas.json`.
- All frontend telemetry goes through **one public function**:  
  `track(eventType: string, properties: Record<string, unknown>): void`
- Tracking must not be scattered in ad-hoc fetch/axios calls.
- Event ownership is explicit to prevent duplicates:
  - **Backend-owned (source of truth):** `supply_order_created`, `supply_order_failed`, `consumption_order_created`, `consumption_order_failed`, `stock_threshold_triggered`, `direct_stock_edit_rejected`
  - **Frontend-owned in this phase:** `ingredient_list_viewed`, `location_filter_applied`, `order_form_abandoned`, `session_expired`, `user_login_succeeded`
- Endpoint URL is configured from env on day one:
  - Backend: `TELEMETRY_ENDPOINT` (pattern established even for stub)
  - Frontend: `NEXT_PUBLIC_TELEMETRY_ENDPOINT`
- The endpoint in this phase is **temporary** and only verifies arrival/shape.
- Optional implementation switch: `TELEMETRY_PHASE_MODE=stub|storage` (`stub` for Phase 2 grading; `storage` for Phase 3 mixed-batch persistence).
- `userId` is always TinyDB UUID (never name/email).
- Inventory telemetry requires `location_id`.
- Frontend capture must avoid PII and raw error stacks.

---

## Canonical Envelope for Stub Endpoint

The backend stub accepts a batch body with shape:

```json
{ "events": [ ... ] }
```

Each event follows the Phase 1 envelope:

```python
from pydantic import BaseModel
from typing import Any
from datetime import datetime

class TelemetryEvent(BaseModel):
    eventId: str                      # UUID generated client-side
    timestamp: datetime               # ISO 8601 capture time
    sessionId: str                    # Opaque session identifier
    userId: str                       # TinyDB user UUID
    event_type: str                   # entity_action format
    schemaVersion: int                # starts at 1
    requestId: str                    # correlation identifier
    service: str                      # "backoffice"
    properties: dict[str, Any] = {}
```

---

## Phase 1 — Backend Stub Endpoint (FastAPI)

Create `POST /telemetry/events` in its own router under `services/api/`.

### Requirements

- Accept request body: `{ "events": [...] }`
- Parse each event with `TelemetryEvent`
- Log:
  - number of events in batch
  - each `event_type`
- Return:
  - `200 OK`
  - body: `{ "received": N }` where `N = len(events)`
- Read `TELEMETRY_ENDPOINT` from env (even if not used to forward traffic yet)

### Explicit non-goals (this phase)

- No Supabase write
- No warehouse write
- No per-event property allowlist enforcement (storage mode adds allowlist checks in Phase 3)
- No stream/batch routing in backend

Stub mode validates the full batch envelope strictly via `TelemetryBatch`; storage mode validates each event individually and supports mixed batches.

---

## Phase 2 — Backoffice TelemetryService

Create: `uis/backoffice/lib/telemetry.ts`

### Responsibilities

1. **Local queue**
   - Keep in-memory array of events pending send.

2. **Batch + debounce**
   - Send every 10 seconds, or
   - Immediately when queue reaches 20 events.

3. **Reliable flush on tab hide/close**
   - Use `navigator.sendBeacon` on `visibilitychange` (and optionally `pagehide`) for pending events.

4. **Retry with backoff**
   - Retry failed batch up to 3 times with exponential delay (e.g., 500ms, 1000ms, 2000ms), then discard.

5. **Automatic envelope population**
   - Auto-add: `eventId`, `timestamp`, `sessionId`, `userId`, `requestId`, `event_type`, `schemaVersion`, `service`.
   - Components must pass only `eventType` + `properties`.

### Public API (only)

```ts
track(eventType: string, properties: Record<string, unknown>): void
```

No direct telemetry fetch/axios calls from components.

---

## Phase 3 — Inventory Flow Instrumentation

Instrument these touchpoints in backoffice:

| Event | Where to call `track()` | Notes |
|---|---|---|
| `supply_order_created` | **Do not emit in frontend** | Backend emits this after commit to avoid duplicates and ensure canonical payload |
| `consumption_order_created` | **Do not emit in frontend** | Backend emits this after commit to include server-resolved fields |
| `consumption_order_failed` | **Do not emit in frontend** | Backend emits standardized failure reasons on API rejection |
| `supply_order_failed` | **Do not emit in frontend** | Backend emits validation/supplier errors as source of truth |
| `ingredient_list_viewed` | On mount of ingredient stock list | include `location_id`, `ingredient_count`, `view_source` |

### Rules

- Every call must include **only** keys allowed in Phase 1 schemas.
- No "just in case" properties.
- Never include stack traces in telemetry properties.

---

## Additional Activity — Authentication Instrumentation

Instrument in auth hooks/components (not page-by-page):

| Event | Where to call `track()` | Notes |
|---|---|---|
| `user_login_succeeded` | After successful auth response | include `location_id` and `auth_method` when available; no email/password |
| `user_login_failed` | **Do not emit in frontend** | Backend emits this event with `source_ip_hash` for security-safe throttling |
| `session_expired` | Token expiry detection in middleware/auth hook | include `last_active_path` and `session_duration_seconds` when available |

---

## Property Allowlists (Frontend-Capture Subset)

These are the allowed keys for frontend-captured properties in this phase:

| Event | Allowed properties for frontend capture |
|---|---|
| `ingredient_list_viewed` | `location_id`, `ingredient_count`, `view_source` |
| `user_login_succeeded` | `location_id`, `auth_method` |
| `user_login_failed` | **Backend-owned** (frontend does not emit) |
| `session_expired` | `last_active_path`, `session_duration_seconds`, `location_id` |

Note: Canonical source of truth remains `docs/telemetry/event-schemas.json`.

---

## Business Constraints

- **Dual currency is business metadata, not frontend usage telemetry** in this phase.
- `location_id` is required for inventory events.
- `reason` on `consumption_order_created` follows Milestone 5 values (`consumption`, `waste`) for KPI aggregation.
- `userId` must always be TinyDB UUID.
- Never capture emails/passwords or user-entered secrets.

---

## Phase 2 Evaluation Criteria

![Telemetry frontend capture evaluation criteria](/home/codespace/.cursor/projects/workspaces-shaunM12-Brasaland-Website/assets/Screenshot_2026-07-08_at_10.35.54_AM-11a5f76f-c0b0-490f-91b3-c331f13ebceb.png)

Reference image used to validate:
- Stub endpoint behavior (`POST /telemetry/events`)
- Envelope field parity with Phase 1
- Env var usage (`NEXT_PUBLIC_TELEMETRY_ENDPOINT`, `TELEMETRY_ENDPOINT`)
- TelemetryService batching/debounce/flush/retry behavior
- `track()` as single entry point
- Strict event/property allowlist compliance
- Inventory + auth instrumentation coverage
- Auth ownership clarity: frontend emits `user_login_succeeded`/`session_expired`; backend emits `user_login_failed` with `source_ip_hash`
- `user_login_succeeded.location_id` is best-effort from the last inventory location in session storage (optional on first login)
- DevTools verification of payload format and `200` response

---

## Verification Checklist

1. Stub endpoint receives batched payload with envelope shape.
2. Backend logs event count + event types and returns `200 { "received": N }`.
3. TelemetryService batches at 10s / 20 events.
4. `sendBeacon` flush executes on hidden/close.
5. Retry policy executes up to 3 times then drops batch.
6. Inventory events reach stub endpoint from backoffice flow.
7. Auth telemetry reaches endpoint with ownership split: frontend (`user_login_succeeded`, `session_expired`) and backend (`user_login_failed`).
8. Captured keys match allowlists in `event-schemas.json`.
9. No PII in properties or envelope.

### Remaining frontend instrumentation

| Event | Status |
|---|---|
| `ingredient_list_viewed` | ✅ Implemented (`/inventory/products` page mount) |
| `user_login_succeeded` | ✅ Implemented (`AuthProvider` after successful login) |
| `session_expired` | ✅ Implemented (`http.ts` on refresh failure) |
| `location_filter_applied` | ✅ Implemented (products page location selector) |
| `order_form_abandoned` | ✅ Implemented (inbound/outbound form idle detection) |

---

_Brasaland Digital — Internal document for 4Geeks Academy AI Engineering Track_
