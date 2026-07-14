# CONTEXT — Telemetry Phase 1: Company Telemetry Plan Design · Brasaland

## AI Engineering - 4Geeks Academy

> **Repository index:** `context-15-telemetry-plan.md`  
> **Companion docs:** `docs/telemetry/telemetry-plan.md`, `docs/telemetry/event-schemas.json`  
> **Alignment:** `context-15-course-alignment-plan.md`  
> **Related context:** `context-11-milestone-5-backend-inventory-management.md`, `context-12-milestone-5-backoffice-inventory-interface.md`  
> **Type:** Observability design + Wave 1 inventory instrumentation  
> **Status:** 🟢 Course floor (`schemaVersion` 2) implemented end-to-end — docs, emitters, analysis, tests, and seeds

> **Authority rule:** Milestone 5 contexts remain the **runtime** source of truth for inventory/API. The course telemetry CONTEXT owns the **telemetry floor** (capture → storage contracts). This telemetry context is additive and must not alter Milestone 5 stock math, routes, or API exit `reason` (`consumption` | `waste`).

---

## Business Objective

Brasaland is a grilled-food restaurant chain with 14 locations across Colombia and Florida. The inventory system already controls ingredients — meats, vegetables, sauces, beverages, packaging — but operations cannot yet see what is happening inside it.

Telemetry Plan, capture, storage, and technical report revolve around that inventory system. They are the foundation for later executive dashboards and business reports (sales per location, Colombia vs Florida, strategic alerts for Mariana and Felipe).

This context defines KPIs, course-floor events, envelopes, stream/batch routing, and exclusions.

---

## Locked Decisions

- **Telemetry entity vocabulary:** `Product`, `InboundOrder`, `OutboundOrder` (course / API names). Milestone ORM: `Ingredient`, `IngredientEntry`, `IngredientExit`.
- **Course owns telemetry contracts; Milestone 5 owns inventory/API.** See `context-15-course-alignment-plan.md`.
- **Event contracts live in `docs/telemetry/event-schemas.json`** (`schemaVersion` 2). Application code must not invent parallel event names or payload shapes.
- **Standard envelope on every event:** `eventId`, `timestamp` (ISO 8601 UTC), `sessionId`, `userId`, `event_type`, `schemaVersion`, `requestId`, `service`, `properties`.
- **Naming convention:** `entity_action` snake_case (e.g. `inbound_order_created`, `stock_threshold_triggered`).
- **Property allowlists are mandatory.** Only explicitly declared keys per event.
- **Floor properties (inventory):** `location_id`, `country` (`CO`/`US`), `product_id`, `product_category`, `quantity`, `unit`, `currency` (`COP`/`USD`) — derived server-side where applicable.
- **No PII in telemetry.** Opaque TinyDB UUIDs only — never names or emails.
- **No FX conversion** at the telemetry layer; executive reporting converts later.
- **Milestone 5 API reason enum unchanged:** `consumption` | `waste`. Waste subtypes are telemetry (now: `unspecified` allowed; later: additive `waste_subtype`).
- **Fail-open on client, fail-safe on server.** Telemetry must never block user flows.

---

## Focus

Define exactly what Brasaland captures for the **course floor** metrics and three reporting KPIs — before (or while) aligning instrumentation code.

Primary surfaces:

- **API:** `services/api/inventory/` (`/inventory` router)
- **Backoffice:** `uis/backoffice/app/inventory/`, auth flows, navigation
- **Schemas:** `docs/telemetry/event-schemas.json`

---

## Canonical Inventory Entities

| Telemetry / API name | Milestone 5 ORM | Description |
| -------------------- | --------------- | ----------- |
| `Product` | `Ingredient` | Ingredient or supply item (e.g. beef loin, house sauce, takeout packaging). Unit of measure + category. |
| `InboundOrder` | `IngredientEntry` | Goods received from a supplier at a location |
| `OutboundOrder` | `IngredientExit` | Dish-prep consumption or recorded waste |
| `location` | location id 1–14 | Country (`CO`/`US`) and city |
| `supplier` | supplier directory | ~20 suppliers, different per country |

