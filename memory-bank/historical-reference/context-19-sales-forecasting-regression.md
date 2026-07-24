# Context 19 — Sales Forecasting with Regression Model

**Ticket:** Sales prediction model (Finance / tech lead)  
**Type:** ML notebook + reusable Python module + pipeline test  
**Depends on:** Provided historical dataset at `data/raw/brasaland_sales.csv`  
**Companion:** `docs/forecasting/README.md`, `docs/forecasting/CONTEXT-brasaland.md`, `notebooks/sales_forecasting.ipynb`  
**Stakeholder:** Finance — honest, explainable forecasts (not memorized past)

---

## Goal

Train and evaluate a **Random Forest regression model** that predicts Brasaland monthly **`revenue_usd`** from **10 years** of historical data:

1. Strict **8-year train / 2-year holdout test** temporal split (no leakage).
2. **Random Forest** with documented justification in code (small dataset, Finance explainability, minimal tuning).
3. Four reported **test-set** metrics: **MSE, PSI, Gini, K2 Score**.
4. **Eight labeled visual aids** (V1–V8) including prediction + **variability band**, not a single point.
5. **Jupyter notebook** as the primary exploration/delivery artifact.
6. At least one **unit test** proving the split rule and no overlap between sets.

---

## Business context

Finance wants to know whether upcoming monthly sales can be predicted from history. The tech lead requires **honest evaluation**: the model must not look good only because it memorized the training period. Predictions must include **uncertainty**, and algorithm choice must be **argued**, not assumed.

**Locked algorithm (D3):** **Random Forest** — ~96 monthly training rows; Finance needs explainability and feature-importance charts; RF provides a natural 10th–90th percentile band across trees; minimal hyperparameter tuning vs XGBoost.

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
| D17 | Tests | `services/api/tests/pipelines/test_sales_forecast_split.py` |
| D18 | Metrics scope | MSE, PSI, Gini, K2 on **test set only** |
| D19 | MSE | `sklearn.metrics.mean_squared_error` on test |
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
  evaluate.py                               # MSE, PSI, Gini, K2 Score
  visualize.py                              # V1–V8 chart helpers
notebooks/sales_forecasting.ipynb           # narrative + end-to-end run
docs/forecasting/
  README.md                                 # metric definitions for Finance
  CONTEXT-brasaland.md                      # column/date/seasonality mirror
  outputs/                                  # exported PNGs (V1–V8)
services/api/tests/pipelines/
  test_sales_forecast_split.py              # split rule + no leakage
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
| Evaluate | MSE, PSI, Gini, K2 on test; metrics table (V4) |
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
| **PSI** | Population Stability Index on binned test actual vs test predicted | Distribution drift; lower is more stable (typical: &lt;0.1 stable) |
| **Gini** | Normalized Gini on test (ranking quality) | How well predictions rank months vs actuals |
| **K2 Score** | Chi-square on binned actual vs predicted proportions | **K2 → 0 = good distributional fit**; large K2 = structural bias in certain revenue ranges |

**K2 (course definition):** After training, bucket predictions and actuals into bins and compare proportions. Catches systematic under/over-prediction that MSE may miss.

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
| **Rows** | MSE, PSI, Gini, K2 — each with plain-language explanation |
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

**Path:** `services/api/tests/pipelines/test_sales_forecast_split.py`

| Test | Asserts |
| ---- | ------- |
| `test_temporal_split_respects_eight_two_year_rule` | Train spans 8 years; test spans 2 years |
| `test_no_date_overlap_between_train_and_test` | No shared dates between sets |

```bash
cd services/api && uv run pytest tests/pipelines/test_sales_forecast_split.py -q
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

- [ ] Dataset at `data/raw/brasaland_sales.csv`; columns match CONTEXT; not simulated
- [ ] Null/empty handling before training; documented
- [ ] 8-year train / 2-year test; no test dates in train
- [ ] Scaling fit on train only
- [ ] Random Forest with justification comment in `train.py`
- [ ] Fixed `random_state = 42`
- [x] MSE, PSI, Gini, K2 on test; README explains each + MSE limits
- [x] V1 variability band uses 10th–90th percentile across RF trees
- [x] All eight visual aids (V1–V8) in notebook with titles, axis labels, legends, and captions
- [x] PNG exports saved under `docs/forecasting/outputs/`
- [x] Notebook runs end-to-end with `services/api` venv
- [x] Dependencies via `uv add` in `services/api` (`scikit-learn`, `matplotlib`, `jupyter`, `ipykernel`)
- [x] Split/leakage unit test passes

---

## Evaluation map

| Rubric theme | Evidence |
| ------------ | -------- |
| 8yr/2yr split, no mixing | `split.py` + unit test + notebook V2 date bounds |
| RF + justification | Comment in `train.py` + notebook markdown |
| Four metrics on test | `evaluate.py` + notebook V4 + README |
| Variability visualization | V1 with band, not point-only |
| Provided dataset intact | Path + EDA matches CONTEXT seasonality |
| Reproducible seed | `random_state = 42` |
| Unit test passes | `pytest tests/pipelines/test_sales_forecast_split.py` |
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

# Split tests
cd services/api && uv run pytest tests/pipelines/test_sales_forecast_split.py -q

# Notebook (from repo root, kernel = brasaland-forecasting)
jupyter notebook notebooks/sales_forecasting.ipynb
```
