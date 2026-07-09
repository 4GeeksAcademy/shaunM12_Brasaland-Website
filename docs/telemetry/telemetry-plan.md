# Telemetry Plan — Brasaland Operational Runbook

## AI Engineering - 4Geeks Academy

> **Canonical design:** `memory-bank/historical-reference/context-15-telemetry-plan.md`  
> **Event contracts:** `docs/telemetry/event-schemas.json`  
> **Type:** Observability / operational runbook  
> **Status:** 🟢 Phases 1-4 backend telemetry implemented (`/telemetry/events` storage + `/telemetry/report`); remaining frontend-only events are additive follow-ups

> **Authority rule:** Milestone 5 contexts are authoritative for runtime inventory/API contracts. This runbook is additive observability guidance and must not redefine Milestone behavior.

---

## Purpose

This runbook operationalizes `context-15-telemetry-plan.md`. It defines how Brasaland emits, validates, routes, and stores telemetry for the inventory system (`Ingredient`, `SupplyOrder`, `ConsumptionOrder`) and selected backoffice flows.

The context document owns **why** and **what**. This document owns **how** at implementation time.

---

## Document Map

| Section | Contents |
| ------- | -------- |
| [Phase 1 — KPIs](#phase-1--kpis) | Three business KPIs and event mapping |
| [Phase 1 — Instrumentation](#phase-1--instrumentation-map) | Where events fire in the application |
| [Phase 2 — Envelope](#phase-2--event-envelope) | Mandatory fields on every event |
| [Phase 2 — Event Catalog](#phase-2--event-catalog) | Wave 1 events by domain |
| [Phase 3 — Delivery](#phase-3--delivery-strategy) | Stream vs batch, throttle rules |
| [Phase 3 — Storage & Ingestion](#phase-3--storage--ingestion-runtime) | Supabase table contract + mixed-batch endpoint behavior |
| [Phase 4 — Reporting](#phase-4--reporting-runtime) | Pandas KPI metrics + cached report endpoint |
| [Implementation Hooks](#implementation-hooks) | Code attachment points |
| [Configuration](#configuration) | Environment variables |
| [Risks and Exclusions](#risks-and-exclusions) | Privacy, currency, gaps |
| [Verification](#verification-checklist) | Pre-ship checklist |

---

## Phase 1 — KPIs

### KPI definitions

| # | KPI | Definition | Business decision | Primary events | Data origin |
| - | --- | ---------- | ------------------- | -------------- | ----------- |
| 1 | **Daily consumption rate by ingredient and location** | Units consumed per ingredient per location per day (`ConsumptionOrder`, `reason = consumption`) | Detect overconsumption; adjust supplier orders | `consumption_order_created` | `POST /inventory/orders/outbound` |
| 2 | **Stock-out frequency** | Times stock hit zero or `min_stock_threshold` | Identify under-stocked ingredients; renegotiate contracts | `stock_threshold_triggered`, `consumption_order_failed` | Stock recompute; outbound rejection |
| 3 | **Waste and loss ratio** | Share of `ConsumptionOrder` with `reason = waste` vs total | Flag abnormal waste; trigger investigation | `consumption_order_created` | `POST /inventory/orders/outbound` |

### KPI → aggregation

| KPI | Aggregation | Batch window |
| --- | ----------- | -------------- |
| Daily consumption rate | `SUM(quantity)` by `ingredient_id`, `location_id`, day where `reason = consumption` | Daily |
| Stock-out frequency | `COUNT` of `stock_threshold_triggered` + `consumption_order_failed` where `error_code = insufficient_stock` | Weekly |
| Waste and loss ratio | `SUM(quantity)` loss reasons / `SUM(quantity)` all reasons by `location_id` | Weekly |

Full KPI index: `event-schemas.json` → `kpis`.

---

## Phase 1 — Instrumentation Map

### Inventory flow

Journey: **login → stock list → location filter → inbound/outbound form → order submit → stock recompute → threshold check**.

| # | Event | Trigger | Golden rule |
| - | ----- | ------- | ----------- |
| 1 | `user_login_succeeded` | `POST /auth/login` success | Correlate consumption anomalies with staffing coverage. |
| 2 | `ingredient_list_viewed` | `GET /inventory/products`, `/inventory/products` page | Decide whether to simplify stock UI or add proactive alerts. |
| 3 | `location_filter_applied` | Location selector on inventory pages | Prioritize location-specific training. |
| 4 | `supply_order_created` | `POST /inventory/orders/inbound` after commit | Adjust supplier delivery schedules before stock-outs. |
| 5 | `supply_order_failed` | Inbound validation, unknown supplier, or 404 | Fix supplier-directory data or retrain managers on inbound entry. |
| 6 | `consumption_order_created` | `POST /inventory/orders/outbound` after commit | Detect overconsumption and abnormal waste (KPIs 1 and 3). |
| 7 | `consumption_order_failed` | Outbound validation or `InsufficientStockError` | Investigate data-entry errors vs real shortages (KPI 2). |
| 8 | `direct_stock_edit_rejected` | Blocked stock mutation outside orders | Enforce training or tighten API guards. |
| 9 | `stock_threshold_triggered` | Edge-triggered stock cross below `min_stock_threshold` after order commit | Trigger emergency supply orders (KPI 2). |

### Backoffice (beyond inventory)

| Event | Trigger | Golden rule |
| ----- | ------- | ----------- |
| `user_login_failed` | `POST /auth/login` failure | Detect credential issues or brute-force at locations. |
| `session_expired` | Refresh failure in `uis/backoffice/lib/http.ts` | Adjust session TTL or add save-draft on order forms. |
| `order_form_abandoned` | Idle timeout on inbound/outbound forms | Fix UX friction blocking stock accuracy. |

Domain groupings: `event-schemas.json` → `domains`.

---

## Phase 2 — Event Envelope

Every emitted event must include these fields (see `event-schemas.json` → `envelope` → `fields`):

| Field | Type | Description |
| ----- | ---- | ----------- |
| `eventId` | UUID v4 | Idempotency key |
| `timestamp` | ISO 8601 UTC | Emission time |
| `sessionId` | string | Opaque session id |
| `userId` | string | TinyDB user UUID (`anonymous` for pre-auth only) |
| `event_type` | string | `entity_action` matching a schema key |
| `schemaVersion` | integer | Starts at `1` |
| `requestId` | string | Request correlation id |
| `properties` | object | Payload — **allowlist only** |

### Example envelope

```json
{
  "eventId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2026-07-06T17:45:00Z",
  "sessionId": "sess_8f3a2b1c",
  "userId": "usr_tinydb_uuid_here",
  "event_type": "consumption_order_created",
  "schemaVersion": 1,
  "requestId": "req_9d4e2f1a",
  "properties": {
    "consumption_order_id": 42,
    "ingredient_id": 7,
    "quantity": 2.5,
    "reason": "consumption",
    "location_id": 11,
    "created_by": "usr_tinydb_uuid_here",
    "currency": "USD",
    "unit": "kg"
  }
}
```

### Validation rules

1. Reject any `properties` key not in the event's `propertyAllowlist`.
2. Derive `currency` from `location_id` (1–9 → `COP`, 10–14 → `USD`) server-side.
3. Never include names, emails, or passwords in envelope or properties.

### Correlation identifiers

| Field | API (server) | Backoffice (client) |
| ----- | ------------ | ------------------- |
| `sessionId` | `EmitContext` in `services/api/telemetry/context.py` — `sess_` + 12 hex chars per request when no browser session | Stable per tab via `uis/backoffice/lib/telemetry.ts` (`sessionStorage`) |
| `requestId` | `req_` + 12 hex chars per handler invocation, or client `X-Request-Id` when present | `X-Request-Id` on authorized API calls; order submits use one correlated id via `request-id.ts` |
| `userId` | JWT user UUID; `"anonymous"` for pre-auth only | Auth store UUID after login |

---

## Phase 2 — Event Catalog

### By domain

#### Inventory (`event-schemas.json` → `domains.inventory`)

| event_type | Processing | KPI | Sensitivity |
| ---------- | ---------- | --- | ----------- |
| `supply_order_created` | batch | 2 (indirect) | standard |
| `supply_order_failed` | batch | — | standard |
| `consumption_order_created` | batch | 1, 3 | standard |
| `consumption_order_failed` | stream | 2 | standard |
| `stock_threshold_triggered` | stream | 2 | standard |
| `direct_stock_edit_rejected` | stream | — | standard |

#### Authentication (`domains.authentication`)

| event_type | Processing | Sensitivity |
| ---------- | ---------- | ----------- |
| `user_login_succeeded` | batch | standard |
| `user_login_failed` | stream | standard |
| `session_expired` | batch | standard |

#### Navigation (`domains.navigation`)

| event_type | Processing | Sensitivity |
| ---------- | ---------- | ----------- |
| `ingredient_list_viewed` | batch | standard |
| `location_filter_applied` | batch | standard |
| `order_form_abandoned` | batch | standard |

Full property allowlists and field types: `event-schemas.json` → `events`.

---

## Phase 3 — Delivery Strategy

### Stream vs batch

| Processing | Events | Business justification |
| ---------- | ------ | ---------------------- |
| **Stream** | `stock_threshold_triggered`, `consumption_order_failed`, `direct_stock_edit_rejected`, `user_login_failed` | Same-shift replenishment, active shortages, policy bypass, brute-force detection |
| **Batch** (hourly) | `supply_order_created`, `consumption_order_created`, `supply_order_failed`, `user_login_succeeded`, `session_expired`, `ingredient_list_viewed`, `location_filter_applied`, `order_form_abandoned` | Daily/weekly KPI and UX analytics |

Routing index: `event-schemas.json` → `processing`.

Backend `emit_event()` may attach a `processing` hint (`stream` vs `batch`) to stdout envelopes. That field is sink metadata only and is not part of the persisted ingestion envelope stored in `telemetry_events`.

### Throttle and debounce

| Event | Strategy | Rule |
| ----- | -------- | ---- |
| `ingredient_list_viewed` | debounce | 30s per `(sessionId, location_id)` |
| `location_filter_applied` | debounce | 10s per `(sessionId, location_id)` |
| `order_form_abandoned` | idle emit | Once per `(sessionId, form_type, ingredient_id)` after 120s |
| `user_login_failed` | throttle | Max 1 per `(source_ip_hash, 60s)` |
| `stock_threshold_triggered` | dedupe | Per `(ingredient_id, location_id, 24h)` unless stock recovers. **Edge-trigger:** `stock_before > threshold` and `stock_after <= threshold` only. |

Full rules: `event-schemas.json` → `throttle`.

### Restricted routing

`consumption_order_created` follows Milestone 5 reason values (`consumption`, `waste`) and routes through the standard telemetry pipeline.

---

## Phase 3 — Storage & Ingestion Runtime

### Active mode

- `TELEMETRY_PHASE_MODE=storage` enables the real ingestion path.
- `TELEMETRY_PHASE_MODE=stub` remains available for Phase 2 envelope-only checks.

### Ingestion contract (`POST /telemetry/events`)

- Request shape remains `{ "events": [...] }`.
- Validation is per event (`TelemetryEvent.model_validate(...)` + allowlist check).
- Mixed batches are supported: valid events are persisted even when some events fail.
- Persistence is one bulk insert operation per batch.
- Response in storage mode is `{ "received": N, "stored": M, "rejected": R }`.

### Storage contract (`telemetry_events`)

- Column set: `id`, `event_type`, `timestamp`, `service`, `level`, `value`, `tags`, `created_at`.
- Indexes: `event_type`, `timestamp`, GIN on `tags`.
- Row model is append-only; no business update/delete flow.

### Dual persistence paths

- **Frontend batches** → `POST /telemetry/events` when `TELEMETRY_PHASE_MODE=storage`.
- **Backend inventory/auth emit** → `emit_event()` → `write_postgres()` when `TELEMETRY_ENABLED=true` and `TELEMETRY_SINK` includes `postgres`.

Both paths write to the same table. Enable both for full end-to-end coverage from backoffice orders and navigation events.

---

## Phase 4 — Reporting Runtime

### Endpoint

- `GET /telemetry/report`
- Optional query params: `start_date`, `end_date` (ISO 8601)
- Default window when omitted: last 7 days (`now_utc - 7d` to `now_utc`)
- Response shape:
  - `period`
  - `metrics`

### Metrics implemented

- `daily_consumption_by_ingredient_and_location` (KPI 1)
  - `SUM(quantity)` from `consumption_order_created` where `reason = consumption`, grouped by date, ingredient, and location.
- `stock_out_frequency` (KPI 2)
  - Count of `stock_threshold_triggered` plus `consumption_order_failed` where `error_code = insufficient_stock`, grouped by date, ingredient, and location.
- `waste_loss_ratio` (KPI 3)
  - `waste_quantity / total_quantity` from `consumption_order_created`, grouped by date and location.
- `auth_failure_rate_per_day` (optional, not a Phase 1 KPI)
  - Daily login failure ratio from `user_login_succeeded` and `user_login_failed`.

### Cache

- In-memory cache with `60s` TTL.
- Cache key includes resolved report period (`start_date`, `end_date`).
- Same-period requests within TTL return cached payload without recalculation.

---

## Implementation Hooks

| Event | Layer | Hook location |
| ----- | ----- | ------------- |
| `supply_order_created` | API | `services/api/inventory/routes.py` → after `repository.create_inbound_order` |
| `supply_order_failed` | API | `services/api/inventory/routes.py` → on inbound validation / 404 |
| `consumption_order_created` | API | `services/api/inventory/routes.py` → after `repository.create_outbound_order` |
| `consumption_order_failed` | API | `services/api/inventory/routes.py` → on `InsufficientStockError` |
| `stock_threshold_triggered` | API | `services/api/inventory/repository.py` → after order commit + stock compare |
| `direct_stock_edit_rejected` | API | `services/api/inventory/routes.py` → `PATCH /inventory/products/{id}` guard |
| `user_login_succeeded` | Frontend | `uis/backoffice/context/AuthProvider.tsx` → after successful login |
| `user_login_failed` | API | `services/api/auth/` → login failure handler |
| `session_expired` | Frontend | `uis/backoffice/lib/http.ts` → refresh failure |
| `ingredient_list_viewed` | Frontend | `/inventory/products` page mount |
| `location_filter_applied` | Frontend | Inventory location selector |
| `order_form_abandoned` | Frontend | `InboundOrderForm`, `OutboundOrderForm` idle detection |

**Ownership rule:** each event has a single emitter. Inventory order lifecycle events are backend-owned (API/repository) and must not be emitted again from frontend forms.

### Module layout (implemented)

```text
services/api/telemetry/
  constants.py
  emit.py          # envelope + validation helpers
  models.py        # telemetry_events storage model
  routes.py        # /telemetry/events + /telemetry/report
  analysis.py      # phase 4 pandas metric pipeline
  throttle.py      # auth failure throttle helper
  seed.py          # reset and seed helper

uis/backoffice/lib/
  telemetry.ts     # client batching/flush helper
  request-id.ts    # correlated request ids for API + telemetry
```

---

## Configuration

| Variable | Purpose | Default |
| -------- | ------- | ------- |
| `TELEMETRY_ENABLED` | Master switch for backend `emit_event()` path | `false` (auto `true` in development when `DATABASE_URL` is set and var is omitted) |
| `TELEMETRY_SINK` | Backend emit destinations (`stdout`, `postgres`, `both`) | `stdout` (auto `both` in development when `DATABASE_URL` is set and var is omitted) |
| `TELEMETRY_STREAM_ENDPOINT` | Stream sink URL | — |
| `TELEMETRY_BATCH_BUCKET` | Batch export destination | — |
| `TELEMETRY_SAMPLE_RATE` | Client sampling `0.0`–`1.0` | `1.0` |
| `TELEMETRY_ENDPOINT` | Backend ingestion path consumed by frontend endpoint config | `/telemetry/events` |
| `NEXT_PUBLIC_TELEMETRY_ENDPOINT` | Backoffice telemetry target URL | environment-specific |
| `TELEMETRY_PHASE_MODE` | Runtime ingestion mode (`stub` or `storage`) | `storage` |
| `TELEMETRY_RESTRICTED_ENDPOINT` | Reserved for future restricted telemetry policies | — |

### Local development

1. Set `DATABASE_URL` to your Supabase/Postgres URI.
2. Either set `TELEMETRY_ENABLED=true` and `TELEMETRY_SINK=both`, or omit them in `APP_ENV=development` to auto-enable backend persistence.
3. Emit test events and validate against `event-schemas.json` allowlists.
4. Confirm consumption events match Milestone 5 reason values (`consumption`, `waste`).

### Login `location_id` semantics

`user_login_succeeded.location_id` is optional. The backoffice sends the last inventory location selected in-session when available; first login before visiting inventory may omit it. This does not change Milestone 5 auth contracts.

---

## Risks and Exclusions

### Privacy

- No emails, names, phone numbers, or free-text in telemetry.
- `user_login_failed`: `failure_reason` enum only — never attempted passwords.
- `consumption_order_created` uses Milestone 5 reasons (`consumption`, `waste`) and excludes PII.

### Dual-currency

- `currency` derived from `location_id` (1–9 → `COP`, 10–14 → `USD`).
- Cross-location cost comparison requires FX in analytics layer — not in raw events.

### Multi-location

- Location-scoped events require `location_id`.
- Events without location use `location_id: null` and are excluded from location KPI rollups.

### Data not captured

- Raw HTTP headers (except `source_ip_hash` for login throttle).
- Ingredient unit costs until procurement exposes pricing.
- Incident descriptions, supplier contacts, password-reset tokens.
- Per-keystroke form input (only `order_form_abandoned` summary).

### Rejected candidate events

| Candidate event | Reason discarded |
| --------------- | ---------------- |
| `ingredient_search_typed` | Privacy exclusion; no KPI; `order_form_abandoned` covers UX friction. |
| `page_view` (generic) | No Brasaland-specific hypothesis; replaced by domain events. |
| `ingredient_name_viewed` | Re-identification risk; use `ingredient_id` only. |
| `supplier_contact_clicked` | Supplier PII excluded; use `supplier_id` on orders. |
| `stock_level_snapshot` (periodic) | Level-trigger spam; use edge-triggered `stock_threshold_triggered` on order commit. |
| `raw_http_request` | Headers/bodies excluded; only `source_ip_hash` on login failure. |

### Implementation gaps (before instrumentation)

| Gap | Status |
| --- | ------ |
| Explicit stock-mutation guard on PATCH | ✅ `direct_stock_edit_rejected` in `inventory/routes.py` |
| API uses `IngredientEntry`/`IngredientExit`; events use `SupplyOrder`/`ConsumptionOrder` | ✅ Mapped in route emitters |
| Supabase storage + mixed-batch ingestion (`POST /telemetry/events`) | ✅ Implemented in Phase 3 |
| Telemetry report endpoint (`GET /telemetry/report`) + pandas metrics + 60s cache | ✅ Implemented in Phase 4 |
| Backoffice-only events (`location_filter_applied`, `order_form_abandoned`) | ✅ Implemented |

---

## Verification Checklist

1. [x] Every Wave 1 event in `context-15` exists in `event-schemas.json` → `events`.
2. [x] Each event has `propertyAllowlist`, `processing`, and `domain`.
3. [x] Stream events have business urgency documented in `processing.stream`.
4. [x] KPI 1–3 map to events via `kpis` and per-event `kpiLinks`.
5. [x] Consumption reason values align with Milestone 5 (`consumption`, `waste`).
6. [x] Throttle rules in `throttle` match this runbook.
7. [x] Test emit validates allowlist rejection for extra keys (`tests/test_telemetry.py`).
8. [x] Storage mode supports mixed-batch persistence and one bulk insert per batch.
9. [x] `GET /telemetry/report` returns the three Phase 1 KPI metrics with period defaults and 60-second cache.
10. [x] Optional auth metric uses login success/failure events to compute daily ratio.
11. [x] Remaining gaps are frontend-only additive instrumentation (`location_filter_applied`, `order_form_abandoned`).

---

_Brasaland Digital — Internal document for 4Geeks Academy AI Engineering Track_