### `Product` (ORM: `Ingredient`)

| Field | Type | Notes |
| ----- | ---- | ----- |
| `id` | int (PK) | Emitted as `product_id` |
| `name` | string | Not emitted in high-volume telemetry |
| `category` | string | API: `meat`, `seafood`, `produce`, `sauce`, `beverage`, `packaging`, `cleaning` (course synonyms: `protein`≈`meat`/`seafood`, `vegetable`≈`produce`) |
| `unit` | string | e.g. `kg`, `litre`, `unit` |
| `current_stock` | float | Computed — never stored directly |
| `min_stock_threshold` | float | Alert threshold per location |
| `country` | string | Product catalogue country when present |

### `InboundOrder` (ORM: `IngredientEntry`)

| Field | Type | Notes |
| ----- | ---- | ----- |
| `id` | int (PK) | Emitted as `inbound_order_id` |
| `ingredient_id` | int | Emitted as `product_id` |
| `quantity` | float | |
| `supplier` | string | Emitted as `supplier_id` |
| `location_id` | int | 1–14 |
| `created_by` / `user_uuid` | string | Opaque TinyDB UUID |
| `created_at` | datetime (UTC) | |

### `OutboundOrder` (ORM: `IngredientExit`)

| Field | Type | Notes |
| ----- | ---- | ----- |
| `id` | int (PK) | Emitted as `outbound_order_id` |
| `ingredient_id` | int | Emitted as `product_id` |
| `quantity` | float | |
| `reason` | string | API: `consumption` \| `waste` only |
| `location_id` | int | 1–14 |
| `created_by` / `user_uuid` | string | Opaque TinyDB UUID |
| `created_at` | datetime (UTC) | |

---

## Course Floor Metrics (mandatory)

Instrument end-to-end (capture → storage). Design for aggregation by location, country, and week (future Felipe dashboard / Mariana weekly report).

| `event_type` | Fires when… | Business hypothesis | Decision it enables |
| ------------ | ----------- | ------------------- | ------------------- |
| `inbound_order_created` | Location registers supplier arrival | Know purchase volume by location and supplier | Consolidate purchasing (Lucía) |
| `outbound_order_created` | Location registers dish-prep consumption | Know consumption rate by location | Adjust auto order suggestion (Felipe) |
| `stock_waste_registered` | Location registers waste | Know loss volume, why, where | Prioritize waste audits (Felipe) |
| `stock_threshold_triggered` | Stock falls below configured minimum | Know shortfall frequency | Adjust threshold or replenishment |
| `direct_stock_edit_rejected` | Direct stock edit blocked | Detect bypass of traceability | Training / permissions (Jake) |
| `ingredient_price_variance_detected` | Inbound unit cost varies beyond threshold (default 10%) vs history for product/supplier | Detect abnormal price rises | Renegotiate or alternate supplier (Lucía, Mariana) |

**Waste split:** API `reason=consumption` → `outbound_order_created` only. API `reason=waste` → `stock_waste_registered` only (never both).

**Waste `reason` in telemetry:** target `expired` \| `kitchen_error` \| `theft_suspected`; interim `unspecified` until additive API `waste_subtype` (alignment decision 5).

---

## The Three Reporting KPIs

Course floor feeds these aggregates (and later executive reporting):

| # | KPI | Definition | Business decision | Primary events | Data origin |
| - | --- | ---------- | ----------------- | -------------- | ----------- |
| 1 | **Daily consumption rate by product and location** | Units consumed per product per location per day | Detect overconsumption; adjust supplier orders | `outbound_order_created` | `POST /inventory/orders/outbound` |
| 2 | **Stock-out frequency** | Times stock hit zero or `min_stock_threshold` | Identify under-stocked products; renegotiate | `stock_threshold_triggered`, `outbound_order_failed` | Stock recompute; outbound rejection |
| 3 | **Waste and loss ratio** | Wasted quantity vs total outbound movement | Flag abnormal waste; investigate | `stock_waste_registered`, `outbound_order_created` | Outbound commits |

