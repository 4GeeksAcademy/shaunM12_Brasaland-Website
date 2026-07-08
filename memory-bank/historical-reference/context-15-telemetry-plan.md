# CONTEXT — Telemetry Phase 1: Company Telemetry Plan Design · Brasaland

## AI Engineering - 4Geeks Academy

> **Repository index:** `context-15-telemetry-plan.md`  
> **Companion docs:** `docs/telemetry/telemetry-plan.md`, `docs/telemetry/event-schemas.json`  
> **Related context:** `context-11-milestone-5-backend-inventory-management.md`, `context-12-milestone-5-backoffice-inventory-interface.md`  
> **Type:** Observability design + Wave 1 inventory instrumentation (partial)  
> **Status:** 🟢 Wave 1 inventory instrumentation implemented (see `services/api/telemetry/`)

> **Authority rule:** Milestone 5 contexts (`context-11-milestone-5-backend-inventory-management.md`, `context-12-milestone-5-backoffice-inventory-interface.md`) remain the runtime source of truth. This telemetry context is additive only and must not alter Milestone 5 API contracts.

---

## Business Objective

Brasaland is a grilled food restaurant chain with 14 locations across Colombia and Florida.  
Brasaland Digital (CTO Nicolás Park) built an inventory system that tracks ingredient stock via `Ingredient`, `SupplyOrder`, and `ConsumptionOrder` — enforcing the rule that stock levels are never edited directly.

Operations (Felipe Guerrero, Operations Director) and leadership (Mariana Restrepo, CEO) are asking questions the system cannot yet answer: daily outbound order volume, which ingredients accumulate validation errors, whether users attempt direct stock edits, and when minimum-stock alerts fire most often. The backoffice also lacks visibility into login failures, section usage, and abandoned flows.

This context defines the telemetry plan the team will implement: KPIs, events, envelopes, stream/batch routing, and exclusions.

---

## Locked Decisions

- **Canonical entity names:** `Ingredient`, `SupplyOrder`, `ConsumptionOrder` (not generic README names in schemas or events).
- **Event contracts live in `docs/telemetry/event-schemas.json`.** Application code must not invent parallel event names or payload shapes.
- **Standard envelope on every event:** `eventId`, `timestamp` (ISO 8601 UTC), `sessionId`, `userId`, `event_type`, `schemaVersion`, `requestId`, `properties`.
- **Naming convention:** `entity_action` snake_case (e.g. `supply_order_created`, `stock_threshold_triggered`).
- **Property allowlists are mandatory.** Only explicitly declared keys per event; nothing outside the allowlist.
- **No PII in telemetry.** `created_by` / `userId` are opaque TinyDB UUIDs — never names or email addresses.
- **Dual currency:** `currency` is `COP` for locations 1–9, `USD` for 10–14; derived from `location_id`, not client-side strings.
- **Multi-location:** location-scoped events must include `location_id` (integer 1–14).
- **Milestone 5 reason enum parity:** `ConsumptionOrder.reason` at API boundaries is `consumption` or `waste`.
- **Fail-open on client, fail-safe on server.** Telemetry must never block user flows.
- **Wave 1 inventory instrumentation is live** in `services/api/telemetry/` (6 events). Auth and backoffice client events remain design-only until hooked.

---

## Focus

Define exactly what data Brasaland captures to answer three inventory KPIs and selected backoffice operational questions — before writing instrumentation code.

Primary surfaces:

- **API:** `services/api/inventory/` (`/inventory` router)
- **Backoffice:** `uis/backoffice/app/inventory/`, auth flows, navigation
- **Schemas:** `docs/telemetry/event-schemas.json`

---

## Canonical Inventory Entities

| Generic name (README) | Brasaland entity name | Description |
| --------------------- | --------------------- | ----------- |
| `Product` | `Ingredient` | A tracked ingredient (e.g. beef cut, sauce, packaging material) |
| `InboundOrder` | `SupplyOrder` | A supplier delivery that increases ingredient stock |
| `OutboundOrder` | `ConsumptionOrder` | A kitchen consumption record that reduces ingredient stock |

### `Ingredient`

