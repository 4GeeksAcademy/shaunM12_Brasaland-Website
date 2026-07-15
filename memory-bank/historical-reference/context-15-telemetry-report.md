# CONTEXT — Brasaland · Telemetry Phase 4: Report from the Data

## AI Engineering - 4Geeks Academy

> **Repository index:** `context-15-telemetry-report.md`  
> **Companion docs:** `memory-bank/historical-reference/context-15-telemetry-plan.md`, `memory-bank/historical-reference/context-15-course-alignment-plan.md`, `memory-bank/historical-reference/context-15-telemetry-frontend-capture.md`, `memory-bank/historical-reference/context-15-backend-storage.md`, `docs/telemetry/telemetry-plan.md`, `docs/telemetry/event-schemas.json`  
> **Type:** Telemetry analysis pipeline + reporting endpoint  
> **Status:** 🟢 Report endpoint live; KPI queries on course-floor events (`schemaVersion` 2)

> **Authority rule:** Milestone 5 contexts govern runtime inventory semantics; this reporting phase enriches observability and must not change API behavior. Course owns telemetry `event_type`s and report property keys (`context-15-course-alignment-plan.md`).

---

## Your Company

**Brasaland** is a grilled food restaurant chain with 14 locations across Colombia and Florida. You are part of **Brasaland Digital**. The `telemetry_events` table is populated with real events from the backoffice. This phase builds the pipeline that converts events into metrics for Felipe Guerrero (Operations Director) and Mariana Restrepo (CEO).

---

## Scope of This Phase

1. Build `services/api/telemetry/analysis.py` with KPI metric functions using Pandas.
2. Implement `GET /telemetry/report` in FastAPI to return grouped KPI outputs.
3. Add a 60-second in-memory cache keyed by report period.
4. Validate end-to-end metric outputs with temporal dimensions.

---

## Locked Decisions

- Metrics are computed in analysis functions, not embedded inline in endpoint logic.
- Endpoint resolves a single report period and passes it to every metric function.
- Timestamp conversion with `pd.to_datetime(..., utc=True)` is required before grouping.
- SQL must pre-filter by `event_type` and timestamp window (`start_date <= ts < end_date`).
- Metric functions are deterministic and side-effect free.
- Metric calculations must use Pandas vectorized operations (`groupby`, `agg`, `count`, `sum`, `mean`) instead of loops.
- KPI contracts use remapped `schemaVersion` 2 event names and `product_id` in report rows (Milestone 5 HTTP API may still use `ingredient_id`).

---

## Important Note on Examples

All snippets and payloads in this document are **reference only**.  
Implementation must follow the KPI contracts from Phase 1 and allowlist semantics from `docs/telemetry/event-schemas.json` (`schemaVersion` 2).

Do not hardcode sample values from examples.

---

## The Three Required KPI Metrics

These metrics implement the KPI contracts from `context-15-telemetry-plan.md` (Phase 1), remapped per `context-15-course-alignment-plan.md`.

## Metric 1 — Daily Consumption by Product and Location (KPI 1)

**Business question:** how many units were consumed per product per location per day?  
**KPI mapping:** Daily consumption rate by product and location.

### Function contract

```python
def daily_consumption_by_product_and_location(start_date, end_date) -> list[dict]:
    ...
```

### Required behavior

- SQL load:
  - `event_type = 'outbound_order_created'`
  - `timestamp >= start_date` and `timestamp < end_date`
- Pandas:
  - convert `timestamp` with UTC
  - derive daily date key from timestamp
  - extract `location_id`, `product_id`, `quantity` from `tags`
  - drop null `location_id`, `product_id`, or `quantity` rows
- Grouping:
  - `groupby(['date', 'product_id', 'location_id'])['quantity'].sum()`
- Output:
  - list of dicts with `date`, `product_id`, `location_id`, `quantity`

Note: `outbound_order_created` is consumption-only. Do not expect or filter `reason=waste` on this event.

## Metric 2 — Stock-Out Frequency (KPI 2)

**Business question:** how often did stock hit the minimum threshold or fail for insufficient stock?  
**KPI mapping:** Stock-out frequency.