---

## Phase 1 — Instrumentation Map

### Inventory flow (authenticated user → order complete)

Journey: **login → stock list → (optional location filter) → inbound/outbound form → order submit → stock recompute → threshold check → (optional price variance check)**.

| # | Point | System location | Event | Golden rule |
| - | ----- | --------------- | ----- | ----------- |
| 1 | Successful login | Backoffice auth after `POST /auth/login` | `user_login_succeeded` | Correlate consumption anomalies with staffing coverage. |
| 2 | Product stock list opened | `GET /inventory/products` + page | `ingredient_list_viewed` | Decide whether to simplify stock UI or add proactive alerts. |
| 3 | Location filter applied | Location selector | `location_filter_applied` | Prioritize location-specific training. |
| 4 | InboundOrder registered | `POST /inventory/orders/inbound` after commit | `inbound_order_created` | Consolidate purchasing and adjust delivery schedules (Lucía / Felipe). |
| 5 | InboundOrder rejected | Inbound validation / 404 | `inbound_order_failed` | Fix supplier data or retrain inbound entry. |
| 6 | Outbound consumption registered | Outbound commit, API `reason=consumption` | `outbound_order_created` | Detect overconsumption (KPI 1). |
| 7 | Waste registered | Outbound commit, API `reason=waste` | `stock_waste_registered` | Prioritize waste audits (KPI 3). |
| 8 | Outbound rejected | Validation or `InsufficientStockError` | `outbound_order_failed` | Distinguish data-entry errors vs shortages (KPI 2 leading). |
| 9 | Direct stock edit blocked | PATCH guard / UI | `direct_stock_edit_rejected` | Enforce training or tighten guards (Jake). |
| 10 | Minimum threshold crossed | Stock recompute after order | `stock_threshold_triggered` | Emergency replenishment (KPI 2). |
| 11 | Price variance detected | After inbound when cost jumps | `ingredient_price_variance_detected` | Alert Lucía / Mariana to renegotiate. |

### Backoffice opportunities (beyond course floor)

| # | Section | Event | Golden rule |
| - | ------- | ----- | ----------- |
| 1 | Authentication | `user_login_failed` | Detect credential issues or brute-force. |
| 2 | Authentication | `session_expired` | Adjust session TTL or save-draft on forms. |
| 3 | Navigation | `order_form_abandoned` | Fix UX friction blocking stock accuracy. |

### Candidate event disposition

| Candidate event | Decision | Notes |
| --------------- | -------- | ----- |
| `inbound_order_created` | **Keep (floor)** | Renamed from `supply_order_created` |
| `outbound_order_created` | **Keep (floor)** | Consumption only |
| `stock_waste_registered` | **Keep (floor)** | Split from former consumption+waste event |
| `stock_threshold_triggered` | **Keep (floor)** | Stream |
| `direct_stock_edit_rejected` | **Keep (floor)** | Stream |
| `ingredient_price_variance_detected` | **Keep (floor)** | New; stream |
| `outbound_order_failed` | **Keep (beyond floor)** | KPI 2 leading |
| `inbound_order_failed` | **Keep (beyond floor)** | Validation analytics |
| Auth / navigation trio | **Keep (beyond floor)** | Staffing, security, UX |

### Rejected candidate events