| Field | Type | Notes |
| ----- | ---- | ----- |
| `id` | int (PK) | |
| `name` | string | |
| `category` | string | `meat`, `produce`, `sauce`, `beverage`, `packaging`, `cleaning` |
| `unit` | string | e.g. `kg`, `litre`, `unit` |
| `current_stock` | float | Computed — never stored directly |
| `min_stock_threshold` | float | Alert threshold per location |
| `location_id` | int | 1–14 |
| `currency` | string | `COP` or `USD` |

### `SupplyOrder`

| Field | Type | Notes |
| ----- | ---- | ----- |
| `id` | int (PK) | |
| `ingredient_id` | int (FK → Ingredient) | |
| `quantity` | float | |
| `supplier_id` | string | Supplier identifier |
| `location_id` | int | 1–14 |
| `created_by` | string | Opaque TinyDB user UUID |
| `created_at` | datetime (UTC) | |

### `ConsumptionOrder`

| Field | Type | Notes |
| ----- | ---- | ----- |
| `id` | int (PK) | |
| `ingredient_id` | int (FK → Ingredient) | |
| `quantity` | float | |
| `reason` | string | `consumption`, `waste` |
| `location_id` | int | 1–14 |
| `created_by` | string | Opaque TinyDB user UUID |
| `created_at` | datetime (UTC) | |

---

## The Three KPIs

| # | KPI | Definition | Business decision it enables | Primary events | Data origin |
| - | --- | ---------- | ---------------------------- | -------------- | ----------- |
| 1 | **Daily consumption rate by ingredient and location** | Units consumed per ingredient per location per day (via `ConsumptionOrder` where `reason = consumption`) | Detect locations overconsuming relative to sales; adjust supplier orders | `consumption_order_created` | `POST /inventory/orders/outbound` |
| 2 | **Stock-out frequency** | Times an ingredient's stock hit zero or `min_stock_threshold` in a period | Identify chronically under-stocked ingredients; renegotiate supply contracts | `stock_threshold_triggered`, `consumption_order_failed` | Stock recompute after order commit; outbound rejection |
| 3 | **Waste and loss ratio** | Proportion of `ConsumptionOrder` with `reason = waste` vs total consumption | Flag abnormal waste patterns; trigger operational investigation | `consumption_order_created` | `POST /inventory/orders/outbound` |

---

## Phase 1 — Instrumentation Map

### Inventory flow (authenticated user → order complete)

Journey: **login → stock list → (optional location filter) → inbound/outbound form → order submit → stock recompute → threshold check**.

| # | Point | System location | Event | Golden rule |
| - | ----- | --------------- | ----- | ----------- |
| 1 | Successful login | Backoffice auth + `POST /auth/login` | `user_login_succeeded` | We capture `user_login_succeeded` because we need to know **which operators are active per location per day**, which allows us to make the decision **to correlate consumption anomalies with staffing coverage**. |
| 2 | Ingredient stock list opened | `GET /inventory/products` + `/inventory/products` | `ingredient_list_viewed` | We capture `ingredient_list_viewed` because we need to know **how often managers review stock before ordering**, which allows us to make the decision **whether to simplify the stock UI or add proactive alerts**. |
| 3 | Location filter applied | `GET /inventory/products?location_id=` + location selector | `location_filter_applied` | We capture `location_filter_applied` because we need to know **which locations receive the most operational attention**, which allows us to make the decision **to prioritize location-specific training**. |
| 4 | SupplyOrder registered | `POST /inventory/orders/inbound` after commit | `supply_order_created` | We capture `supply_order_created` because we need to know **inbound volume and timing per ingredient and location**, which allows us to make the decision **to adjust supplier delivery schedules before stock-outs**. |
| 5 | SupplyOrder rejected | `POST /inventory/orders/inbound` on validation, unknown supplier, or 404 | `supply_order_failed` | We capture `supply_order_failed` because we need to know **which inbound orders fail validation and why (supplier, ingredient, quantity)**, which allows us to make the decision **to fix supplier-directory data or retrain managers on inbound entry (secondary to KPI 2)**. |
| 6 | ConsumptionOrder registered | `POST /inventory/orders/outbound` after commit | `consumption_order_created` | We capture `consumption_order_created` because we need to know **daily consumption by ingredient, location, and reason**, which allows us to make the decision **to detect overconsumption and abnormal waste (KPIs 1 and 3)**. |
| 7 | ConsumptionOrder rejected | `POST /inventory/orders/outbound` on validation or insufficient stock | `consumption_order_failed` | We capture `consumption_order_failed` because we need to know **which ingredients fail validation or exceed available stock**, which allows us to make the decision **to investigate data-entry errors vs real shortages (KPI 2 leading indicator)**. |
| 8 | Direct stock edit blocked | API/UI attempt to mutate `current_stock` outside an order | `direct_stock_edit_rejected` | We capture `direct_stock_edit_rejected` because we need to know **whether users attempt to bypass the order-only stock rule**, which allows us to make the decision **to enforce training or tighten API guards**. |
| 9 | Minimum threshold crossed | Repository stock recompute after order commit | `stock_threshold_triggered` | We capture `stock_threshold_triggered` because we need to know **when and where low-stock alerts fire (edge-triggered: stock crosses downward through `min_stock_threshold`)**, which allows us to make the decision **to trigger emergency supply orders (KPI 2)**. |

