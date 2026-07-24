# Sales forecasting — setup and metrics

**Plan:** [context-19](../../memory-bank/historical-reference/context-19-sales-forecasting-regression.md)  
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
| **PSI** | Distribution drift: predicted vs actual revenue mix | Lower | V5 (binned distribution) |
| **Gini** | How well the model ranks high vs low months | Higher (max 1.0) | V1, V7 |
| **K2** | Range-level bias across revenue buckets | Closer to 0 | V5, V8 |

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

### PSI — Population Stability Index

**What it measures:** Whether the **shape** of predicted revenue matches the **shape** of actual revenue on the holdout. Revenue is split into bins (by actual revenue levels); PSI compares the **proportion** of months in each bin for actuals vs predictions.

**Finance reading:** PSI answers: *“Does the model forecast the same mix of strong, average, and weak months as we actually had?”* A model could hit average error (MSE) while systematically putting too many months in the “low revenue” bucket and too few in “high revenue” — PSI catches that.

**How to read:**

| PSI (rule of thumb) | Interpretation |
| ------------------- | -------------- |
| **&lt; 0.10** | Very stable — predicted distribution closely matches actual |
| **0.10 – 0.25** | Moderate shift — worth investigating |
| **&gt; 0.25** | Significant shift — predictions may not match business reality |

Holdout samples are small (24 months), so PSI can be sensitive; use it together with V5 (binned chart), not in isolation.

**Code:** `psi_score()` in `evaluate.py` — 10 equal-frequency bins from test actuals, standard PSI formula.

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

### K2 — Chi-square score on binned distributions

**What it measures:** After bucketing holdout months into revenue ranges, K2 compares **counts** of actual vs predicted months in each bucket using a chi-square-style statistic. **K2 → 0** means proportions align well; **large K2** means structural bias in specific revenue ranges (e.g. under-predicting peak months).

**Finance reading:** K2 answers: *“In which revenue bands is the model systematically wrong?”* It complements MSE: you can have moderate average error while still missing every peak month (high K2, visible in V5/V8).

**How to read:**

| K2 | Interpretation |
| -- | -------------- |
| **Near 0** | Good fit across revenue buckets |
| **Large** | Systematic over- or under-prediction in one or more ranges — see V5 and V8 |

**Code:** `k2_score()` in `evaluate.py` — same 10-bin edges as PSI, chi-square on actual counts vs expected from predicted proportions.

**Course definition:** Bucket predictions and actuals, compare proportions. Catches systematic bias that a single MSE number can hide.

---

## Why MSE alone is not enough

A forecasting model can show **acceptable MSE** and still be **unsafe for Finance** because:

1. **Scale vs shape** — MSE averages errors; it does not show if forecasts are consistently too high or too low in certain seasons (PSI, K2).
2. **Range-level bias** — Under-predicting every strong month and over-predicting weak months can partially cancel in MSE but break planning (K2, V5, V8).
3. **Ranking failures** — Dollar error may be moderate while the model ranks months wrong for staffing or inventory (Gini).
4. **Memorization** — Training error can look good while holdout error does not; we only report **test** metrics for an honest read.
5. **Seasonal blind spots** — Missing recurring peaks (e.g. year-end) may not dominate MSE but shows up in binned metrics and residual charts (V7, V8).

**Practical rule for Brasaland:** Read **MSE/RMSE** for overall magnitude, **Gini** for “does it know which months are big?”, **PSI + K2 + V5** for “does the forecast mix match reality?”, and **V1’s uncertainty band** for planning ranges rather than a single point.

---

## Outputs

| Artifact | Location |
| -------- | -------- |
| Chart PNGs (V1–V8) | `docs/forecasting/outputs/` |
| Metrics markdown (V4) | `docs/forecasting/outputs/v4_metrics_summary.md` |
| Interactive report | `notebooks/sales_forecasting.ipynb` |

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