| Candidate event | Decision | Reason discarded |
| --------------- | -------- | ---------------- |
| `ingredient_search_typed` | **Discard** | Per-keystroke privacy; use `order_form_abandoned`. |
| `page_view` (generic) | **Discard** | No ops hypothesis; use domain events. |
| `ingredient_name_viewed` | **Discard** | Re-identification risk; use `product_id`. |
| `supplier_contact_clicked` | **Discard** | Supplier PII excluded; use `supplier_id`. |
| `stock_level_snapshot` (periodic) | **Discard** | Level spam; use edge-triggered threshold. |
| `raw_http_request` | **Discard** | Bodies/headers excluded. |

---

## Phase 2 — Event Envelope

### Mandatory envelope fields

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `eventId` | string (UUID v4) | ✅ | Unique idempotency key |
| `timestamp` | string (ISO 8601 UTC) | ✅ | Emission time |
| `sessionId` | string | ✅ | Opaque browser/API session id |
| `userId` | string | ✅ | TinyDB user UUID; `"anonymous"` only for pre-auth |
| `event_type` | string | ✅ | `entity_action` snake_case |
| `schemaVersion` | integer | ✅ | Floor inventory events use `2` |
| `requestId` | string | ✅ | Correlates API ↔ UI ↔ logs |
| `service` | string | ✅ | `backoffice` or `api` |
| `properties` | object | ✅ | Allowlist only |

### Correlation identifiers

| Field | API (server) | Backoffice (client) |
| ----- | ------------ | ------------------- |
| `sessionId` | `EmitContext` (`sess_` + hex) when no browser session | `sessionStorage` via `telemetry.ts` |
| `requestId` | Per handler or client `X-Request-Id` | Shared on order submits |
| `userId` | JWT UUID; `"anonymous"` pre-auth | Auth store after login |

### Wave 1 event catalog

Full allowlists: `docs/telemetry/event-schemas.json`.

| event_type | Floor? | Description | KPI / role |
| ---------- | ------ | ----------- | ---------- |
| `inbound_order_created` | ✅ | Inbound registered | Purchasing / indirect KPI 2 |
| `outbound_order_created` | ✅ | Consumption registered | KPI 1, 3 |
| `stock_waste_registered` | ✅ | Waste registered | KPI 3 |
| `stock_threshold_triggered` | ✅ | Low-stock edge trigger | KPI 2 |
| `direct_stock_edit_rejected` | ✅ | Blocked stock mutation | Governance |
| `ingredient_price_variance_detected` | ✅ | Unit cost spike | Procurement alert |
| `inbound_order_failed` | — | Inbound rejected | Validation |
| `outbound_order_failed` | — | Outbound rejected | KPI 2 leading |
| `user_login_succeeded` | — | Login ok | Staffing |
| `user_login_failed` | — | Login failed | Security |
| `session_expired` | — | Session timeout | UX |
| `ingredient_list_viewed` | — | Stock list opened | Navigation |
| `location_filter_applied` | — | Location filter | Segmentation |
| `order_form_abandoned` | — | Form idle abandon | UX |

---

## Phase 3 — Delivery Strategy

### Stream vs batch

| event_type | Processing | Justification |
| ---------- | ---------- | ------------- |
| `stock_threshold_triggered` | **Stream** | Same-shift replenishment |
| `outbound_order_failed` | **Stream** | Active shortage / bad entry |
| `direct_stock_edit_rejected` | **Stream** | Policy bypass |
| `ingredient_price_variance_detected` | **Stream** | Procurement alert |
| `user_login_failed` | **Stream** | Brute-force detection |
| `inbound_order_created` | **Batch** | Daily/weekly purchasing |
| `outbound_order_created` | **Batch** | Daily KPI 1 |
| `stock_waste_registered` | **Batch** | Weekly waste ratio |
| `inbound_order_failed` | **Batch** | Training analytics |
| Auth success / session / navigation | **Batch** | Daily–weekly product ops |

### Throttle / debounce