### Backoffice opportunities (beyond inventory)

| # | Section | Event | Golden rule |
| - | ------- | ----- | ----------- |
| 1 | Authentication | `user_login_failed` | We capture `user_login_failed` because we need to know **daily failed login volume and patterns**, which allows us to make the decision **to detect credential issues or brute-force attempts at specific locations**. |
| 2 | Authentication | `session_expired` | We capture `session_expired` because we need to know **how often operators lose work mid-shift due to timeout**, which allows us to make the decision **to adjust session TTL or add save-draft UX on order forms**. |
| 3 | Navigation | `order_form_abandoned` | We capture `order_form_abandoned` because we need to know **which SupplyOrder or ConsumptionOrder flows are started but not submitted**, which allows us to make the decision **to fix UX friction that blocks stock accuracy**. |

### Candidate event disposition

| Candidate event | Decision | Notes |
| --------------- | -------- | ----- |
| `supply_order_created` | **Keep** | Wave 1 schema; batch processing |
| `consumption_order_created` | **Keep** | Primary KPI 1 + 3 feed |
| `stock_threshold_triggered` | **Keep** | Primary KPI 2 feed; stream processing |
| `direct_stock_edit_rejected` | **Keep** | Governance signal; stream processing |
| `consumption_order_failed` | **Keep** | KPI 2 leading indicator; stream processing |
| `supply_order_failed` | **Keep (secondary)** | Validation analytics; batch only; not KPI-primary |
| `user_login_succeeded` | **Keep** | Staffing correlation; batch |
| `user_login_failed` | **Keep** | Security; stream |
| `session_expired` | **Keep** | UX; batch |
| `ingredient_list_viewed` | **Keep** | Navigation; batch |
| `order_form_abandoned` | **Keep** | UX funnel; batch |
| `location_filter_applied` | **Keep** | Segmentation; batch |

### Rejected candidate events

Events considered during design but **not** included in Wave 1 — each rejected for a documented reason:

| Candidate event | Decision | Reason discarded |
| --------------- | -------- | ---------------- |
| `ingredient_search_typed` | **Discard** | Per-keystroke search telemetry violates privacy exclusions; no KPI maps to raw typing. `order_form_abandoned` summary is sufficient for UX friction. |
| `page_view` (generic) | **Discard** | Too broad — no hypothesis tied to a Brasaland ops decision. Replaced by domain-specific events (`ingredient_list_viewed`, `location_filter_applied`). |
| `ingredient_name_viewed` | **Discard** | Ingredient names in high-volume navigation events add no KPI value and increase re-identification risk; use `ingredient_id` only. |
| `supplier_contact_clicked` | **Discard** | Supplier PII (contacts) explicitly excluded; procurement analytics use `supplier_id` on `supply_order_created` instead. |
| `stock_level_snapshot` (periodic) | **Discard** | Level-triggered stock polling would spam telemetry and duplicate computed stock; `stock_threshold_triggered` uses edge-trigger on order commit only. |
| `raw_http_request` | **Discard** | Raw headers and bodies excluded; only `source_ip_hash` on `user_login_failed` for throttle keying. |

---

## Phase 2 — Event Envelope

