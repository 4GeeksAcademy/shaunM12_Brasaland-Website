# Sales forecasting — Brasaland dataset context

**Authority:** Course sales-forecasting CONTEXT; implementation locks in `memory-bank/historical-reference/context-19-sales-forecasting-regression.md`.

**Dataset path (monorepo):** `data/raw/brasaland_sales.csv`

---

## Business context

Brasaland is a grilled-food restaurant chain (14 locations, Colombia and United States). Finance wants to know whether **monthly consolidated revenue** can be forecast from historical sales. The model must be evaluated honestly on a **holdout period the model never saw during training**.

**Stakeholder:** Finance — explainable forecasts with uncertainty, not memorized past performance.

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
| Market scope | `market = consolidated` (chain-wide; all rows) |

---

## Columns

| Column | Type | Description | Used in model |
| ------ | ---- | ----------- | ------------- |
| `month` | date | First day of the reporting month | Split key; calendar features (month, trend) |
| `revenue_usd` | float | Total consolidated monthly revenue in USD | **Target** |
| `covers_served` | integer | Customer covers / tickets for the month | **Not used** as a feature (not known in advance for future months; would leak target) |
| `avg_ticket_usd` | float | Average spend per cover (`revenue_usd ÷ covers_served`) | **Not used** as a feature (same reason) |
| `market` | string | Always `consolidated` in this file | **Dropped** — constant, no information |

**Schema validation (on load):** Assert exactly these five columns exist. Fail fast if names, row count, or date span differ from this document.

---

## Seasonality and growth

Patterns visible in the provided data — **do not alter the CSV** in ways that break these:

### Growth trend

- Revenue rises over the decade (e.g. Jan 2016 ≈ \$421k → Dec 2025 ≈ \$994k).
- The model should capture trend via calendar/time features and lagged revenue, not by distorting raw values.

### Seasonality

- **December peaks:** December is often the highest-revenue month each year (e.g. 2016-12 ≈ \$617k vs 2016-11 ≈ \$515k; 2025-12 ≈ \$994k).
- **Monthly variation:** Revenue fluctuates month-to-month around the upward trend; calendar month features and `lag_12` help capture this.

### Operational relationship (informational only)

- `avg_ticket_usd` is derived from `revenue_usd` and `covers_served`. Same-month covers/ticket are **not** used as model inputs (see context-19 D5).

---

## Modeling locks (from context-19)

| Topic | Lock |
| ----- | ---- |
| Algorithm | Random Forest (`RandomForestRegressor`, `random_state=42`) |
| Target | `revenue_usd` |
| Features | Calendar (month, trend) + **lagged revenue** at t−1, t−3, t−12 only |
| Forecast mode | One-step-ahead on holdout; lags use **actual** prior months only |
| Scaling | `StandardScaler` — fit on train features, transform train + test |
| Nulls | Drop rows with missing values; drop rows with NaN lags after feature build |
| Uncertainty | 10th–90th percentile across RF tree predictions per month |

---

## Train / test split (locked)

Split by **`month`** — temporal only; **no random shuffle**.

| Set | Calendar years | Date range (inclusive) | Rows | Purpose |
| --- | -------------- | ---------------------- | ---- | ------- |
| **Training** | 2016–2023 | `2016-01-01` → `2023-12-01` | 96 | Model fit, scaler fit, lag construction within train |
| **Test (holdout)** | 2024–2025 | `2024-01-01` → `2025-12-01` | 24 | Metrics (MSE, PSI, Gini, K2) and visual aids V1–V8 only |

**Leakage rules:**

- No test-row dates in the training frame.
- Scaler and any bin edges for PSI/K2 on test must not use test labels during **fit** (bins for evaluation may use test actuals at report time only).
- Do not fit the model on the full 10 years before splitting.

---

## Evaluation metrics (test set only)

| Metric | Purpose |
| ------ | ------- |
| **MSE** | Average squared error on holdout predictions |
| **PSI** | Distribution drift between actual and predicted revenue (binned) |
| **Gini** | Normalized Gini — ranking quality of predictions vs actuals |
| **K2 Score** | Chi-square on binned actual vs predicted proportions; **→ 0 = good fit**; large K2 = structural bias across revenue ranges |

Plain-language definitions: `docs/forecasting/README.md` (to be written in implementation step 6).

---

## Data quality expectations

| Check | Expected |
| ----- | -------- |
| Row count | 120 |
| Null cells | None in provided file |
| `market` values | All `consolidated` |
| Monotonic months | One row per month, no gaps in sequence 2016-01 … 2025-12 |
| Revenue range (approx.) | ~\$420k–\$994k monthly over full series |

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
