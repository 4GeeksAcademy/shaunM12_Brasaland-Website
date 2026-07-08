# CONTEXT — Brasaland · Telemetry Phase 3: Backend Storage

## AI Engineering - 4Geeks Academy

> **Repository index:** `context-15-backend-storage.md`  
> **Companion docs:** `memory-bank/historical-reference/context-15-telemetry-plan.md`, `memory-bank/historical-reference/context-15-telemetry-frontend-capture.md`, `docs/telemetry/telemetry-plan.md`, `docs/telemetry/event-schemas.json`  
> **Type:** Telemetry persistence + ingestion endpoint  
> **Status:** 🟡 Planned

---

## Your Company

**Brasaland** is a grilled food restaurant chain with 14 locations across Colombia and Florida. You are part of **Brasaland Digital**. The `TelemetryService` in the backoffice is already sending batches of events to the stub endpoint. In this phase, the stub is replaced with the real storage layer.

---

## Scope of This Phase

1. Create the telemetry storage table and indexes in Supabase.
2. Replace the stub `POST /telemetry/events` with real ingestion + persistence.
3. Support mixed valid/invalid batches (per-event rejection, no batch-wide failure).
4. Verify end-to-end ingestion from backoffice to Supabase rows.

---

## Locked Decisions

- Reuse the exact `TelemetryEvent` model from the previous phase; do not modify it.
- Endpoint request contract remains `{ "events": [...] }`.
- Validation is done **per event** inside the handler with `TelemetryEvent.model_validate(...)`.
- Valid events must still be stored when other events in the same batch are invalid.
- Insert valid events using **one bulk insert operation per batch**.
- Response contract is `{ "received": N, "stored": M, "rejected": R }`.
- Telemetry rows are immutable once recorded (no update/delete business logic).

---

## Important Note on Examples

All payload/table snippets in this document are **illustrative reference only**.  
Implementation must follow:

- the shared `TelemetryEvent` envelope contract, and
- per-event allowlists in `docs/telemetry/event-schemas.json`.

Do not hardcode illustrative values from examples.

---

## Reference Appendix — Partial Validation Pattern (Non-Normative)

The following image is included as a **reference only** to explain why per-event parsing is required for mixed batches. It does not replace the implementation contract above.

![Partial validation reference](/home/codespace/.cursor/projects/workspaces-shaunM12-Brasaland-Website/assets/Screenshot_2026-07-08_at_11.33.30_AM-a1579f8d-9260-43b8-9dae-2129b5fe91ad.png)

Key reference takeaways:

- Telemetry storage is append-only (write-only facts), not a CRUD workflow.
- `tags` should keep allowlisted event properties as JSONB.
- Avoid typed whole-body validation like `events: list[TelemetryEvent]` because one invalid event can fail the whole request.
- Prefer loose envelope parsing + per-item `TelemetryEvent.model_validate(...)` inside the handler.
- Continue processing after per-event validation failures and return aggregate counts (`received`, `stored`, `rejected`).

This appendix is explanatory only. For implementation, follow the "Locked Decisions" and "Phase 2 — Real Endpoint in FastAPI" sections.

---

## TelemetryEvent Contract (Reused As-Is)

```python
from pydantic import BaseModel
from typing import Any
from datetime import datetime

class TelemetryEvent(BaseModel):
    eventId: str
    timestamp: datetime
    sessionId: str
    userId: str
    event_type: str
    schemaVersion: int
    requestId: str
    service: str
    properties: dict[str, Any] = {}
```

---

## Phase 1 — Storage Tables in Supabase

Create `telemetry_events` with eight columns:

1. `id` (PK, identity)
2. `event_type` (text)
3. `timestamp` (timestamptz)
4. `service` (text)
5. `level` (text)
6. `value` (numeric, nullable)
7. `tags` (jsonb)
8. `created_at` (timestamptz default `now()`)

### Mapping contract