### Mandatory envelope fields

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `eventId` | string (UUID v4) | ✅ | Unique idempotency key |
| `timestamp` | string (ISO 8601 UTC) | ✅ | Emission time |
| `sessionId` | string | ✅ | Opaque browser/API session id |
| `userId` | string | ✅ | TinyDB user UUID; `"anonymous"` only for pre-auth events |
| `event_type` | string | ✅ | `entity_action` snake_case |
| `schemaVersion` | integer | ✅ | Starts at `1`; increment on breaking changes |
| `requestId` | string | ✅ | Correlates API request ↔ UI action ↔ logs |
| `properties` | object | ✅ | Event-specific payload (allowlist only) |

### Correlation identifiers (`sessionId`, `requestId`)

| Field | API (server) | Backoffice (client) |
| ----- | ------------ | ------------------- |
| `sessionId` | Generated per authenticated request via `EmitContext` (`sess_` + random hex) when no browser session exists | Stable per browser tab from `uis/backoffice/lib/telemetry/session.ts` (planned) |
| `requestId` | Generated per API handler invocation (`req_` + random hex) | Propagated from client `X-Request-Id` header when present; else generated client-side |
| `userId` | TinyDB user UUID from JWT; `"anonymous"` for pre-auth events only | Same UUID from auth store after login |

---

### Wave 1 event catalog

Full schemas with property allowlists are in `docs/telemetry/event-schemas.json`.

| event_type | Description | KPI link | Sensitivity |
| ---------- | ----------- | -------- | ----------- |
| `supply_order_created` | SupplyOrder successfully registered | Indirect KPI 2 | Standard |
| `consumption_order_created` | ConsumptionOrder successfully registered | KPI 1, KPI 3 | Standard |
| `stock_threshold_triggered` | Stock at or below `min_stock_threshold` | KPI 2 | Standard |
| `direct_stock_edit_rejected` | Blocked direct stock mutation | Governance | Standard |
| `consumption_order_failed` | Outbound order rejected | KPI 2 leading | Standard |
| `supply_order_failed` | Inbound order rejected | Validation analytics | Standard |
| `user_login_succeeded` | Successful backoffice login | Staffing correlation | Standard |
| `user_login_failed` | Failed backoffice login | Security | Standard |
| `session_expired` | Session timed out | UX | Standard |
| `ingredient_list_viewed` | Ingredient stock list opened | Navigation / UX | Standard |
| `location_filter_applied` | Location filter changed on inventory pages | Segmentation | Standard |
| `order_form_abandoned` | Order form started but not submitted | UX / data quality | Standard |

---

## Phase 3 — Delivery Strategy

### Stream vs batch (business justification)

| event_type | Processing | Justification |
| ---------- | ---------- | ------------- |
| `stock_threshold_triggered` | **Stream** | Stock-out at a high-volume Miami location on Friday night needs same-shift replenishment — not a weekly batch. |
| `consumption_order_failed` | **Stream** | Insufficient-stock failures signal an active operational crisis. |
| `direct_stock_edit_rejected` | **Stream** | Policy bypass attempts require near-real-time visibility. |
| `user_login_failed` | **Stream** | Brute-force spike detection cannot wait for nightly ETL. |
| `supply_order_created` | **Batch** (hourly) | Procurement decisions are daily/weekly. |
| `consumption_order_created` | **Batch** (hourly) | KPI 1 and KPI 3 are daily aggregates. |
| `supply_order_failed` | **Batch** | Validation errors inform training; not time-critical. |
| `user_login_succeeded` | **Batch** | Staffing correlation is analyzed daily. |
| `session_expired` | **Batch** | Session TTL tuning uses weekly aggregates. |
| `ingredient_list_viewed` | **Batch** | Navigation analytics; no urgent ops decision. |
| `location_filter_applied` | **Batch** | Weekly ops segmentation. |
| `order_form_abandoned` | **Batch** | UX funnel analysis is weekly product work. |

### Throttle / debounce

| event_type | Strategy |
| ---------- | -------- |
| `ingredient_list_viewed` | Debounce 30s per `(sessionId, location_id)` |
| `location_filter_applied` | Debounce 10s per `(sessionId, location_id)` |
| `order_form_abandoned` | Emit once per `(sessionId, form_type, ingredient_id)` after 120s idle |
| `user_login_failed` | Throttle max 1 per `(source_ip_hash, 60s)` |
| `stock_threshold_triggered` | Dedupe per `(ingredient_id, location_id, 24h)` unless stock recovers and retriggers. **Edge-trigger only:** emit when `stock_before > min_stock_threshold` and `stock_after <= min_stock_threshold` — not while stock remains low. |

