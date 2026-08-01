# Sales forecasting — setup and metrics

**Plan:** [context-19](../../memory-bank/historical-reference/context-19-sales-forecasting-regression.md)  
**Evaluation (context-20):** [EVALUATION-report.md](./EVALUATION-report.md) · [notebooks/evaluating_regression.ipynb](../../notebooks/evaluating_regression.ipynb)  
**Dataset context:** [CONTEXT-brasaland.md](./CONTEXT-brasaland.md)  
**Notebook:** [notebooks/sales_forecasting.ipynb](../../notebooks/sales_forecasting.ipynb)

---

## Dependencies

Installed in **`services/api/pyproject.toml`** with `uv` (canonical). Mirror list in `services/api/requirements.txt` for pip-only workflows.

| Package | Min version | Role |
| ------- | ----------- | ---- |
| `scikit-learn` | 1.9.0 | `RandomForestRegressor`, `StandardScaler`, MSE |
| `pandas` | 2.0 | Load `data/raw/brasaland_sales.csv` |
| `matplotlib` | 3.11.1 | Visual aids V1–V8 |
| `jupyter` | 1.1.1 | Notebook UI |
| `ipykernel` | 7.3.0 | Kernel bound to `services/api` venv |

**Not used:** `xgboost` (Random Forest locked in context-19).

### Install

```bash
cd services/api
uv sync
```

Add packages individually (if needed on a fresh clone):

```bash
cd services/api && uv add scikit-learn pandas matplotlib jupyter ipykernel
```

### Jupyter kernel

```bash
cd services/api
uv run python -m ipykernel install --user --name brasaland-forecasting --display-name "Brasaland Forecasting (Python 3.12)"
```

In Cursor/VS Code or Jupyter, select **Brasaland Forecasting (Python 3.12)** for `notebooks/sales_forecasting.ipynb`.

**Notebook tip:** Cell 1 adds the repo root to Python's path. If imports fail, use **Kernel → Restart** and run again.

---

## Evaluation metrics (test set only)

Rubric metrics plus **MAPE** are computed on the **2024–2025 holdout** — 24 months the model never saw during training. Training metrics are intentionally **not** reported.

Implementation: `data/forecasting/evaluate.py`  
Notebook summary: **V4** in `notebooks/sales_forecasting.ipynb`  
Exported table: `docs/forecasting/outputs/v4_metrics_summary.md`

### Quick reference

| Metric | One-line summary | Better direction | Related chart |
| ------ | ---------------- | ---------------- | ------------- |
| **MSE** | Average squared forecast error (USD²) | Lower | V3 (monthly errors) |
| **MAPE** | Average % error vs actual revenue on holdout | Lower | V4 (metrics table) |
| **PSI** | Target drift: train vs holdout `revenue_usd` distribution | Lower | V2 (split context) |
| **Gini** | How well the model ranks high vs low months | Higher (max 1.0) | V1, V7 |
| **K2** | D'Agostino-Pearson K² on holdout residuals (error shape) | Lower | V8 (residual plot) |
| **V5 chart** | Supplementary forecast-mix calibration (actual vs predicted bins) | Visual | V5 |

---

### MSE — Mean Squared Error

**What it measures:** On average, how far off were the monthly revenue forecasts? Errors are **squared** before averaging, so large misses count much more than small ones.

**Finance reading:** MSE is reported in **USD²**, which is hard to interpret directly. Two companion readings (also in V4):

- **RMSE = √MSE** — dollar-scale typical error (e.g. MSE ≈ 3.4 billion → RMSE ≈ **$58,000**/month).
- **MAPE (avg. % error)** — mean of `|actual − predicted| / actual` on the holdout, as a percentage; this is how Mariana and Felipe usually read “how far off” the forecast is.

**Code:** `sklearn.metrics.mean_squared_error(y_test, y_pred)` and `mean_absolute_percentage_error()` in `evaluate.py`.

**Strengths:** Single number; penalizes big misses (e.g. missing a holiday peak hurts more than being off by a few thousand).

**Limits:**

- Two models can have similar MSE but fail in different ways (always under in Q4, always over in slow months).
- MSE says nothing about whether predicted revenue is **shifted** high or low overall.
- A model that memorizes training patterns can look acceptable on MSE while failing on unseen years.

---

### MAPE — Mean Absolute Percentage Error

**What it measures:** On average, how far off were forecasts **as a percentage of actual revenue**? Example: MAPE ≈ **6%** means typical holdout months were about six cents wrong per dollar of actual sales.

**Finance reading:** Mariana and Felipe use this more naturally than MSE in USD². Report alongside MSE/RMSE in V4 and the notebook Finance summary.

**Code:** `mean_absolute_percentage_error()` in `evaluate.py` — holdout only; does not feed model training.

---

### PSI — Population Stability Index (train vs holdout target)

**What it measures:** Whether **revenue levels shifted** between the training era (2016–2023) and the holdout era (2024–2025). Revenue is binned using **training** quantiles; PSI compares the proportion of months in each bin for train vs test **actual** `revenue_usd`.

