# Sales forecasting — Brasaland dataset context

**Authority:** Course Brasaland CONTEXT; implementation locks in `memory-bank/historical-reference/context-19-sales-forecasting-regression.md` (decisions R1–R7 confirmed 2026-07-24).

**Dataset path (monorepo):** `data/raw/brasaland_sales.csv`

---

## Business context

Brasaland is a grilled-food restaurant chain (14 locations, Colombia and United States).

**Stakeholders:** Mariana (CEO) — forecast accuracy before a full executive dashboard; Felipe (Operations) — ingredient purchasing from expected trend; Lucía (Procurement) — volume-driven meat price planning.

The model must be evaluated honestly on a **holdout period the model never saw during training**, with **uncertainty** (not a single optimistic point).

---

## Dataset overview

| Item | Value |
| ---- | ----- |
| Company | Brasaland |
| Granularity | Monthly (one row per month) |
| Total span | 10 years — **120 rows** |
| Date range | `2016-01-01` through `2025-12-01` |
| Source | Provided course dataset — **never simulate or alter** seasonality/growth |
| Date column | `month` (first day of each month, `YYYY-MM-DD`) |
| Target (model output) | `revenue_usd` |
| Market scope | **`consolidated` only** in the provided file (R2) |

**Course schema note:** Course CONTEXT allows `market` values `"colombia"`, `"florida"`, or `"consolidated"`. This repo's CSV is **consolidated-only**; per-market features are optional and **not implemented** (R3).

---

## Columns

| Column | Type | Description | Used in model |
| ------ | ---- | ----------- | ------------- |
| `month` | date | First day of the reporting month | Split key; calendar features (month, trend) |
| `revenue_usd` | float | Total consolidated monthly revenue in USD (fixed COP→USD rate in course data, e.g. 1 USD = 4,000 COP) | **Target** |
| `covers_served` | integer | Customer covers / tickets for the month | **Not used** as a feature (not known in advance; would leak target) |
| `avg_ticket_usd` | float | Average spend per cover (`revenue_usd ÷ covers_served`) | **Not used** as a feature (same reason) |
| `market` | string | Always `consolidated` in this file | **Dropped** — constant, no information |

**Schema validation (on load):** Assert exactly these five columns exist. Fail fast if names, row count, or date span differ from this document.

---

## Seasonality and growth

Patterns in the provided data — **do not alter the CSV** in ways that break these:

### Growth trend

- Base annual growth **X = 5%**, variation **Y = 2%**; yearly growth alternates between **3% and 7%** (always positive).
- Revenue rises over the decade (e.g. Jan 2016 ≈ $421k → Dec 2025 ≈ $994k).
- Captured via `months_since_start` and lagged revenue features — not by distorting raw values.

### Seasonality

- **January:** sales drop **12–18%** vs prior-year average (vacaciones colectivas / post-December slump).
- **December:** sales rise **20–30%** vs average (holiday season in both markets).
- Other months fluctuate **±5%** around the growth trend.
- `calendar_month` and `revenue_lag_12` help capture these patterns.

### Operational relationship (informational only)

- `avg_ticket_usd` is derived from `revenue_usd` and `covers_served`. Same-month covers/ticket are **not** model inputs (context-19 D5).

---

## Modeling locks (from context-19)

| Topic | Lock |
| ----- | ---- |
| Algorithm | **Random Forest** (`RandomForestRegressor`, `random_state=42`) — R1 |
| Target | `revenue_usd` |
| Features | Calendar (month, trend) + **lagged revenue** at t−1, t−3, t−12 only |
| Forecast mode | One-step-ahead on holdout; lags use **actual** prior months only |
| Scaling | `StandardScaler` — fit on train features, transform train + test |
| Nulls | Drop rows with missing values; drop rows with NaN lags after feature build |
| Uncertainty | 10th–90th percentile across RF tree predictions per month |

---

## Train / test split (locked)

Split by **`month`** — temporal only; **no random shuffle**.

| Set | Calendar years | Date range (inclusive) | Raw rows | Featured rows (after lags) | Purpose |
| --- | -------------- | ---------------------- | -------- | -------------------------- | ------- |
| **Training** | 2016–2023 | `2016-01-01` → `2023-12-01` | 96 | **84** (2017-01 → 2023-12) | Model fit, scaler fit |
| **Test (holdout)** | 2024–2025 | `2024-01-01` → `2025-12-01` | 24 | **24** | Metrics and visual aids V1–V8 only |

**Leakage rules:**

- No test-row dates in the training frame.
- Scaler fit on train only; PSI/K2 bin edges use test actuals at **report time** only (D20).
- Do not fit the model on the full 10 years before splitting.

---

## Evaluation metrics (test set only)

| Metric | Purpose |
| ------ | ------- |
| **MSE** | Average squared error on holdout (USD²) |
| **MAPE** | Average absolute percentage error on holdout — stakeholder-readable (R5) |
| **PSI** | Target drift: training vs holdout `revenue_usd` (D20 / R4) |
| **Gini** | Normalized Gini — ranking quality of predictions vs actuals |
| **K2 Score** | D'Agostino-Pearson K² on holdout residuals; lower = more random error shape |

Plain-language definitions and holdout snapshot: [`docs/forecasting/README.md`](./README.md) and [`docs/forecasting/outputs/v4_metrics_summary.md`](./outputs/v4_metrics_summary.md).

**High PSI/K2:** Call out in Finance summary — train→holdout target drift (PSI) or non-normal residual shape (K2) may warrant retraining; see V2, V8, and V5 (forecast-mix supplementary).

---

## Data quality expectations

| Check | Expected |
| ----- | -------- |
| Row count | 120 |
| Null cells | None in provided file |
| `market` values | All `consolidated` |
| Monotonic months | One row per month, no gaps 2016-01 … 2025-12 |
| Revenue range (approx.) | ~$420k–$994k monthly over full series |
| All `revenue_usd` | Positive |

If validation fails, stop and fix the CSV or paths before training.

---

## Environment and dependencies

Managed in **`services/api/pyproject.toml`** via [uv](https://docs.astral.sh/uv/). Do not use `pip install` at repo root.

| Package | Version lock (min) | Purpose |
| ------- | ------------------ | ------- |
| `scikit-learn` | ≥1.9.0 | Random Forest, metrics, scaling |
| `pandas` | ≥2.0 | Load CSV, features |
| `matplotlib` | ≥3.11.1 | Visual aids V1–V8 |
| `jupyter` | ≥1.1.1 | Notebook runtime |
| `ipykernel` | ≥7.3.0 | Jupyter kernel for `services/api` venv |

```bash
cd services/api && uv sync
uv run python -m ipykernel install --user --name brasaland-forecasting --display-name "Brasaland Forecasting (Python 3.12)"
```

Details: [services/api/README.md#sales-forecasting-context-19](../../services/api/README.md#sales-forecasting-context-19).

---

## Related paths

| Artifact | Path |
| -------- | ---- |
| Raw CSV | `data/raw/brasaland_sales.csv` |
| Implementation plan | `memory-bank/historical-reference/context-19-sales-forecasting-regression.md` |
| Python modules | `data/forecasting/` |
| Notebook | `notebooks/sales_forecasting.ipynb` |
| Chart exports | `docs/forecasting/outputs/` |
| Setup / metrics README | `docs/forecasting/README.md` |