---

## Scope

### In scope

- KPI definitions and event-to-KPI mapping
- Inventory flow instrumentation map (9 points)
- Backoffice instrumentation (3 non-inventory opportunities)
- Standard event envelope and Wave 1 schemas (`docs/telemetry/event-schemas.json`)
- Stream/batch routing and throttle rules
- Operational runbook outline (`docs/telemetry/telemetry-plan.md`)
- Risks, exclusions, and implementation-gap notes

### Out of scope (Phase 1)

- Instrumentation code (emitters, sinks, SDK)
- Third-party vendor selection (GA4, Datadog, Mixpanel, etc.)
- Real-time executive dashboards
- OpenTelemetry / distributed tracing
- Replacing existing `auth_audit` storage

---

## Required File Layout

```text
memory-bank/historical-reference/
  context-15-telemetry-plan.md     # this document (canonical design)

docs/telemetry/
  telemetry-plan.md                # operational runbook (sinks, env, sampling)
  event-schemas.json               # canonical event contracts + allowlists
```

---

## Risks and Exclusions

### Privacy and sensitivity

- No emails, names, phone numbers, or free-text notes in telemetry.
- `consumption_order_created` follows Milestone 5 reason values (`consumption`, `waste`) and remains standard telemetry.
- `user_login_failed` carries `failure_reason` enum only — never attempted passwords.

### Dual-currency

- `currency` derived from `location_id` (1–9 → `COP`, 10–14 → `USD`).
- Cross-location cost comparisons require explicit FX in the analytics layer — not in raw events.

### Multi-location

- Operational events require `location_id` for country/city segmentation.
- Events without location context use `location_id: null` and are excluded from location KPI rollups.

### Data not captured

- Raw HTTP headers (except one-way `source_ip_hash` for login throttle).
- Ingredient unit costs until procurement exposes authoritative pricing.
- Incident descriptions, supplier contacts, password-reset tokens.
- Per-keystroke form telemetry (only `order_form_abandoned` summary).

See also **Rejected candidate events** (Phase 1 instrumentation map) for events explicitly considered and discarded during design.

### Implementation gaps (pre-instrumentation)

- ~~`direct_stock_edit_rejected` requires explicit API guard on stock mutation attempts.~~ ✅ Done
- ~~API paths today use `IngredientEntry`/`IngredientExit`; telemetry events use canonical `SupplyOrder`/`ConsumptionOrder` names.~~ ✅ Mapped in emitters
- Backoffice client events and auth login telemetry remain pending.

---

## Acceptance Criteria

- Plan references `Ingredient`, `SupplyOrder`, `ConsumptionOrder` by canonical name.
- All three KPIs mapped to events and system origins.
- ≥ 5 instrumentation points with completed golden-rule sentences.
- ≥ 2 non-inventory backoffice opportunities documented.
- Standard envelope defined with all mandatory fields.
- `docs/telemetry/event-schemas.json` contains ≥ 5 complete schemas with property allowlists.
- Stream/batch decision per event with business (not technical) justification.
- Risks section covers dual-currency, multi-location, and exclusions without conflicting with Milestone 5 runtime contracts.

---

## Verification Checklist

1. `context-15-telemetry-plan.md` indexed in `context-index.md`.
2. `docs/telemetry/event-schemas.json` validates Wave 1 catalog (≥ 5 events).
3. Each kept event survives the golden-rule test (hypothesis → decision).
4. Every location-scoped schema includes `location_id` and `currency` where applicable.
5. Consumption reason values align with Milestone 5 (`consumption`, `waste`) and legacy aliases are documented.
6. Stream events (`stock_threshold_triggered`, `consumption_order_failed`, `direct_stock_edit_rejected`, `user_login_failed`) have business urgency documented.
7. Throttle/debounce rules documented for high-frequency events.
8. Implementation gaps listed before instrumentation sprint starts.

---

_Brasaland Digital — Internal document for 4Geeks Academy AI Engineering Track_