| event_type | Strategy |
| ---------- | -------- |
| `ingredient_list_viewed` | Debounce 30s per `(sessionId, location_id)` |
| `location_filter_applied` | Debounce 10s per `(sessionId, location_id)` |
| `order_form_abandoned` | Emit once per `(sessionId, form_type, product_id)` after 120s idle |
| `user_login_failed` | Throttle max 1 per `(source_ip_hash, 60s)` |
| `stock_threshold_triggered` | Dedupe per `(product_id, location_id, 24h)`; edge-trigger only |
| `ingredient_price_variance_detected` | Dedupe per `(product_id, supplier_id, location_id, 24h)` |

---

## Scope

### In scope

- Course floor metrics + three reporting KPIs
- Inventory + backoffice instrumentation maps
- Standard envelope and `event-schemas.json` v2
- Stream/batch and throttle rules
- Runbook (`docs/telemetry/telemetry-plan.md`)
- Alignment decision log

### Out of scope (design / later course work)

- Third-party analytics vendors
- Real-time executive dashboards (consume this data later)
- OpenTelemetry / distributed tracing
- Replacing `auth_audit` storage
- Rewriting Milestone 5 API reason enum
- Additive API `waste_subtype` (alignment decision 5 D)

---

## Required File Layout

```text
memory-bank/historical-reference/
  context-15-telemetry-plan.md              # this document (canonical design)
  context-15-course-alignment-plan.md       # locked remap decisions

docs/telemetry/
  telemetry-plan.md                         # operational runbook
  event-schemas.json                        # canonical contracts + allowlists (v2)
```

---

## Risks and Exclusions

### Privacy and sensitivity

- No emails, names, phone numbers, or free-text notes.
- No employee names or customer data in `properties`.
- `user_login_failed` — `failure_reason` enum only; never passwords.

### Dual-currency

- `currency` from `location_id` (1–9 → `COP`, 10–14 → `USD`).
- FX only in executive reporting — not in telemetry emit.

### Multi-location / country

- Inventory events require `location_id` and `country`.
- UI language (ES/EN) is independent from `country` — do not mix.

### Remaining follow-ups

- Until `waste_subtype` exists on API, emit `reason: unspecified` on `stock_waste_registered` while still registering API `waste` (decision 5 D).
- Typed waste seed reasons (`expired` / `kitchen_error` / `theft_suspected`) wait on that API addition.

### Data not captured

- Raw HTTP headers (except `source_ip_hash` for login throttle).
- Supplier contacts, incident free text, password-reset tokens.
- Per-keystroke form telemetry.

### Implementation status (course floor)

- ✅ Emitters use v2 `event_type`s; waste split to `stock_waste_registered`.
- ✅ Report/`analysis.py` queries v2 names and `product_id`.
- ✅ Price-variance emit + inbound `unit_cost` + seed fixtures.
- ✅ Telemetry seed includes threshold and price-variance demo rows.

---

## Acceptance Criteria

- Plan uses `Product` / `InboundOrder` / `OutboundOrder` in telemetry prose with Milestone ORM map.
- Six course floor events documented with hypothesis → decision.
- Three KPIs mapped to remapped primary events.
- `event-schemas.json` schemaVersion 2 includes floor allowlists (`country`, `product_id`, `product_category`, …).
- Waste split rules and C-now/D-later subtype path documented.
- Stream/batch justified per event with business urgency.
- Alignment plan indexed; Milestone 5 runtime contracts unchanged.

---

## Verification Checklist

1. `context-15-telemetry-plan.md` and `context-15-course-alignment-plan.md` indexed in `context-index.md`.
2. `event-schemas.json` includes ≥ 6 floor events with allowlists.
3. Each floor event survives the golden-rule test.
4. Location-scoped inventory schemas include `location_id`, `country`, `currency`.
5. API exit reasons remain `consumption` | `waste`; telemetry waste subtypes documented separately.
6. Stream events include threshold, failed outbound, direct edit, price variance, login failed.
7. Course-floor emitters, report metrics, and tests validated against `event-schemas.json` v2.

---

_Brasaland Digital — Internal document for 4Geeks Academy AI Engineering Track_