### Function contract

```python
def stock_out_frequency(start_date, end_date) -> list[dict]:
    ...
```

### Required behavior

- SQL load:
  - `event_type IN ('stock_threshold_triggered', 'outbound_order_failed')`
  - `timestamp >= start_date` and `timestamp < end_date`
- Pandas:
  - convert timestamp UTC
  - derive `date`
  - extract `location_id`, `product_id`, `error_code` from `tags`
  - keep `stock_threshold_triggered` rows and `outbound_order_failed` rows where `error_code = 'insufficient_stock'`
  - drop null `location_id` or `product_id` rows
- Grouping:
  - `groupby(['date', 'product_id', 'location_id'])['id'].count()`
- Output:
  - list of dicts with `date`, `product_id`, `location_id`, `count`

## Metric 3 — Waste and Loss Ratio (KPI 3)

**Business question:** what proportion of outbound movement was waste vs total outbound volume?  
**KPI mapping:** Waste and loss ratio.

### Function contract

```python
def waste_loss_ratio(start_date, end_date) -> list[dict]:
    ...
```

### Required behavior

- SQL load:
  - `event_type IN ('stock_waste_registered', 'outbound_order_created')`
  - `timestamp >= start_date` and `timestamp < end_date`
- Pandas:
  - convert timestamp UTC
  - derive `date`
  - extract `location_id`, `quantity` from `tags`
  - drop null `location_id` or `quantity` rows
- Grouping:
  - `groupby(['date', 'location_id'])` with `waste_quantity = sum(quantity where event_type = stock_waste_registered)` and `total_quantity = sum(quantity)` across both event types
  - compute `ratio = waste_quantity / total_quantity`
- Output:
  - list of dicts with `date`, `location_id`, `waste_quantity`, `total_quantity`, `ratio`

Note: API still uses `reason: waste` on outbound create; telemetry stores waste only as `stock_waste_registered` (interim `reason` allowlist value: `unspecified`). Do not instruct emitting `reason=waste` on `outbound_order_created`.

---

## Additional Activity — Auth Failure Rate (Optional)

If authentication telemetry is instrumented, add:

```python
def auth_failure_rate_per_day(start_date, end_date) -> list[dict]:
    ...
```

### Metric intent

- Load `event_type IN ('user_login_succeeded', 'user_login_failed')`
- Group by day
- Compute `failure_rate = failed / total`
- Return JSON-serializable records under `auth_failure_rate_per_day`

This metric is **not** one of the three Phase 1 KPIs.

---

## Business Constraints for Your Pipeline

- `location_id` and `product_id` must be extracted from `tags`, not from fixed SQL columns.
- Consumption and stock-out metrics must preserve location segmentation so Colombia and Florida can be compared.
- Temporal grouping is mandatory; a global scalar count without time context is not a KPI metric.
- KPI 1 uses `outbound_order_created` only; KPI 3 uses `stock_waste_registered` for the waste numerator and both waste + consumption events for total volume.

---

## Expected JSON Output Shape (Reference Only)

```json
{
  "period": { "from": "2025-01-13", "to": "2025-01-20" },
  "metrics": {
    "daily_consumption_by_product_and_location": [
      { "date": "2025-01-13", "product_id": 7, "location_id": 3, "quantity": 42.0 }
    ],
    "stock_out_frequency": [
      { "date": "2025-01-13", "product_id": 7, "location_id": 3, "count": 2 }
    ],
    "waste_loss_ratio": [
      {
        "date": "2025-01-13",
        "location_id": 3,
        "waste_quantity": 5.0,
        "total_quantity": 50.0,
        "ratio": 0.1
      }
    ],
    "auth_failure_rate_per_day": [
      { "date": "2025-01-13", "total": 20, "failed": 3, "failure_rate": 0.15 }
    ]
  }
}
```

---

## Phase 1 — Analysis Pipeline with Pandas

Create `services/api/telemetry/analysis.py` with three KPI metric functions (and one optional auth metric).

Each function must:

- receive `start_date` and `end_date` (inclusive start, exclusive end, UTC)
- pre-filter events in SQL by event type and timestamp range
- load into DataFrame
- convert timestamp to UTC datetime before grouping
- extract needed dimensions from `tags`
- drop null dimension rows where metric requires dimensions
- group and aggregate with Pandas operations only
- return JSON-serializable list via `.reset_index().to_dict(orient='records')`

Constraints:

- independent and side-effect free
- deterministic for same inputs
- no manual loop aggregation logic

---

## Phase 2 — Report Endpoint

Create `GET /telemetry/report` in FastAPI:

- accept optional `start_date` and `end_date` (ISO 8601)
- default to last 7 days if missing:
  - `start_date = now_utc - 7d`
  - `end_date = now_utc`
- resolve period once and pass to all metric functions
- return combined report JSON:
  - `period`
  - `metrics`
- do not recompute on every request:
  - in-memory cache
  - 60-second TTL
  - cache key includes start/end period values

Compatibility note: endpoint response remains JSON; metric values must always be serializable.

---

## Phase 3 — End-to-End Verification

1. Generate real events through backoffice:
   - at least one inbound order
   - at least one outbound consumption order
   - preferably one waste registration
2. Query `telemetry_events` to confirm source rows exist for report window.
3. Call `GET /telemetry/report` and validate:
   - date grouping present
   - location grouping present where expected
   - ratios mathematically consistent
4. Validate cache behavior:
   - repeated same-period request within TTL returns cached response
   - after TTL, report recalculates
5. (Optional) validate auth failure metric if implemented.

---

## Reference Appendix — Metric Formula Guide (Non-Normative)

The following image is included as **reference only** to support implementation understanding.  
It does not replace the formal requirements in this context.

![Metric formula reference](/home/codespace/.cursor/projects/workspaces-shaunM12-Brasaland-Website/assets/Screenshot_2026-07-08_at_11.36.30_AM-696eb212-7694-4fa5-ba41-cb6775651692.png)

Key reference takeaways:

- keep temporal filtering (`start_date`, `end_date`) in SQL before loading to Pandas
- convert `timestamp` with `pd.to_datetime(..., utc=True)` before grouping
- extract dimensions such as `location_id` and `product_id` from `tags` before aggregation
- use Pandas vectorized operations (`groupby`, `agg`, `count`, `sum`, `mean`) instead of loops
- return serializable rows with `reset_index().to_dict(orient='records')`

This appendix is explanatory only. Implementation is governed by the metric contracts and endpoint requirements above.

---

## Verification Checklist

- [x] `analysis.py` exists with three KPI-grounded metric functions
- [x] SQL pre-filters by event type and period in each metric function
- [x] UTC datetime conversion occurs before grouping in every metric
- [ ] KPI 1 groups by `date` + `product_id` + `location_id` and sums `quantity` from `outbound_order_created`
- [ ] KPI 2 groups by `date` + `product_id` + `location_id` and counts stock-out signals (`stock_threshold_triggered`, `outbound_order_failed`)
- [ ] KPI 3 groups by `date` + `location_id` with `waste_quantity` from `stock_waste_registered`, `total_quantity`, and `ratio`
- [x] Endpoint defaults to last 7 days when query params are omitted
- [x] Endpoint shares one resolved period across all metric functions
- [x] Endpoint uses in-memory cache with 60-second TTL
- [x] Response shape includes `period` and grouped metric outputs
- [x] All outputs are JSON-serializable
- [ ] Metric key `daily_consumption_by_product_and_location` and `product_id` row fields align to v2 once analysis is updated

---

## Evaluation Criteria

- Analysis pipeline computes KPI metrics with temporal dimensions (not global scalar counts only)
- Endpoint serves combined report and does not recalculate for every same-period request within TTL
- Timestamp conversion is correctly handled before grouping
- Per-metric SQL filtering is done by event type and period before Pandas transforms
- Grouping dimensions match business questions from Phase 1 (`product_id`, remapped event types)
- Optional auth metric (if implemented) uses both login event types and computes ratio correctly

---

_Brasaland Digital — Internal document for 4Geeks Academy AI Engineering Track_
