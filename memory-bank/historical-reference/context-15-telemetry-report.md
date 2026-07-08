# CONTEXT — Brasaland · Telemetry Phase 4: Report from the Data

## AI Engineering - 4Geeks Academy

> **Repository index:** `context-15-telemetry-report.md`  
> **Companion docs:** `memory-bank/historical-reference/context-15-telemetry-plan.md`, `memory-bank/historical-reference/context-15-telemetry-frontend-capture.md`, `memory-bank/historical-reference/context-15-backend-storage.md`, `docs/telemetry/telemetry-plan.md`, `docs/telemetry/event-schemas.json`  
> **Type:** Telemetry analysis pipeline + reporting endpoint  
> **Status:** 🟡 Planned

> **Authority rule:** Milestone 5 contexts govern runtime inventory semantics; this reporting phase enriches observability and must not change API behavior.

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

---

## Important Note on Examples

All snippets and payloads in this document are **reference only**.  
Implementation must follow the KPI contracts from Phase 1 and allowlist semantics from `docs/telemetry/event-schemas.json`.

Do not hardcode sample values from examples.

---

## Your Two Required Metrics

These metrics map directly to the KPIs defined in the Phase 1 plan.

## Metric 1 — Daily Consumption by Location

**Business question:** how many consumption order events were registered per day, segmented by location?  
**KPI mapping:** Daily consumption rate by ingredient and location.

### Function contract

```python
def consumption_by_location_per_day(start_date, end_date) -> list[dict]:
    ...
```

### Required behavior

- SQL load:
  - `event_type = 'consumption_order_created'`
  - `timestamp >= start_date` and `timestamp < end_date`
- Pandas:
  - convert `timestamp` with UTC
  - derive daily date key from timestamp
  - extract `location_id` from `tags`
  - drop null `location_id` rows
- Grouping:
  - `groupby(['date', 'location_id'])['id'].count()`
- Output:
  - list of dicts with `date`, `location_id`, `count`

## Metric 2 — Order Failure Rate per Day

**Business question:** what proportion of order attempts (supply + consumption) failed each day?  
**KPI mapping:** Stock-out frequency (indirectly, failures signal supply chain stress).

### Function contract

```python
def order_failure_rate_per_day(start_date, end_date) -> list[dict]:
    ...
```

### Required behavior

- SQL load:
  - `event_type IN ('consumption_order_created', 'supply_order_created', 'consumption_order_failed', 'supply_order_failed')`
  - `timestamp >= start_date` and `timestamp < end_date`
- Pandas:
  - convert timestamp UTC
  - derive `date`
  - compute `is_failure = event_type.endswith('_failed')`
- Grouping:
  - `groupby('date').agg(total=('id', 'count'), failures=('is_failure', 'sum'))`
  - compute `failure_rate = failures / total`
- Output:
  - list of dicts with `date`, `total`, `failures`, `failure_rate`

---

## Additional Activity — Auth Failure Rate

If authentication telemetry is instrumented, add:

```python
def auth_failure_rate_per_day(start_date, end_date) -> list[dict]:
    ...
```

### Metric intent

- Load `event_type IN ('user_login_succeeded', 'user_login_failed')`
- Group by day (and optionally `location_id` from `tags`)
- Compute `failure_rate = failed / (failed + succeeded)`
- Return JSON-serializable records under `auth_failure_rate`

---

## Business Constraints for Your Pipeline

- `location_id` must be extracted from `tags`, not from a fixed SQL column.
- Consumption metric must preserve location segmentation so Colombia and Florida can be compared.
- Temporal grouping is mandatory; a global scalar count without time context is not a KPI metric.
- Optional third metric for waste ratio may be added using `reason == waste` extracted from `tags`.

---

## Expected JSON Output Shape (Reference Only)

```json
{
  "period": { "from": "2025-01-13", "to": "2025-01-20" },
  "metrics": {
    "consumption_by_location_per_day": [
      { "date": "2025-01-13", "location_id": 3, "count": 12 },
      { "date": "2025-01-13", "location_id": 11, "count": 8 }
    ],
    "order_failure_rate_per_day": [
      { "date": "2025-01-13", "total": 20, "failures": 3, "failure_rate": 0.15 }
    ]
  }
}
```

---

## Phase 1 — Analysis Pipeline with Pandas

Create `services/api/telemetry/analysis.py` with at least two metric functions.

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
   - at least one outbound order
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
- extract dimensions such as `location_id` from `tags` before aggregation
- use Pandas vectorized operations (`groupby`, `agg`, `count`, `sum`, `mean`) instead of loops
- return serializable rows with `reset_index().to_dict(orient='records')`

This appendix is explanatory only. Implementation is governed by the metric contracts and endpoint requirements above.

---

## Verification Checklist

- [ ] `analysis.py` exists with at least two KPI-grounded metric functions
- [ ] SQL pre-filters by event type and period in each metric function
- [ ] UTC datetime conversion occurs before grouping in every metric
- [ ] Consumption metric groups by `date` + `location_id`
- [ ] Failure-rate metric groups by `date` with derived `failure_rate`
- [ ] Endpoint defaults to last 7 days when query params are omitted
- [ ] Endpoint shares one resolved period across all metric functions
- [ ] Endpoint uses in-memory cache with 60-second TTL
- [ ] Response shape includes `period` and grouped metric outputs
- [ ] All outputs are JSON-serializable

---

## Evaluation Criteria

- Analysis pipeline computes KPI metrics with temporal dimensions (not global scalar counts only)
- Endpoint serves combined report and does not recalculate for every same-period request within TTL
- Timestamp conversion is correctly handled before grouping
- Per-metric SQL filtering is done by event type and period before Pandas transforms
- Grouping dimensions match business questions from Phase 1
- Optional auth metric (if implemented) uses both login event types and computes ratio correctly

---

_Brasaland Digital — Internal document for 4Geeks Academy AI Engineering Track_