**Finance reading:** PSI answers: *“Did the business regime change between when we trained and when we evaluate?”* High PSI means the holdout period lives in a different part of the revenue distribution than training — the model may need retraining or regime-aware features even if point forecasts look acceptable on MSE.

**How to read:**

| PSI (rule of thumb) | Interpretation |
| ------------------- | -------------- |
| **&lt; 0.10** | Very stable — holdout target mix matches training |
| **0.10 – 0.25** | Moderate shift — worth investigating |
| **&gt; 0.25** | Significant shift — training distribution may not represent holdout |

Holdout samples are small (24 months), so PSI can be sensitive; interpret alongside V2 (train/holdout timeline), not in isolation.

**Code:** `psi_score(y_train, y_test)` in `evaluate.py` — bin edges from training targets, standard PSI formula.

**Not the same as:** comparing test actual vs test predicted (forecast-mix calibration). That supplementary check is visualized in **V5** via `forecast_mix_chi2_score()`.

---

### Gini — Normalized Gini (ranking quality)

**What it measures:** If you **rank** holdout months by predicted revenue (highest forecast first), how well does that ordering match ranking by **actual** revenue? Normalized Gini divides the model’s score by a perfect ranker (1.0 = perfect).

**Finance reading:** Gini answers: *“When the model says December will be bigger than March, is it usually right?”* Useful for planning and prioritization even when exact dollar forecasts are off.

**How to read:**

| Gini | Interpretation |
| ---- | -------------- |
| **1.0** | Perfect ranking of months vs actuals |
| **0.7 – 0.9** | Strong ranking — model separates good vs weak months well |
| **~0.5** | Weak — barely better than random ordering |
| **0.0** | No ranking signal |

**Code:** `normalized_gini()` in `evaluate.py` — Lorenz-style Gini on actuals ordered by predicted values.

---

### K2 — D'Agostino-Pearson K² on residuals

**What it measures:** Whether holdout **forecast errors** (`actual − predicted`) look like random noise or have a **systematic shape** (skew, heavy tails). Uses SciPy `normaltest` (D'Agostino-Pearson K² statistic).

**Finance reading:** K2 answers: *“Are mistakes randomly scattered, or is there a pattern in how we miss?”* Complements MSE: average error can look fine while the model consistently under-predicts peaks (visible in V8).

**How to read:**

| K2 (D'Agostino) | Interpretation |
| --------------- | -------------- |
| **Low (near 0)** | Residuals closer to normal / random |
| **Elevated (e.g. &gt; ~6)** | Non-normal error shape — investigate V8 |

**Code:** `k2_score(y_test, y_pred)` in `evaluate.py` — D'Agostino-Pearson on holdout residuals.

**Supplementary:** V5 binned actual vs predicted chart and `forecast_mix_chi2_score()` show **forecast calibration** across revenue buckets — a different question from residual normality.

---

## Why MSE alone is not enough

A forecasting model can show **acceptable MSE** and still be **unsafe for Finance** because:

1. **Scale vs shape** — MSE averages errors; it does not show train→holdout target drift (PSI) or structured errors (K2).
2. **Regime shift** — Holdout years may sit in a higher-revenue band than training; MSE alone does not flag that the model was trained on a different world (PSI).
3. **Error shape** — Skewed or patterned residuals break planning confidence even when average error is moderate (K2, V8).
4. **Ranking failures** — Dollar error may be moderate while the model ranks months wrong for staffing or inventory (Gini).
5. **Memorization** — Training error can look good while holdout error does not; we only report **test** metrics for an honest read.

**Practical rule for Brasaland:** Read **MSE/RMSE/MAPE** for overall magnitude, **Gini** for “does it know which months are big?”, **PSI** for “did revenue distribution shift train→holdout?”, **K2** for “are errors random?”, **V5** for forecast-mix calibration, and **V1’s uncertainty band** for planning ranges rather than a single point.

---

## Outputs

| Artifact | Location |
| -------- | -------- |
| Chart PNGs (V1–V8) | `docs/forecasting/outputs/` |
| Evaluation charts (V9–V10) | `docs/forecasting/outputs/v9_learning_curve.png`, `v10_cv_fold_metrics.png` |
| Metrics markdown (V4) | `docs/forecasting/outputs/v4_metrics_summary.md` |
| Technical evaluation report | `docs/forecasting/EVALUATION-report.md` |
| Interactive report | `notebooks/sales_forecasting.ipynb` |
| Evaluation notebook | `notebooks/evaluating_regression.ipynb` |

---

## Verification

```bash
# All forecasting pipeline tests (split, model, visualize)
cd services/api && uv run pytest tests/pipelines/test_sales_forecast_split.py \
  tests/pipelines/test_sales_forecast_model.py \
  tests/pipelines/test_sales_forecast_visualize.py -q

# Regenerate chart PNGs without the notebook
cd services/api && uv run python -c "
import sys; sys.path.insert(0, '../..')
from data.forecasting.visualize import save_all_visuals
save_all_visuals()
"
```

Open `notebooks/sales_forecasting.ipynb` with kernel **Brasaland Forecasting (Python 3.12)** and **Run All** for the full Finance walkthrough.
