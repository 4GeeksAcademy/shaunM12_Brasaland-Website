# Context 19 — Sales Forecasting with Regression Model

**Ticket:** Sales prediction model (Finance / tech lead)  
**Type:** ML notebook + reusable Python module + pipeline tests  
**Branch:** `sales-forecasting-with-regression` (merged via PR #37)  
**Status:** ✅ Completed — model trained, holdout evaluated, eight visuals exported  
**Depends on:** Provided historical dataset at `data/raw/brasaland_sales.csv`  
**Companion:** `docs/forecasting/README.md`, `docs/forecasting/CONTEXT-brasaland.md`, `notebooks/sales_forecasting.ipynb`  
**Stakeholders:** Mariana (CEO), Felipe (Operations), Lucía (Procurement); tech lead — honest, explainable forecasts (not memorized past)

---

## Goal

Train and evaluate a **Random Forest regression model** that predicts Brasaland monthly **`revenue_usd`** from **10 years** of historical data:

1. Strict **8-year train / 2-year holdout test** temporal split (no leakage).
2. **Random Forest** with documented justification in code (small dataset, Finance explainability, minimal tuning).
3. Rubric **test-set** metrics: **MSE, PSI, Gini, K2**; plus **MAPE** (avg. % error) for Mariana/Felipe (R5).
4. **Eight labeled visual aids** (V1–V8) including prediction + **variability band**, not a single point.
5. **Jupyter notebook** as the primary exploration/delivery artifact.
6. At least one **unit test** proving the split rule and no overlap between sets.

---

## CONTEXT — Brasaland (Regression model for sales prediction)

Course domain context for this ticket. Implementation locks below must stay consistent with this file to avoid churn.

### 1. Why this matters to Brasaland

Mariana (CEO) wants to know whether, before investing in a full executive dashboard, it's possible to predict how much the chain will sell in the coming months within a reasonable margin. Felipe (Operations) needs to anticipate ingredient purchases based on the expected trend, and Lucía (Procurement) wants to anticipate meat price fluctuations based on projected volume. A regression model over historical sales is the first concrete step toward that dashboard.

The tech lead requires **honest evaluation**: the model must not look good only because it memorized the training period. Predictions must include **uncertainty**, and algorithm choice must be **argued**, not assumed.

### 2. Data structure

The monthly consolidated sales dataset for all 14 locations is in the monorepo at `data/raw/brasaland_sales.csv`, with these exact columns:

| Column | Type | Description |
| ------ | ---- | ----------- |
| `month` | date (`YYYY-MM-01`) | First day of the reported month |
| `revenue_usd` | float | Total sales for the month, consolidated in USD (fixed COP→USD conversion rate for simplicity, e.g. 1 USD = 4,000 COP) |
| `covers_served` | int | Total number of guests served during the month, across all 14 locations |
| `avg_ticket_usd` | float | Average ticket for the month in USD |
| `market` | string | `"colombia"`, `"florida"`, or `"consolidated"` — use `"consolidated"` as the main row for the model; per-market rows are optional as additional features |

The model's target variable is `revenue_usd` from the `consolidated` row.

**Repo note:** The provided file in this branch contains **120 consolidated rows only** (`market = consolidated`). `load.py` validates that constraint.

### 3. KPIs and what a good model means here

- A **low normalized Gini** means the model doesn't distinguish well between "good" and "bad" months — for Mariana this matters as much as absolute error, since she needs to identify underperforming months in advance. (**Higher Gini = better ranking** in our implementation.)
- A **high PSI** on the holdout (actual vs predicted revenue mix) signals that forecast behavior may not match reality — call out explicitly if detected; Finance may need retraining or feature work.
- Report **MSE** in USD² and **MAPE** (average percentage error) on the holdout in V4 and the notebook Finance summary — how Felipe and Mariana understand forecast error.

**Implementation note (no leakage impact):** PSI in `evaluate.py` compares **test actual vs test predicted** distributions (D20). Course wording about train/test structural shift is a **business narrative** when PSI/K2 are high — it does not change the metric formula unless Decision R4 below is revised.

### 4. About the provided dataset

The file `data/raw/brasaland_sales.csv` contains **10 years** of monthly data (120 `consolidated` rows), from `2016-01` to `2025-12`. It already reflects the following patterns — you don't need to generate them, but you do need to understand them to interpret results:

**Growth pattern:** the base annual growth is `X = 5%`, with variation `Y = 2%`. Each year, the actual growth `d` alternates between `X+Y` and `X-Y` (i.e. between 3% and 7%), always positive and never outside that range.

**Seasonality pattern (present every year in the dataset):**

- **January:** sales drop of 12–18% relative to the previous year's average, explainable by the "vacaciones colectivas" period and the typical post-December slump in Colombia.
- **December:** sales rise of 20–30% relative to the average, due to the holiday season in both markets.
- All other months fluctuate moderately (±5%) around the annual growth trend, with no abrupt patterns.

The dataset was generated with a fixed random seed (`random_state=42`), so it's deterministic: regenerating it with the same script and seed would produce exactly the same values.

### 5. Business constraints

- All `revenue_usd` values must be positive.
- There must be no missing months in the 2016-01 to 2025-12 range.
- The provided dataset only includes the `consolidated` row; if you want to analyze Colombia and Florida separately as an additional feature, keep in mind Florida is a smaller market (roughly 25% of the total) — don't assume similar magnitudes between the two.

### 6. Expected deliverables (course minimum)

| Course deliverable | Repo implementation (this branch) |
| ------------------ | --------------------------------- |
| Training script in `scripts/` | `data/forecasting/train.py` + `train_sales_model()` |
| 8yr train / 2yr test split | `data/forecasting/split.py` |
| Trained model (XGBoost or Random Forest) + 4 test metrics | **Random Forest** locked (see Decision R1); `evaluate.py` |
| Visualization: prediction + variability vs 2 test years | V1 + band; full set V1–V8 exceeds minimum |
| Unit test validating 8/2 split | `services/api/tests/pipelines/test_sales_forecast_split.py` (+ model/visualize tests) |

---

## Decisions log (confirmed)

All items reviewed against course Brasaland CONTEXT vs repo implementation. **Locked 2026-07-24.** Re-running the pipeline preserves the same model, split, and leakage rules; R5 adds holdout-only MAPE reporting.

| ID | Topic | Locked choice | Notes |
| -- | ----- | ------------- | ----- |
| **R1** | Algorithm | **Random Forest** | Course allows RF or XGBoost; RF chosen for small N, explainability, tree band (D3, D14) |
| **R2** | `market` column | **Consolidated-only CSV** | 120 rows, `market = consolidated`; `load.py` validates; column dropped as constant (D5) |
| **R3** | Per-market features | **Not implemented** | Optional in course CONTEXT; no col/fl rows in provided file — defer unless new CSV + D5 revision |
| **R4** | PSI | **Keep D20 formula** | Test actual vs test predicted in `evaluate.py`; high PSI/K2 → Finance retraining narrative (not train/test PSI in code) |
| **R5** | MSE reporting | **MSE + MAPE on holdout** | MSE in USD²; **avg. % error (MAPE)** in `evaluate.py`, V4, README, notebook Finance summary — test set only, no leakage |
| **R6** | Deliverable paths | **Keep repo layout** | `data/forecasting/`, `services/api/tests/pipelines/` — course `scripts/` mapped in §6 |
| **R7** | Scope | **Keep extended deliverables** | V1–V8, 3 test modules (11 tests), notebook, README — superset of course minimum |

---

## Reconciliation — course CONTEXT vs repo locks

| Topic | Course CONTEXT | Repo lock |
| ----- | -------------- | --------- |
| Algorithm | RF or XGBoost | **Random Forest** (R1 ✅) |
| `market` rows | col / fl / consolidated possible | **consolidated-only** in provided CSV (R2 ✅) |
| Per-market features | optional | **not used** (R3 ✅) |
| Training code path | `scripts/` | `data/forecasting/` + notebook (R6 ✅) |
| PSI | structural shift narrative | test actual vs predicted in code (R4 ✅) |
| MSE reporting | USD² + average % error | MSE + **MAPE** on holdout (R5 ✅) |
| Deliverables | minimum set | superset: V1–V8, extended tests (R7 ✅) |

---

## Decision rationale (locked during planning)

Decisions were validated against the actual CSV (120 rows, 2016–2025, no nulls, `market=consolidated` only) and checked for repo conflicts (no overlap with Milestone 6 telemetry/pipeline code, no FastAPI forecast UI, no synthetic data).

| # | Decision | Rationale |
| - | -------- | --------- |
| 1 | **Random Forest** over XGBoost | ~84 featured training rows after lags — too small for heavy XGBoost tuning; stakeholders need feature importance; RF yields natural 10th–90th tree band |
| 2 | Target **`revenue_usd`** | Mariana/Felipe/Lucía question is consolidated monthly revenue |
| 3 | Calendar + **lagged revenue** (t−1, t−3, t−12) | Captures trend and seasonality (§4 growth/seasonality) without same-month leakage; drop constant `market`; exclude same-month `covers_served` / `avg_ticket_usd` |
| 4 | **`StandardScaler`**, fit train only | Numeric features on different scales; scaler must not see test rows during fit |
| 5 | **Drop** nulls / NaN lag rows | Provided CSV has no nulls; first 12 months drop after `lag_12` |
| 6 | **10th–90th percentile** tree band | Ticket requires variability range, not a single optimistic point |
| 7 | **MSE, MAPE, PSI, Gini, K2** on test only | Course rubric; MAPE for stakeholder readability (R5); K2 is chi-square on bins (not R²) |
| 8 | **`random_state = 42`** | Matches dataset generation seed; reproducible notebook and tests |
| 9 | Layout under `data/forecasting/`, `notebooks/`, `services/api/tests/pipelines/` | Matches context-16/17/18 module patterns; deps via `uv` in `services/api` |

**Conflict check:** No churn with telemetry, Prefect pipelines, inventory API, or supplier directory. Forecasting is a standalone Python module + notebook path.

| Algorithm | Strength | Tradeoff |
| --------- | -------- | -------- |
| **Random Forest** ✓ | Many trees averaged; feature importance; easier to explain; natural uncertainty band | Usually lower peak accuracy; simpler defaults |
| **XGBoost** (not chosen) | Sequential error correction; often higher accuracy | Harder to explain; more tuning; weaker default uncertainty |

---

## Locked decisions (D1–D22)

| ID | Topic | Lock |
| -- | ----- | ---- |
| D1 | Dataset path | `data/raw/brasaland_sales.csv` — provided dataset only; never simulate or alter seasonality/growth |
| D2 | Company context | Read `docs/forecasting/CONTEXT-brasaland.md` before coding |
| D3 | Algorithm | **Random Forest** (`RandomForestRegressor`) — small dataset (~96 train rows), Finance explainability, minimal tuning; document in `train.py` comment |
| D4 | Target | **`revenue_usd`** |
| D5 | Features | Calendar + **lagged revenue only** (t−1, t−3, t−12); drop `market`; **no** same-month `covers_served` or `avg_ticket_usd` |
| D6 | Forecast mode | **One-step-ahead** on 2024–2025 holdout; lags use actual prior months only |
| D7 | Train/test split | First **8 calendar years → train** (2016–2023); most recent **2 years → test** (2024–2025); split by date, not shuffle |
| D8 | Leakage prevention | No test dates in train; scaler fit on train only; no global stats across full 10 years before split |
| D9 | Scaling | `StandardScaler` on numeric features — **fit train, transform train + test** |
| D10 | Null handling | Validate on load; **drop** rows with missing values; drop rows with NaN lags; document counts |
| D11 | Variability band | **10th–90th percentile** across RF tree predictions per month |
| D12 | Reproducibility | **`random_state = 42`** in module and notebook |
| D13 | Python env | `services/api/pyproject.toml` + `uv add` — no `pip install` / `pipenv`; no competing root `pyproject.toml` |
| D14 | Dependencies | `scikit-learn`, `pandas`, `matplotlib`, `jupyter`, `ipykernel` (no `xgboost` — RF only) |
| D15 | Notebook | `notebooks/sales_forecasting.ipynb` |
| D16 | Reusable code | `data/forecasting/` (load, split, features, train, evaluate, visualize) |
| D17 | Tests | `test_sales_forecast_split.py`, `test_sales_forecast_model.py`, `test_sales_forecast_visualize.py` |
| D18 | Metrics scope | MSE, MAPE, PSI, Gini, K2 on **test set only** |
| D19 | MSE | `sklearn.metrics.mean_squared_error` on test |
| D19b | MAPE (avg. % error) | `mean_absolute_percentage_error()` on test — holdout reporting for Mariana/Felipe (R5); does not feed `fit()` |
| D20 | PSI | Bin **test actual** vs **test predicted** `revenue_usd`; standard PSI formula |
| D21 | Gini | **Normalized Gini** on test (ranking quality of predictions vs actuals) |
| D22 | K2 Score | Chi-square on binned actual vs predicted proportions; **K2 → 0 = good fit**; large K2 = structural bias across revenue ranges |
| — | Raw data folder | Drop CSV in `data/raw/`; see `data/raw/README.md` |

---

## Dataset contract

| Item | Expected |
| ---- | -------- |
| Path | `data/raw/brasaland_sales.csv` |
| Span | 10 years total (2016–2025 monthly) |
| Columns | `month`, `revenue_usd`, `covers_served`, `avg_ticket_usd`, `market` |
| Target | `revenue_usd` |
| Validation | Assert expected columns and date range on load; fail fast if schema mismatches CONTEXT |
| Null handling | Drop rows with missing values; document in notebook + README |
| Integrity | Do not alter CSV in ways that break seasonality/growth from CONTEXT |

Column definitions and seasonality: **`docs/forecasting/CONTEXT-brasaland.md`**.

### Row pipeline (implemented counts)

Understanding row counts prevents accidental leakage or “missing data” confusion:

| Stage | Rows | Date span | Notes |
| ----- | ---- | --------- | ----- |
| Raw CSV | **120** | 2016-01 → 2025-12 | Full provided dataset |
| After `build_feature_frame` | **108** | 2017-01 → 2025-12 | First **12** months dropped (`revenue_lag_12` requires prior year) |
| Featured **train** | **84** | 2017-01 → 2023-12 | 8 calendar years of train **after** lag drop (not 96) |
| Featured **test** | **24** | 2024-01 → 2025-12 | Holdout — never used in `fit` |

Raw split constants in `split.py` still describe **96 / 24** on the **unfeatured** frame (2016–2023 vs 2024–2025). Model training uses the **featured** 84 / 24 split from `train.py`.

---

## Feature engineering (implemented)

| Feature | Source | Role |
| ------- | ------ | ---- |
| `calendar_month` | `month` → 1–12 | Seasonality (December peaks) |
| `months_since_start` | Months from 2016-01 | Upward growth trend |
| `revenue_lag_1` | t−1 `revenue_usd` | Short-term momentum |
| `revenue_lag_3` | t−3 `revenue_usd` | Quarterly pattern |
| `revenue_lag_12` | t−12 `revenue_usd` | Year-over-year seasonality |

**Excluded (leakage or no signal):** `covers_served`, `avg_ticket_usd` (same month), `market` (constant).

**Model hyperparameters (locked):** `RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)`.

**Forecast mode:** One-step-ahead on holdout — each test month’s lags use **actual** prior-month revenue from the CSV, not prior predictions.

---

## File layout

```text
data/raw/brasaland_sales.csv              # provided — drop file here
data/raw/README.md                        # drop instructions
data/forecasting/
  __init__.py
  load.py                                   # load + schema validation
  split.py                                  # 8yr/2yr temporal split
  features.py                               # train-safe feature engineering
  train.py                                  # Random Forest fit
  evaluate.py                               # MSE, MAPE, PSI, Gini, K2 Score
  visualize.py                              # V1–V8 chart helpers
notebooks/sales_forecasting.ipynb           # narrative + end-to-end run
docs/forecasting/
  README.md                                 # metric definitions for Finance
  CONTEXT-brasaland.md                      # column/date/seasonality mirror
  outputs/                                  # exported PNGs (V1–V8)
services/api/tests/pipelines/
  test_sales_forecast_split.py              # split rule + no leakage (5 tests)
  test_sales_forecast_model.py              # features, train, metrics, uncertainty band
  test_sales_forecast_visualize.py          # V1–V8 PNG export smoke
```

---

## Dependencies (`uv`)

```bash
cd services/api && uv add scikit-learn pandas matplotlib jupyter ipykernel
```

Register Jupyter kernel from the API venv:

```bash
cd services/api && uv run python -m ipykernel install --user --name brasaland-forecasting
```

---

## Notebook structure

| Section | Purpose |
| ------- | ------- |
| Setup | Imports, `random_state=42`, paths |
| Load | Read CSV; verify columns vs CONTEXT |
| EDA | Note seasonality/growth; optional pre-model views |
| Clean | Drop nulls / NaN lag rows; document counts |
| Features | Calendar + lagged revenue (t−1, t−3, t−12); no same-month covers/ticket |
| Split | 2016–2023 train / 2024–2025 test; print date boundaries |
| Scale | Fit `StandardScaler` on train only |
| Model | Train Random Forest; comment block: why RF |
| Evaluate | MSE, MAPE, PSI, Gini, K2 on test; metrics table (V4) |
| Visualize | V1–V8 in order (see Visual aids section) |
| Summary | Plain-language note for Finance |

---

## Model training

Required comment block in `train.py`:

- Data size (~96 monthly training rows after lags)
- Explainability need (Finance stakeholder)
- Minimal tuning time → RF over XGBoost
- Natural uncertainty band via tree percentiles

Use `RandomForestRegressor(random_state=42, n_estimators=100, max_depth=8)`. Temporal split only — no shuffled `train_test_split`.

---

## Evaluation metrics (test set only)

Document in `docs/forecasting/README.md` in Finance-friendly language. Explain why **low MSE alone is not enough** (memorization, scale, seasonal bias, distribution shift, range-level bias).

| Metric | Definition | Interpretation |
| ------ | ---------- | -------------- |
| **MSE** | `mean_squared_error(y_test, y_pred)` | Average squared error; lower is better; penalizes large misses |
| **MAPE** | `mean_absolute_percentage_error(y_test, y_pred)` | Average % error vs actual revenue; stakeholder-readable (R5) |
| **PSI** | Population Stability Index on binned test actual vs test predicted | Distribution drift; lower is more stable (typical: &lt;0.1 stable) |
| **Gini** | Normalized Gini on test (ranking quality) | How well predictions rank months vs actuals |
| **K2 Score** | Chi-square on binned actual vs predicted proportions | **K2 → 0 = good distributional fit**; large K2 = structural bias in certain revenue ranges |

**K2 (course definition):** After training, bucket predictions and actuals into bins and compare proportions. Catches systematic under/over-prediction that MSE may miss.

### Holdout results snapshot (2024–2025, `random_state=42`)

Reproducible via `train_sales_model()` + `evaluate_forecast()`. Exported in `docs/forecasting/outputs/v4_metrics_summary.md`.

| Metric | Value | Finance read (honest, not a pass/fail gate) |
| ------ | ----- | ------------------------------------------- |
| **MSE** | 3,386,101,902.59 | RMSE ≈ **$58,000**/month scale — moderate dollar error |
| **MAPE** | 6.00% | Average holdout error as % of actual revenue (Mariana/Felipe) |
| **PSI** | 4.48 | High distribution drift — predicted revenue mix ≠ actual mix |
| **Gini** | 0.74 | Decent ranking — model often knows which months are bigger |
| **K2** | ~16,000,000 | Large range-level bias — peaks/weak months systematically off in some bins |

**Rubric note:** Context-19 requires **reporting** these honestly, not hitting metric thresholds. High PSI/K2 supports the README narrative that MSE alone is insufficient and may warrant retraining discussion per §3.

---

## Visual aids (implementation plan)

Eight charts for Finance and the tech lead. Each must have a **title**, **axis labels**, **legend**, and a **one-sentence caption** in the notebook. Implement in `data/forecasting/visualize.py`; render in `notebooks/sales_forecasting.ipynb`. Save PNGs to `docs/forecasting/outputs/`.

### V1 — Actual vs predicted with uncertainty band (required / rubric)

| Field | Value |
| ----- | ----- |
| **Purpose** | Primary forecast view: point estimate + plausible range vs reality |
| **Chart type** | Time-series line + shaded band |
| **Data** | Test period only (2024–2025) |
| **Title** | `Brasaland Monthly Revenue — Holdout Forecast (2024–2025)` |
| **X-axis label** | `Month` |
| **Y-axis label** | `Revenue (USD)` |
| **Series** | Actual (solid); mean prediction (dashed); band = 10th–90th percentile across RF trees |
| **Legend labels** | `Actual revenue`, `Mean prediction`, `Prediction range (10th–90th percentile)` |
| **Caption** | Shows whether monthly forecasts match actual sales and how wide the model's uncertainty is. |
| **Output file** | `docs/forecasting/outputs/v1_forecast_with_band.png` |

### V2 — Full history with train/test split

| Field | Value |
| ----- | ----- |
| **Purpose** | Prove the model never trained on the last two years |
| **Chart type** | Line chart, full 2016–2025 |
| **Title** | `Brasaland Revenue History — Training vs Holdout Period` |
| **X-axis label** | `Month` |
| **Y-axis label** | `Revenue (USD)` |
| **Series** | Train (2016–2023) one color; test (2024–2025) another; vertical line at `2024-01-01` optional |
| **Legend labels** | `Training period (2016–2023)`, `Holdout period (2024–2025)` |
| **Caption** | The model was fit only on the training period; holdout months were unseen during training. |
| **Output file** | `docs/forecasting/outputs/v2_train_test_timeline.png` |

### V3 — Monthly prediction error (test)

| Field | Value |
| ----- | ----- |
| **Purpose** | Intuitive errors in dollars (not MSE²) |
| **Chart type** | Bar chart |
| **Data** | Test months; error = actual − predicted |
| **Title** | `Monthly Forecast Error on Holdout Data (2024–2025)` |
| **X-axis label** | `Month` |
| **Y-axis label** | `Error (USD): Actual − Predicted` |
| **Caption** | Positive bars = underprediction; negative = overprediction. |
| **Output file** | `docs/forecasting/outputs/v3_monthly_errors.png` |

### V4 — Test metrics summary table

| Field | Value |
| ----- | ----- |
| **Purpose** | Single rubric-facing summary for Finance |
| **Chart type** | Notebook markdown/HTML table (not matplotlib) |
| **Title** | `Model Evaluation on Holdout Period (2024–2025)` |
| **Columns** | `Metric`, `Value`, `What it means` |
| **Rows** | MSE, MAPE, RMSE scale, PSI, Gini, K2 — each with plain-language explanation |
| **Caption** | Low MSE alone does not guarantee a good model; PSI, Gini, and K2 catch drift, ranking, and range-level bias. |
| **Output** | Notebook cell + optional `docs/forecasting/outputs/v4_metrics_summary.md` |

### V5 — Binned actual vs predicted distribution (PSI / K2 support)

| Field | Value |
| ----- | ----- |
| **Purpose** | Show whether forecast *distribution* matches reality |
| **Chart type** | Grouped bar chart (side-by-side bins) |
| **Data** | Test set; same bin edges for actual and predicted |
| **Title** | `Distribution of Actual vs Predicted Revenue (Holdout)` |
| **X-axis label** | `Revenue bin (USD)` |
| **Y-axis label** | `Share of months (%)` |
| **Legend labels** | `Actual`, `Predicted` |
| **Caption** | Supports PSI and K2: mismatched bar heights indicate systematic bias in certain revenue ranges. |
| **Output file** | `docs/forecasting/outputs/v5_binned_distribution.png` |

### V6 — Random Forest feature importance

| Field | Value |
| ----- | ----- |
| **Purpose** | Explain what drives predictions (not a black box) |
| **Chart type** | Horizontal bar chart |
| **Title** | `What Drives Revenue Predictions — Feature Importance` |
| **X-axis label** | `Importance (relative)` |
| **Y-axis label** | `Feature` |
| **Caption** | Shows which inputs (e.g. last month's revenue, seasonality) matter most. |
| **Output file** | `docs/forecasting/outputs/v6_feature_importance.png` |

### V7 — Seasonality: actual vs predicted by calendar month

| Field | Value |
| ----- | ----- |
| **Purpose** | Check December peaks and seasonal pattern on holdout |
| **Chart type** | Grouped bar (months 1–12) |
| **Data** | Test years (2024–2025) |
| **Title** | `Seasonal Pattern — Actual vs Predicted Revenue by Month (Holdout)` |
| **X-axis label** | `Calendar month` |
| **Y-axis label** | `Revenue (USD)` |
| **Legend labels** | `Actual`, `Predicted` |
| **Caption** | Validates whether the model captures recurring monthly effects (e.g. year-end peaks). |
| **Output file** | `docs/forecasting/outputs/v7_seasonality_by_month.png` |

### V8 — Residual plot (predicted vs error)

| Field | Value |
| ----- | ----- |
| **Purpose** | Detect systematic bias patterns |
| **Chart type** | Scatter plot |
| **Data** | Test set; x = predicted, y = residual (actual − predicted) |
| **Title** | `Residual Analysis — Holdout Predictions` |
| **X-axis label** | `Predicted revenue (USD)` |
| **Y-axis label** | `Residual (USD): Actual − Predicted` |
| **Reference line** | Horizontal at y = 0 |
| **Caption** | A clear trend in residuals suggests the model under- or over-predicts at certain revenue levels. |
| **Output file** | `docs/forecasting/outputs/v8_residuals.png` |

### Notebook visual order (locked)

1. V2 — Train/test timeline (trust)
2. V1 — Forecast + band (required)
3. V3 — Monthly errors
4. V5 — Binned distribution
5. V4 — Metrics table
6. V6 — Feature importance
7. V7 — Seasonality
8. V8 — Residuals

### Labeling standards (all charts)

- Format Y-axis as USD (`$600K` or `$600,000`).
- Every figure: `plt.title(...)`, `plt.xlabel(...)`, `plt.ylabel(...)`, `plt.legend(...)`.
- Markdown cell **caption** immediately below each figure (use caption text above).
- `fig.savefig(..., dpi=150, bbox_inches='tight')` for exports.

---

## Testing

**Paths:** `services/api/tests/pipelines/test_sales_forecast_*.py`

| File | Coverage |
| ---- | -------- |
| `test_sales_forecast_split.py` | Load contract; 96/24 raw split; no date overlap; boundary checks |
| `test_sales_forecast_model.py` | Feature columns; 84/24 featured split; metrics finite; uncertainty band ordering |
| `test_sales_forecast_visualize.py` | `save_all_visuals()` writes all eight PNG keys |

```bash
cd services/api && uv run pytest tests/pipelines/test_sales_forecast_split.py \
  tests/pipelines/test_sales_forecast_model.py \
  tests/pipelines/test_sales_forecast_visualize.py -q
```

---

## Explicit non-goals

- FastAPI / backoffice forecast UI
- Modifying Milestone 6 telemetry or reporting pipelines
- Synthetic sales data
- Random (non-temporal) train/test splits
- Primary metrics reported on training set
- `pip install` / `pipenv` for ML dependencies
- XGBoost (RF locked for this implementation)

---

## Acceptance criteria

- [x] Dataset at `data/raw/brasaland_sales.csv`; columns match CONTEXT; not simulated
- [x] Null/empty handling before training; documented in `CONTEXT-brasaland.md` + `load.py` validation
- [x] 8-year train / 2-year test; no test dates in train (`assert_no_split_leakage`)
- [x] Scaling fit on train only (`prepare_scaled_matrices` in `train.py`)
- [x] Random Forest with justification comment in `train.py`
- [x] Fixed `random_state = 42`
- [x] MSE, MAPE, PSI, Gini, K2 on test; README explains each + MSE/MAPE limits
- [x] V1 variability band uses 10th–90th percentile across RF trees
- [x] All eight visual aids (V1–V8) in notebook with titles, axis labels, legends, and captions
- [x] PNG exports saved under `docs/forecasting/outputs/`
- [x] Notebook runs end-to-end with `services/api` venv (kernel `brasaland-forecasting`)
- [x] Dependencies via `uv add` in `services/api` (`scikit-learn`, `matplotlib`, `jupyter`, `ipykernel`)
- [x] Split, model, and visualize pipeline tests pass (11 tests total)

---

## Evaluation map

| Rubric theme | Evidence |
| ------------ | -------- |
| 8yr/2yr split, no mixing | `split.py` + unit test + notebook V2 date bounds |
| RF + justification | Comment in `train.py` + notebook markdown |
| Four metrics + MAPE on test | `evaluate.py` + notebook V4 + README |
| Variability visualization | V1 with band, not point-only |
| Provided dataset intact | Path + EDA matches CONTEXT seasonality |
| Reproducible seed | `random_state = 42` |
| Unit test passes | `pytest tests/pipelines/test_sales_forecast_*.py` (11 passed) |
| Explainability | V6 feature importance + Finance summary |

---

## Implementation order

1. [x] Complete `docs/forecasting/CONTEXT-brasaland.md` (columns, split dates, seasonality)
2. [x] `uv add` ML + Jupyter deps in `services/api` — `scikit-learn`, `matplotlib`, `jupyter`, `ipykernel` (pandas already present); kernel `brasaland-forecasting`
3. [x] Implement `load.py` + `split.py`; write split tests first
4. [x] Implement `features.py`, `train.py`, `evaluate.py`
5. [x] `visualize.py` (V1–V8) + notebook cells in visual order above
6. [x] `docs/forecasting/README.md` (metrics + why MSE alone isn't enough)
7. [x] Create `docs/forecasting/outputs/`; full notebook run + pytest green

---

## Verification notes

```bash
# Confirm dataset present
test -f data/raw/brasaland_sales.csv && head -3 data/raw/brasaland_sales.csv

# Full forecasting test suite (11 tests)
cd services/api && uv run pytest tests/pipelines/test_sales_forecast_split.py \
  tests/pipelines/test_sales_forecast_model.py \
  tests/pipelines/test_sales_forecast_visualize.py -q

# Regenerate chart PNGs without the notebook
cd services/api && uv run python -c "
import sys; sys.path.insert(0, '../..')
from data.forecasting.visualize import save_all_visuals
save_all_visuals()
"

# Notebook (from repo root, kernel = brasaland-forecasting)
jupyter notebook notebooks/sales_forecasting.ipynb
```

**Operator verification (2026-07-23):** All acceptance criteria met; holdout metrics exported to `v4_metrics_summary.md`; eight PNGs under `docs/forecasting/outputs/`.