- `event_type` <- envelope `event_type`
- `timestamp` <- envelope `timestamp`
- `service` <- envelope `service`
- `level` <- fixed operational default (for example `info`)
- `value` <- optional quantity projection for numeric querying (document decision)
- `tags` <- event-specific allowlisted properties
- `created_at` <- DB default

### Required indexes

- index on `timestamp`
- index on `event_type`
- GIN index on `tags` (jsonb search/query performance)

### Immutability

- no update flow
- no delete flow
- append-only insert behavior

---

## Illustrative `tags` Examples (Reference Only)

These examples show the intent of storing event-specific properties in `tags`.

| `event_type` | Illustrative `tags` content |
|---|---|
| `supply_order_created` | `{ "ingredient_id": 7, "quantity": 50, "location_id": 3, "supplier_id": "12" }` |
| `consumption_order_created` | `{ "ingredient_id": 7, "quantity": 12, "reason": "kitchen_use", "location_id": 11 }` |
| `consumption_order_failed` | `{ "error_code": "insufficient_stock", "ingredient_id": 7, "location_id": 3 }` |
| `supply_order_failed` | `{ "error_code": "unknown_supplier", "location_id": 11 }` |
| `ingredient_list_viewed` | `{ "location_id": 3, "ingredient_count": 34, "view_source": "backoffice" }` |
| `user_login_succeeded` | `{ "location_id": 11, "auth_method": "password" }` |
| `user_login_failed` | `{ "failure_reason": "invalid_credentials" }` |
| `session_expired` | `{}` |

The fixed columns (`event_type`, `timestamp`, `service`, `level`) come from envelope and server defaults.

---

## Phase 2 — Real Endpoint in FastAPI

Replace stub `POST /telemetry/events` with full implementation:

- Accept the same envelope shape: `{ "events": [...] }`
- Parse list loosely (do **not** declare `events: list[TelemetryEvent]` as request body type)
- Validate each raw event inside the handler using `TelemetryEvent.model_validate(...)`
- Reject invalid events individually without canceling the batch
- Persist valid events in a single bulk insert operation
- Return `{ "received": N, "stored": M, "rejected": R }`

### Brasaland mixed-batch behavior (required)

If a batch has 5 events and 1 fails validation, 4 valid events must still be inserted:

```json
{ "received": 5, "stored": 4, "rejected": 1 }
```

---

## Phase 3 — End-to-End Verification

With the real endpoint active:

1. Generate real events from backoffice:
   - at least one inbound order
   - at least one outbound order
2. Query `telemetry_events` in Supabase:
   - confirm rows include `event_type`, `timestamp`, and `tags`
3. Test rejection behavior:
   - send a mixed valid/invalid batch with curl or HTTP client
   - verify response counts match inserted vs rejected events

---

## Verification Checklist for Brasaland

- [ ] `supply_order_created` rows include `location_id` in `tags` (required for country segmentation)
- [ ] `consumption_order_created` rows include `reason` in `tags` (required for waste ratio KPI)
- [ ] No row contains manager names, email addresses, passwords, or raw error stacks in `tags`
- [ ] Colombian and Florida events are segmentable via `location_id` in `tags`
- [ ] Mixed batch response correctly reports `received`, `stored`, and `rejected`
- [ ] Insert behavior is one bulk operation per batch

---

## Evaluation Criteria

- The `telemetry_events` table exists in Supabase with eight columns, three indexes, and no update/delete logic
- The `POST /telemetry/events` endpoint does bulk insert and returns `{ "received", "stored", "rejected" }`
- Invalid events are rejected individually without canceling the batch (per-event `model_validate`, not typed `list[TelemetryEvent]` request body)
- The `TelemetryEvent` Pydantic model is reused unchanged from previous phase
- Events appear in `telemetry_events` with `event_type`, `timestamp`, and `tags` correctly populated
- Stored `tags` preserve property allowlists and context-specific dimensions from `telemetry-plan.md`
- Insert path is a single operation per batch, not one insert per event

---

_Brasaland Digital — Internal document for 4Geeks Academy AI Engineering Track_
