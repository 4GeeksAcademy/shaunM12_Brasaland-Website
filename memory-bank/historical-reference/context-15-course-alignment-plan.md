# CONTEXT — Telemetry Course Floor Alignment · Brasaland

## AI Engineering - 4Geeks Academy

> **Repository index:** `context-15-course-alignment-plan.md`  
> **Updates:** `context-15-telemetry-plan.md`, `context-15-telemetry-frontend-capture.md`, `context-15-backend-storage.md`, `context-15-telemetry-report.md`, `docs/telemetry/telemetry-plan.md`, `docs/telemetry/event-schemas.json`  
> **Related:** Milestone 5 (`context-11`, `context-12`); course telemetry CONTEXT (Plan · Capture · Storage · Report)  
> **Type:** Decision log + remap + update checklist  
> **Status:** 🟢 Docs, schemas, emitters, analysis, tests, and seeds aligned to course floor (`schemaVersion` 2)  
> **Branch:** `telemetry-course-alignment`

---

## Authority stacking (locked)

| Layer | Canonical for | Source |
| ----- | ------------- | ------ |
| Inventory API, models, stock rules, exit `reason` enum | Milestone 5 | `context-11`, `context-12` |
| Telemetry `event_type`s, envelopes, allowlists, Wave contracts | Course floor + this alignment | `event-schemas.json` after this pass |
| Design why/what | Context-15 telemetry plan | `context-15-telemetry-plan.md` |
| Operational how | Telemetry runbook | `docs/telemetry/telemetry-plan.md` |

**Rule:** Course owns telemetry contracts. Milestone 5 owns inventory/API. Telemetry must not redefine stock math, order routes, or the API exit reason enum (`consumption` | `waste`).

---

## Locked decisions

| # | Topic | Lock |
| - | ----- | ---- |
| 1 | Authority | **B** — Course = telemetry; Milestone 5 = inventory/API |
| 2 | Entity vocabulary | **B** — Telemetry docs use `Product` / `InboundOrder` / `OutboundOrder` + ORM map |
| 3 | `event_type` names | **B** — Rename to course names |
| 4 | Waste split | **B** — Waste emits only `stock_waste_registered` |
| 5 | Waste reasons | **C now / D later** — API keeps `waste`; telemetry targets course subtypes; additive `waste_subtype` later |
| 6 | Property keys | **B** — `product_id` / order ids; values = Milestone ids; `schemaVersion` → `2` |
| 7 | Floor properties | **A+B** — Required; derive `country` / `currency` / `product_category` server-side |
| 8 | Categories | **A** — Emit Milestone/API category strings + synonym table |
| 9 | Price variance | **B** — Full contract in plan/schemas |
| 10 | Extended catalog | **B** — Keep `*_failed`, auth, navigation beyond floor |
| 11 | KPIs | **C** — Course floor table + three reporting KPIs on top |
| 12 | Seed | **B** — Gap checklist vs current seed |
| 13 | Doc scope | **B** — This file + schemas + context-15 + telemetry-plan (code later) |
| 14 | History | **A** — No migrator; regenerate local `telemetry_events` as needed |

---

## Entity map

| Telemetry / API name (course) | Milestone 5 ORM | Role |
| ----------------------------- | --------------- | ---- |
| `Product` | `Ingredient` | Catalogue item |
| `InboundOrder` | `IngredientEntry` | Supplier delivery (stock in) |
| `OutboundOrder` | `IngredientExit` | Consumption or waste (stock out) |
| `location` | location id 1–14 | Country (`CO`/`US`) + city |
| `supplier` | supplier directory | ~20 suppliers, country-scoped |

---

## Event remap

| Previous `event_type` | New `event_type` | Emit rule |
| --------------------- | ---------------- | --------- |
| `supply_order_created` | `inbound_order_created` | After successful inbound commit |
| `consumption_order_created` (`reason=consumption`) | `outbound_order_created` | After outbound commit when API `reason=consumption` |
| `consumption_order_created` (`reason=waste`) | `stock_waste_registered` | After outbound commit when API `reason=waste` — **do not** also emit `outbound_order_created` |
| `supply_order_failed` | `inbound_order_failed` | Inbound validation / not found (beyond floor) |
| `consumption_order_failed` | `outbound_order_failed` | Outbound validation / insufficient stock (beyond floor) |
| `stock_threshold_triggered` | same | Edge-trigger after order commit |
| `direct_stock_edit_rejected` | same | Blocked direct stock mutation |
| — | `ingredient_price_variance_detected` | Inbound unit cost vs historical for product+supplier exceeds threshold (default 10%) |

Auth/navigation events keep names; `order_form_abandoned.form_type` uses `InboundOrder` / `OutboundOrder`.

---

## Waste reason path (C now / D later)

| Phase | API | Telemetry `stock_waste_registered.properties.reason` |
| ----- | --- | ---------------------------------------------------- |
| **Now (C)** | `reason: waste` only | Target allowlist: `expired` \| `kitchen_error` \| `theft_suspected`. Until subtype exists, emit `unspecified` |
| **Later (D)** | Additive optional `waste_subtype` on outbound create | Copy subtype into telemetry; stock rules unchanged |

Never replace Milestone API `waste` with the three course values as the sole exit reason.

---

## Category synonyms (decision 8)

Emit Milestone/API categories in `product_category`. Course wording is a reporting synonym only:

