# Telemetry Plan — Brasaland Operational Runbook

## AI Engineering - 4Geeks Academy

> **Canonical design:** `memory-bank/historical-reference/context-15-telemetry-plan.md`  
> **Alignment:** `memory-bank/historical-reference/context-15-course-alignment-plan.md`  
> **Event contracts:** `docs/telemetry/event-schemas.json` (`schemaVersion` 2)  
> **Type:** Observability / operational runbook  
> **Status:** 🟢 Course floor runtime live — emitters, storage, and report use `schemaVersion` 2

> **Authority rule:** Milestone 5 contexts are authoritative for runtime inventory/API. This runbook is additive observability and must not redefine Milestone stock behavior or API exit `reason` (`consumption` | `waste`).

---

## Purpose

This runbook operationalizes `context-15-telemetry-plan.md` after course-floor alignment. It defines how Brasaland emits, validates, routes, and stores telemetry for inventory (`Product`, `InboundOrder`, `OutboundOrder`) and selected backoffice flows.

The context document owns **why** and **what**. This document owns **how** at implementation time.

---

## Document Map

| Section | Contents |
| ------- | -------- |
| [Phase 1 — KPIs](#phase-1--kpis) | Course floor + three reporting KPIs |
| [Phase 1 — Instrumentation](#phase-1--instrumentation-map) | Where events fire |
| [Phase 2 — Envelope](#phase-2--event-envelope) | Mandatory fields |
| [Phase 2 — Event Catalog](#phase-2--event-catalog) | Wave 1 by domain |
| [Phase 3 — Delivery](#phase-3--delivery-strategy) | Stream vs batch, throttle |
| [Phase 3 — Storage & Ingestion](#phase-3--storage--ingestion-runtime) | Supabase + mixed-batch |
| [Phase 4 — Reporting](#phase-4--reporting-runtime) | Pandas KPIs + report endpoint |
| [Implementation Hooks](#implementation-hooks) | Code attachment points |
| [Configuration](#configuration) | Environment variables |
| [Risks and Exclusions](#risks-and-exclusions) | Privacy, currency, gaps |
| [Verification](#verification-checklist) | Checklist |

---

## Phase 1 — KPIs

### Course floor (mandatory instrumentation)

| `event_type` | Role |
| ------------ | ---- |
| `inbound_order_created` | Purchasing visibility (Lucía) |
| `outbound_order_created` | Consumption rate (Felipe) |
| `stock_waste_registered` | Waste audits (Felipe) |
| `stock_threshold_triggered` | Shortfall / replenishment |
| `direct_stock_edit_rejected` | Traceability bypass (Jake) |
| `ingredient_price_variance_detected` | Price spike alert (Lucía, Mariana) |

### Reporting KPI definitions

| # | KPI | Definition | Business decision | Primary events | Data origin |
| - | --- | ---------- | ----------------- | -------------- | ----------- |
| 1 | **Daily consumption rate by product and location** | Units consumed per product per location per day | Detect overconsumption; adjust supplier orders | `outbound_order_created` | `POST /inventory/orders/outbound` |
| 2 | **Stock-out frequency** | Times stock hit zero or `min_stock_threshold` | Identify under-stocked products | `stock_threshold_triggered`, `outbound_order_failed` | Stock recompute; outbound rejection |
| 3 | **Waste and loss ratio** | Wasted quantity vs total outbound movement | Flag abnormal waste | `stock_waste_registered`, `outbound_order_created` | Outbound commits |

### KPI → aggregation

| KPI | Aggregation | Batch window |
| --- | ----------- | ------------ |
| Daily consumption rate | `SUM(quantity)` by `product_id`, `location_id`, day from `outbound_order_created` | Daily |
| Stock-out frequency | `COUNT` of `stock_threshold_triggered` + `outbound_order_failed` where `error_code = insufficient_stock` | Weekly |
| Waste and loss ratio | `SUM(quantity)` from `stock_waste_registered` / (`outbound` + waste quantities) by `location_id` | Weekly |

Full KPI index: `event-schemas.json` → `kpis`.

---

## Phase 1 — Instrumentation Map

### Inventory flow

Journey: **login → stock list → location filter → inbound/outbound form → order submit → stock recompute → threshold check → price variance check**.

| # | Event | Trigger | Golden rule |
| - | ----- | ------- | ----------- |
| 1 | `user_login_succeeded` | `POST /auth/login` success | Correlate consumption with staffing. |
| 2 | `ingredient_list_viewed` | Products list page / API | Simplify UI or add alerts. |
| 3 | `location_filter_applied` | Location selector | Location-specific training. |
| 4 | `inbound_order_created` | Inbound after commit | Purchasing consolidation / schedules. |
| 5 | `inbound_order_failed` | Inbound validation / 404 | Fix supplier data or retrain. |
| 6 | `outbound_order_created` | Outbound commit, API `reason=consumption` | KPI 1 consumption. |
| 7 | `stock_waste_registered` | Outbound commit, API `reason=waste` | KPI 3 waste (no dual emit). |
| 8 | `outbound_order_failed` | Outbound validation / insufficient stock | KPI 2 leading indicator. |
| 9 | `direct_stock_edit_rejected` | Blocked stock mutation | Training / API guards. |
| 10 | `stock_threshold_triggered` | Edge-trigger after order commit | Emergency supply (KPI 2). |
| 11 | `ingredient_price_variance_detected` | Inbound unit cost vs history ≥ threshold | Alert Lucía / Mariana. |

### Backoffice (beyond floor)

| Event | Trigger | Golden rule |
| ----- | ------- | ----------- |
| `user_login_failed` | Login failure | Credential / brute-force detection. |
| `session_expired` | Refresh failure in `http.ts` | Session TTL / save-draft. |
| `order_form_abandoned` | Idle on order forms | UX friction. |

Domain groupings: `event-schemas.json` → `domains`.

---

## Phase 2 — Event Envelope

Every emitted event must include these fields (`event-schemas.json` → `envelope` → `fields`):

| Field | Type | Description |
| ----- | ---- | ----------- |
| `eventId` | UUID v4 | Idempotency key |
| `timestamp` | ISO 8601 UTC | Emission time |
| `sessionId` | string | Opaque session id |
| `userId` | string | TinyDB UUID (`anonymous` pre-auth only) |
| `event_type` | string | Matches a schema key |
| `schemaVersion` | integer | Floor inventory events use `2` |
| `requestId` | string | Correlation id |
| `properties` | object | Allowlist only |

### Example envelopes

**Consumption (`outbound_order_created`):**

```json
{
  "eventId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2026-07-06T17:45:00Z",
  "sessionId": "sess_8f3a2b1c",
  "userId": "usr_tinydb_uuid_here",
  "event_type": "outbound_order_created",
  "schemaVersion": 2,
  "requestId": "req_9d4e2f1a",
  "properties": {
    "outbound_order_id": 42,
    "product_id": 7,
    "product_category": "meat",
    "quantity": 2.5,
    "unit": "kg",
    "location_id": 11,
    "country": "US",
    "created_by": "usr_tinydb_uuid_here",
    "currency": "USD"
  }
}
```

**Waste (`stock_waste_registered`):**

```json
{
  "eventId": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "timestamp": "2026-07-06T18:00:00Z",
  "sessionId": "sess_8f3a2b1c",
  "userId": "usr_tinydb_uuid_here",
  "event_type": "stock_waste_registered",
  "schemaVersion": 2,
  "requestId": "req_aa11bb22",
  "properties": {
    "outbound_order_id": 43,
    "product_id": 7,
    "product_category": "meat",
    "quantity": 1.0,
    "unit": "kg",
    "reason": "unspecified",
    "location_id": 1,
    "country": "CO",
    "created_by": "usr_tinydb_uuid_here",
    "currency": "COP"
  }
}
```

Until additive API `waste_subtype` exists, `reason` may be `unspecified`. Target values: `expired`, `kitchen_error`, `theft_suspected`.

### Validation rules

1. Reject any `properties` key not in the event's `propertyAllowlist`.
2. Derive `currency`, `country`, and `product_category` server-side — never trust the client.
3. Never include names, emails, or passwords.
4. Do not convert currencies in the emitter.

### Correlation identifiers

| Field | API (server) | Backoffice (client) |
| ----- | ------------ | ------------------- |
| `sessionId` | `EmitContext` — `sess_` + hex when no browser session | `telemetry.ts` `sessionStorage` |
| `requestId` | Per handler or client `X-Request-Id` | Shared on order submits via `request-id.ts` |
| `userId` | JWT UUID; `"anonymous"` pre-auth | Auth store after login |

---

## Phase 2 — Event Catalog

### Inventory (`domains.inventory`)

| event_type | Floor | Processing | KPI |
| ---------- | ----- | ---------- | --- |
| `inbound_order_created` | ✅ | batch | 2 (indirect) |
| `inbound_order_failed` | — | batch | — |
| `outbound_order_created` | ✅ | batch | 1, 3 |
| `outbound_order_failed` | — | stream | 2 |
| `stock_waste_registered` | ✅ | batch | 3 |
| `stock_threshold_triggered` | ✅ | stream | 2 |
| `direct_stock_edit_rejected` | ✅ | stream | — |
| `ingredient_price_variance_detected` | ✅ | stream | — |

### Authentication / navigation (beyond floor)

Unchanged names: `user_login_succeeded`, `user_login_failed`, `session_expired`, `ingredient_list_viewed`, `location_filter_applied`, `order_form_abandoned` (`form_type`: `InboundOrder` \| `OutboundOrder`).

Full allowlists: `event-schemas.json` → `events`.

---

## Phase 3 — Delivery Strategy

### Stream vs batch

| Processing | Events | Justification |
| ---------- | ------ | ------------- |
| **Stream** | `stock_threshold_triggered`, `outbound_order_failed`, `direct_stock_edit_rejected`, `ingredient_price_variance_detected`, `user_login_failed` | Same-shift ops, policy, price alerts, brute-force |
| **Batch** (hourly) | `inbound_order_created`, `outbound_order_created`, `stock_waste_registered`, `inbound_order_failed`, auth success, session, navigation | Daily/weekly KPI and UX |

### Throttle and debounce

| Event | Strategy | Rule |
| ----- | -------- | ---- |
| `ingredient_list_viewed` | debounce | 30s per `(sessionId, location_id)` |
| `location_filter_applied` | debounce | 10s per `(sessionId, location_id)` |
| `order_form_abandoned` | idle emit | Once per `(sessionId, form_type, product_id)` after 120s |
| `user_login_failed` | throttle | Max 1 per `(source_ip_hash, 60s)` |
| `stock_threshold_triggered` | dedupe | Per `(product_id, location_id, 24h)`; edge-trigger only |
| `ingredient_price_variance_detected` | dedupe | Per `(product_id, supplier_id, location_id, 24h)` |

### Restricted routing / waste split

- API `reason=consumption` → emit `outbound_order_created` only.
- API `reason=waste` → emit `stock_waste_registered` only.
- Never dual-emit waste into both events (double-counts KPI 3).

---

## Phase 3 — Storage & Ingestion Runtime

### Active mode

- `TELEMETRY_PHASE_MODE=storage` enables real ingestion.
- `TELEMETRY_PHASE_MODE=stub` remains for envelope-only checks.

### Ingestion contract (`POST /telemetry/events`)

- Request shape `{ "events": [...] }`.
- Per-event validation + allowlist.
- Mixed batches: valid events persist when some fail.
- One bulk insert per batch.
- Response: `{ "received", "stored", "rejected" }`.

### Storage contract (`telemetry_events`)

- Columns: `id`, `event_type`, `timestamp`, `service`, `level`, `value`, `tags`, `created_at`.
- Indexes: `event_type`, `timestamp`, GIN on `tags`.
- Append-only.

### Dual persistence paths

- Frontend batches → `POST /telemetry/events` when `TELEMETRY_PHASE_MODE=storage`.
- Backend emit → `emit_event()` → `write_postgres()` when enabled.

**History:** After v2 rename, regenerate local rows (no migrator). Old `supply_order_*` / `consumption_order_*` names are deprecated.

---

## Phase 4 — Reporting Runtime

### Endpoint

- `GET /telemetry/report`
- Optional `start_date`, `end_date` (ISO 8601); default last 7 days
- Response: `period`, `metrics`

### Metrics

- `daily_consumption_by_product_and_location` (KPI 1) ← `outbound_order_created`
- `stock_out_frequency` (KPI 2) ← `stock_threshold_triggered` + `outbound_order_failed` (`insufficient_stock`)
- `waste_loss_ratio` (KPI 3) ← `stock_waste_registered` / total outbound movement
- Optional `auth_failure_rate_per_day`

`analysis.py` queries v2 `event_type`s and report rows use `product_id`.

### Cache

- In-memory 60s TTL keyed by report period.

---

## Implementation Hooks

| Event | Layer | Hook location |
| ----- | ----- | ------------- |
| `inbound_order_created` | API | `inventory/routes.py` after inbound create |
| `inbound_order_failed` | API | Inbound validation / 404 |
| `outbound_order_created` | API | Outbound create when `reason=consumption` |
| `stock_waste_registered` | API | Outbound create when `reason=waste` |
| `outbound_order_failed` | API | `InsufficientStockError` / validation |
| `stock_threshold_triggered` | API | Repository after order + stock compare |
| `direct_stock_edit_rejected` | API | `PATCH /inventory/products/{id}` guard |
| `ingredient_price_variance_detected` | API | After inbound when variance ≥ threshold |
| `user_login_succeeded` | Frontend | `AuthProvider.tsx` |
| `user_login_failed` | API | Auth login failure |
| `session_expired` | Frontend | `http.ts` refresh failure |
| `ingredient_list_viewed` | Frontend | `/inventory/products` |
| `location_filter_applied` | Frontend | Location selector |
| `order_form_abandoned` | Frontend | Inbound/Outbound form idle |

**Ownership:** each event has a single emitter. Inventory lifecycle events are backend-owned.

### Module layout

```text
services/api/telemetry/
  constants.py
  emit.py
  models.py
  routes.py
  analysis.py
  throttle.py
  seed.py

uis/backoffice/lib/
  telemetry.ts
  request-id.ts
```

---

## Configuration

| Variable | Purpose | Default |
| -------- | ------- | ------- |
| `TELEMETRY_ENABLED` | Backend `emit_event()` master switch | `false` (auto `true` in dev when `DATABASE_URL` set) |
| `TELEMETRY_SINK` | `stdout`, `postgres`, `both` | `stdout` (auto `both` in that same case) |
| `TELEMETRY_STREAM_ENDPOINT` | Stream sink URL | — |
| `TELEMETRY_BATCH_BUCKET` | Batch export | — |
| `TELEMETRY_SAMPLE_RATE` | Client sampling | `1.0` |
| `TELEMETRY_ENDPOINT` | Ingestion path | `/telemetry/events` |
| `NEXT_PUBLIC_TELEMETRY_ENDPOINT` | Backoffice target | environment-specific |
| `TELEMETRY_PHASE_MODE` | `stub` \| `storage` | `storage` |
| `TELEMETRY_RESTRICTED_ENDPOINT` | Reserved | — |

### Local development

1. Set `DATABASE_URL`.
2. Enable `TELEMETRY_ENABLED` / `TELEMETRY_SINK=both` (or rely on dev auto).
3. Validate emits against `event-schemas.json` v2 allowlists.
4. Confirm API outbound reasons remain `consumption` | `waste`; waste telemetry uses `stock_waste_registered`.

### Login `location_id` semantics

`user_login_succeeded.location_id` is optional (last inventory location in-session). Does not change Milestone 5 auth.

---

## Risks and Exclusions

### Privacy

- No emails, names, phones, free-text.
- No employee/customer PII on inventory events.
- `user_login_failed`: enum only — never passwords.

### Dual-currency

- Derive `currency` from `location_id`.
- No FX in telemetry; price variance compares same-currency costs only.

### Multi-location

- Floor inventory events require `location_id` + `country`.
- UI language ≠ `country`.

### Data not captured

- Raw HTTP headers (except login `source_ip_hash`).
- Supplier contacts, incident free text, password-reset tokens.
- Per-keystroke form input.

### Rejected candidates

Same as context-15: no `ingredient_search_typed`, generic `page_view`, name-viewed, supplier-contact, periodic stock snapshots, or raw HTTP.

### Implementation gaps (remaining)

| Gap | Status |
| --- | ------ |
| Emitters renamed to course `event_type`s | ✅ Done |
| Waste split emit path | ✅ Done |
| Floor props (`country`, `product_category`, …) on emit | ✅ Done |
| `ingredient_price_variance_detected` | ✅ Done |
| `analysis.py` / report tests on v2 names | ✅ Done |
| Additive API `waste_subtype` | ⏳ Decision 5 D later |
| Seed: three typed waste subtypes | ⏳ Waits on `waste_subtype` |

---

## Verification Checklist

1. [x] Wave/floor events in context-15 exist in `event-schemas.json` → `events`.
2. [x] Each event has `propertyAllowlist`, `processing`, and `domain`.
3. [x] Stream events have business urgency documented.
4. [x] KPI 1–3 map via `kpis` / `kpiLinks` to remapped events.
5. [x] Milestone API reasons remain `consumption` | `waste`; waste telemetry split documented.
6. [x] Throttle rules updated for `product_id` keys where applicable.
7. [x] Test emit validates v2 allowlists.
8. [x] Storage mixed-batch contract unchanged.
9. [x] `GET /telemetry/report` queries v2 event names.
10. [x] Alignment plan and deprecated event name map recorded.
11. [x] History policy: regenerate local rows; no migrator.

---

_Brasaland Digital — Internal document for 4Geeks Academy AI Engineering Track_