| API / telemetry value | Course synonym |
| --------------------- | -------------- |
| `meat` | `protein` |
| `seafood` | `protein` (seafood stays distinct in API) |
| `produce` | `vegetable` |
| `sauce` | `sauce` |
| `beverage` | `beverage` |
| `packaging` | `packaging` |
| `cleaning` | `cleaning` |

---

## Mandatory course floor metrics

These must be instrumented end-to-end (capture → storage) and designed for aggregation by location, country, and week:

| `event_type` | Fires when… | Business hypothesis | Decision enabled |
| ------------ | ----------- | ------------------- | ---------------- |
| `inbound_order_created` | Location registers supplier goods | Know what is purchased by location and supplier | Consolidate purchasing (Lucía) |
| `outbound_order_created` | Location registers dish-prep consumption | Know consumption rate by location | Adjust auto replenishment (Felipe) |
| `stock_waste_registered` | Location registers waste | Know loss volume, why, where | Prioritize waste audits (Felipe) |
| `stock_threshold_triggered` | Stock crosses below minimum | Know shortfall frequency | Adjust threshold or replenishment |
| `direct_stock_edit_rejected` | Direct stock edit blocked | Know traceability bypass attempts | Reinforce training/permissions (Jake) |
| `ingredient_price_variance_detected` | Inbound unit cost varies beyond threshold vs history | Detect abnormal ingredient price rises | Renegotiate / alternate supplier (Lucía, Mariana) |

**Minimum floor properties** (plus standard envelope): `location_id`, `country` (`CO`/`US`), `product_id`, `product_category`, `quantity`, `unit`, `currency` (`COP`/`USD`). Waste also needs `reason` (target subtypes above). No employee names or customer data.

**Constraints:** no FX conversion at telemetry layer; stock never modified outside orders; UI language ≠ `country`.

---

## Price variance contract (decision 9)

| Field | Rule |
| ----- | ---- |
| Trigger | After successful inbound when `unit_cost` (or equivalent) differs from historical reference for `(product_id, supplier_id)` by more than `threshold_pct` (default **10**) |
| Comparison | Same `currency` only — never convert COP↔USD in the emitter |
| Historical reference | Prior successful inbound unit costs for same product+supplier (define window in implementation; document when coding) |
| Processing | **Stream** (ops alert) |
| Seed | At least one inbound that crosses the threshold |

---

## Three reporting KPIs (on top of floor)

| # | KPI | Primary events after remap |
| - | --- | -------------------------- |
| 1 | Daily consumption rate by product and location | `outbound_order_created` |
| 2 | Stock-out frequency | `stock_threshold_triggered`, `outbound_order_failed` (leading) |
| 3 | Waste and loss ratio | `stock_waste_registered` vs consumption volume (`outbound_order_created` + waste quantities) |

---

## Seed acceptance gap checklist (decision 12)

Course asks for at least: 8–10 products across ≥3 categories; 3 locations (CO + US); 15–20 inbound; 15–20 outbound including ≥3 waste with distinct reasons; ≥2 threshold triggers; ≥1 price variance.

| Criterion | Current seed posture | Gap |
| --------- | -------------------- | --- |
| 8–10+ products, ≥3 categories | Large catalogue (meat, produce, sauce, packaging, …) | Met |
| ≥3 locations CO + US | Locations 1–14 seeded; CO and US present | Met |
| 15–20 inbound | Explicit rows + generated fill | Likely met; confirm count in implementation pass |
| 15–20 outbound | Explicit + generated | Likely met; confirm count |
| ≥3 waste with distinct reasons | API `reason=waste` + telemetry `unspecified`; typed subtypes pending decision 5 D | **Partial** — typed reasons wait on `waste_subtype` |
| ≥2 `stock_threshold_triggered` | Overrides + telemetry seed rows / edge-trigger emit path | **Met** for demo (telemetry seed + emit path) |
| ≥1 price variance | Inbound `unit_cost` seed pairs + emit + telemetry seed row | **Met** |

---

## Update order (this pass)

1. ✅ This alignment plan  
2. ✅ `docs/telemetry/event-schemas.json` (`schemaVersion` 2, remapped events)  
3. ✅ `context-15-telemetry-plan.md`  
4. ✅ `docs/telemetry/telemetry-plan.md`  
5. ✅ `context-index.md` link  
6. ✅ `context-15-telemetry-frontend-capture.md`  
7. ✅ `context-15-backend-storage.md`  
8. ✅ `context-15-telemetry-report.md`  

## Deferred (intentional)

- Additive API `waste_subtype` (decision 5 D) + three typed waste seed reasons  
- Historical `telemetry_events` migrator (decision 14 A — regenerate instead)  
- Any remaining pipeline design docs not present on this branch  

---

## Implementation follow-ups

1. ~~Rename emit calls to new `event_type`s; split waste emit path.~~ ✅  
2. ~~Derive and attach floor properties server-side.~~ ✅  
3. ~~Implement price-variance detector on inbound.~~ ✅  
4. ~~Update KPI queries in `analysis.py`.~~ ✅  
5. ~~Regenerate local telemetry data; update tests.~~ ✅  
6. When ready: additive `waste_subtype` on outbound API + seed three distinct subtypes.

---

_Brasaland Digital — Internal alignment document for 4Geeks Academy AI Engineering Track_
