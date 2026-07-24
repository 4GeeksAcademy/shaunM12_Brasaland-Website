# Context 20 — Evaluating the Regression Model

**Ticket:** Formal evaluation / diagnosis of the context-19 sales forecast model  
**Type:** Diagnostic Python module + evaluation notebook + technical report + tests  
**Branch:** `evaluating-regression-model`  
**Status:** ✅ Complete — Phases 1–3 implemented  
**Depends on:** [context-19](./context-19-sales-forecasting-regression.md) (frozen model, holdout metrics, V1–V8)  
**Companion:** `docs/forecasting/EVALUATION-report.md`, `notebooks/evaluating_regression.ipynb`, `data/forecasting/diagnose.py`  
**Stakeholders:** Tech lead (primary); Mariana / Felipe / Lucía (downstream of honest read — no new “pass/fail” gates)

---

## Goal

Produce a **technical evaluation** of the **existing** Random Forest from context-19 — without retraining, retuning, or changing holdout metrics:

1. **Learning curve** on train-era data only (pre-2024) with temporal inner validation.
2. **Walk-forward temporal cross-validation** on featured 2017–2023 rows — holdout 2024–2025 never in any fold.
3. **Separate structural PSI** (train-era actual vs holdout actual) — distinct from context-19 D20 (test actual vs test predicted).
4. **Written technical report** explaining why MAPE can look acceptable while PSI/K2 are high.
5. **New visuals V9–V10**; reference context-19 V5/V7/V8 for distribution, seasonality, residuals.
6. **Unit tests** proving CV/curve date boundaries (no leakage into 2024–2025).

**Golden rule:** Context-20 is **additive**. Re-running `train_sales_model()` + `evaluate_forecast()` must still yield the same context-19 holdout snapshot.

---

## Scope boundary — context-19 vs context-20

| Topic | Context-19 (frozen ✅) | Context-20 (this ticket) |
| ----- | ---------------------- | ------------------------- |
| Purpose | Build RF + report holdout | Diagnose generalization and calibration |
| Model | `RandomForestRegressor(100, max_depth=8, random_state=42)` | **Same** — import only (E1) |
| Split | 8yr train / 2yr holdout (2024–2025) | Holdout **sacred**; CV/curve use pre-2024 only |
| Primary metrics | MSE, MAPE, PSI, Gini, K2 on holdout (D20 PSI formula) | MSE + MAPE on CV folds; full rubric stays on V4 |
| Code | `load`, `split`, `features`, `train`, `evaluate`, `visualize` | New **`diagnose.py`** only |
| Notebook | `sales_forecasting.ipynb` (V1–V8) | **`evaluating_regression.ipynb`** |
| Report | `docs/forecasting/README.md` (Finance metrics) | **`docs/forecasting/EVALUATION-report.md`** |
| Tests | 11 tests (`split`, `model`, `visualize`) | **Add** `test_sales_forecast_diagnose.py` |

---

## Frozen baseline (from context-19 — do not change)

Reproducible via `train_sales_model()` + `evaluate_forecast()`. Exported in `docs/forecasting/outputs/v4_metrics_summary.md`.

| Metric | Value | Role in context-20 |
| ------ | ----- | ------------------ |
| **MSE** | 3,386,101,902.59 | Reference holdout row in V10 / report |
| **MAPE** | 6.00% | Reference holdout row; compare to CV fold MAPE |
| **PSI (D20)** | 4.48 | Test actual vs test predicted — explain, do not redefine |
| **Gini** | 0.74 | Ranking OK; distribution may still fail |
| **K2** | ~16,000,000 | Range-level bias — cite V5/V8 |

**Row pipeline (unchanged):**

| Stage | Rows | Date span |
| ----- | ---- | --------- |
| Raw CSV | 120 | 2016-01 → 2025-12 |
| After `build_feature_frame` | 108 | 2017-01 → 2025-12 |
| Featured train | 84 | 2017-01 → 2023-12 |
| Featured holdout | 24 | 2024-01 → 2025-12 |

**Imports from context-19 (read-only):**

```python
from data.forecasting.train import RANDOM_STATE, create_model, train_sales_model
from data.forecasting.evaluate import evaluate_forecast
from data.forecasting.split import TEST_START, TRAIN_END, assert_no_split_leakage
from data.forecasting.features import build_feature_frame, feature_matrix
from data.forecasting.load import load_sales
```

---

## Decisions log (confirmed)

All items reviewed against context-19 locks R1–R7 and D1–D22. **Locked 2026-07-24.** Implementation must not change holdout metrics or context-19 acceptance criteria.

| ID | Topic | Locked choice | Notes |
| -- | ----- | ------------- | ----- |
| **E1** | Context-19 code | **Read-only** | No edits to `train.py`, `split.py`, `features.py`, `evaluate.py`, `visualize.py` |
| **E2** | Module layout | **`data/forecasting/diagnose.py`** | Learning curve, walk-forward CV, structural PSI, V9/V10 plot helpers |
| **E3** | Notebook | **`notebooks/evaluating_regression.ipynb`** | Do not extend `sales_forecasting.ipynb` |
| **E4** | Technical report | **`docs/forecasting/EVALUATION-report.md`** | Tech-lead narrative; memory-bank holds this plan only |
| **E5** | Learning curve | **Train-era only** | Pre-2024 featured rows; temporal inner val; holdout at most one labeled reference point |
| **E6** | Temporal CV | **Walk-forward pre-2024** | **≥5 folds** (2019–2023 val years); never include 2024–2025 in train or val |
| **E7** | CV metrics | **MAE + RMSE + MAPE** | Report **mean ± std** across folds; PSI/Gini/K2 optional in report only |
| **E8** | Structural PSI | **Separate diagnostic** | Train-era actual vs holdout actual; **D20 unchanged** |
| **E9** | Bias/variance | **Diagnose only** | Retraining recommendations in prose; no hyperparameter or feature changes |
| **E10** | Algorithm | **RF only** | Reference context-19 R1; no XGBoost |
| **E11** | Visuals | **V9 + V10 new PNGs** | Do not overwrite V1–V8 paths |
| **E12** | Tests | **`test_sales_forecast_diagnose.py`** | Leakage guards + CV/curve smoke; keep 11 context-19 tests green |

---

## Reconciliation — context-20 vs context-19 locks

| Context-19 lock | Context-20 respects it by |
| --------------- | ------------------------- |
| R1 Random Forest | E10 — evaluate same model |
| R4 D20 PSI | E8 — new metric name; V4 untouched |
| R5 MAPE on holdout | E7 — MAPE on CV val; V4 still official |
| D7/D8 temporal split | E5/E6/E12 — 2024–2025 out of curve/CV |
| R7 V1–V8 + 11 tests | E11 additive PNGs; E1 no edits to visualize tests |
| D12 `random_state=42` | Use `create_model()` / `RANDOM_STATE` from `train.py` |

---

## Locked implementation decisions (D1–D15)

| ID | Topic | Lock |
| -- | ----- | ---- |
| D1 | Context-19 artifacts | **Read-only** — call `train_sales_model()`, `evaluate_forecast()`; never fork hyperparams |
| D2 | New module | `data/forecasting/diagnose.py` — all context-20 logic here (E2) |
| D3 | Holdout boundary | `TEST_START = 2024-01-01` from `split.py` — no diagnose train/val row may have `month >= TEST_START` |
| D4 | Model factory | `create_model(random_state=RANDOM_STATE)` — `n_estimators=100`, `max_depth=8` |
| D5 | Scaler per slice | `StandardScaler.fit` on fold/curve train only; transform val only (same as D9 context-19) |
| D6 | Features | Same as context-19 D5 — calendar + lags; no new features (E9, R3) |
| D7 | Walk-forward folds | See [CV fold table](#walk-forward-cv-folds-locked) |
| D8 | Learning curve steps | Expanding train windows within featured 2017–2023; inner val = next calendar year(s) before 2024 |
| D9 | CV metrics | Per fold: **MAE, RMSE, MSE, MAPE** on validation; aggregate via `summarize_cv_results()` → **mean ± std** (course) |
| D10 | Structural PSI | `psi_structural_train_vs_holdout_actual()` — bins from **train-era actual** quantiles; compare train actual counts vs holdout **actual** counts; **not** D20 |
| D11 | D20 PSI | Unchanged in `evaluate.py` — import for holdout row only |
| D12 | Notebook | `notebooks/evaluating_regression.ipynb`; kernel **Brasaland Forecasting (Python 3.12)** |
| D13 | Report | `docs/forecasting/EVALUATION-report.md` — see [Report outline](#technical-report-outline) |
| D14 | New PNGs | `v9_learning_curve.png`, `v10_cv_fold_metrics.png` under `docs/forecasting/outputs/` |
| D15 | Tests | `services/api/tests/pipelines/test_sales_forecast_diagnose.py` |

---

## Walk-forward CV folds (locked)

Featured dates (after `build_feature_frame`). Holdout **never** in any fold. **Minimum 5 folds** (course / `MIN_CV_FOLDS = 5`).

| Fold | Train (featured) | Validation (featured) | Train rows ≈ | Val rows ≈ |
| ---- | ---------------- | --------------------- | ------------ | ---------- |
| **1** | 2017-01 → 2018-12 | 2019-01 → 2019-12 | 24 | 12 |
| **2** | 2017-01 → 2019-12 | 2020-01 → 2020-12 | 36 | 12 |
| **3** | 2017-01 → 2020-12 | 2021-01 → 2021-12 | 48 | 12 |
| **4** | 2017-01 → 2021-12 | 2022-01 → 2022-12 | 60 | 12 |
| **5** | 2017-01 → 2022-12 | 2023-01 → 2023-12 | 72 | 12 |

Per fold:

1. Slice featured frame by `month` (no shuffle).
2. `feature_matrix` on train and val slices.
3. `StandardScaler.fit` on fold train; `transform` train + val.
4. `fit_random_forest()` → `predict` on val.
5. Record **MAE, RMSE, MSE, MAPE** on validation (E7).
6. Aggregate with `summarize_cv_results()` → mean ± std across folds.

**Chronological guards (required in tests):**

```python
assert_cv_folds_chronological(folds)  # train before val; val years increasing
assert max(val_months) < TEST_START
assert_no_split_leakage(train_frame, val_frame)
```

---

## Learning curve (locked)

**Purpose:** Bias/variance read on train era — does error keep improving with more pre-2024 data?

**Data rule (E5):** All curve fit/validation slices use featured rows with `month < TEST_START` only.

**Suggested steps (expanding train end year):**

| Step | Train (featured) | Inner validation | Train rows ≈ |
| ---- | ---------------- | ---------------- | ------------ |
| 1 | 2017-01 → 2018-12 | 2019 | 24 |
| 2 | 2017-01 → 2019-12 | 2020 | 36 |
| 3 | 2017-01 → 2020-12 | 2021 | 48 |
| 4 | 2017-01 → 2021-12 | 2022 | 60 |
| 5 | 2017-01 → 2022-12 | 2023 | 72 |
| 6 | 2017-01 → 2023-12 | — (full train era) | 84 |

Each step: same pipeline as CV fold (scaler on train slice, same RF hyperparams).

**Plot (V9):**

- X-axis: featured training row count or last train month
- Y-axis: **RMSE (USD)** primary for course; **MAPE (%)** for stakeholder read (R5)
- Lines: **Training** and **validation** error (MAE/RMSE/MAPE available on `LearningCurvePoint`)
- Optional annotation: “Context-19 holdout MAPE ~6% (2024–2025)” — **not** used to fit the curve

**Interpretation guide (for report):**

| Pattern | Read |
| ------- | ---- |
| Train ↓, val ↓ with size | Still learning — possible underfitting at full 84 rows |
| Train ↓, val flat/↑ | Overfitting gap — RF memorizing train-era noise |
| Val stable, holdout PSI (D20) high | Structural / distribution issue more than sample size (link E8, V5) |

---

## Structural PSI vs D20 PSI (E8)

| Metric | Code home | Compares | Question |
| ------ | --------- | -------- | -------- |
| **D20 PSI** | `evaluate.py` → `psi_score(y_test, y_pred)` | Holdout **actual** vs holdout **predicted** | Does forecast **mix** match reality? (V4) |
| **Structural PSI** | `diagnose.py` only | Train-era **actual** vs holdout **actual** | Did the **world** shift between eras? |

**Naming in docs:** Never label structural PSI as “V4 PSI” or overwrite D20.

**Binning lock for structural PSI:** Use quantile breakpoints from **train-era actual** `revenue_usd` (same `DEFAULT_BIN_COUNT=10` style as `evaluate.py`); apply bins to both train actuals and holdout actuals; standard PSI formula on proportions.

**Report combinations:**

| D20 high | Structural high | Interpretation |
| -------- | ----------------- | -------------- |
| Yes | No | Model mix wrong; holdout actuals similar to history |
| Yes | Yes | Regime shift + poor forecast mix |
| Yes | Moderate | Mixed — use CV MAPE + V5/V7 |

---

## File layout

```text
data/forecasting/
  diagnose.py                              # NEW — learning curve, CV, structural PSI, V9/V10 helpers
notebooks/
  evaluating_regression.ipynb              # NEW — evaluation narrative
  sales_forecasting.ipynb                  # UNCHANGED (context-19)
docs/forecasting/
  EVALUATION-report.md                     # NEW — tech-lead report
  README.md                                # optional one-line pointer to EVALUATION-report
  outputs/
    v1_…png … v8_…png                      # UNCHANGED
    v9_learning_curve.png                  # NEW
    v10_cv_fold_metrics.png                # NEW
services/api/tests/pipelines/
  test_sales_forecast_diagnose.py          # NEW
  test_sales_forecast_*.py                 # UNCHANGED (11 tests)
memory-bank/historical-reference/
  context-20-evaluating-regression-model.md  # this file
```

---

## `diagnose.py` — suggested public API

Implement these (names may match exactly for recreate-from-doc):

```python
MIN_CV_FOLDS = 5

@dataclass(frozen=True)
class CvFoldResult:
    fold_id: int
    train_end: str
    val_start: str
    val_end: str
    mse: float
    mae: float
    rmse: float
    mape_pct: float

@dataclass(frozen=True)
class CvSummary:
    fold_count: int
    val_mae_mean: float
    val_mae_std: float
    val_rmse_mean: float
    val_rmse_std: float
    val_mse_mean: float
    val_mse_std: float
    val_mape_pct_mean: float
    val_mape_pct_std: float

@dataclass(frozen=True)
class LearningCurvePoint:
    train_rows: int
    train_end: str
    train_mae: float
    train_rmse: float
    train_mape_pct: float
    val_mae: float | None
    val_rmse: float | None
    val_mape_pct: float | None

def walk_forward_cv_folds() -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    """Return (train_frame, val_frame) pairs — ≥5 temporal folds."""

def assert_cv_folds_chronological(folds) -> None:
    """Course: preserve chronological order within and across folds."""

def run_walk_forward_cv() -> list[CvFoldResult]:
    """Run CV; validation MAE, RMSE, MSE, MAPE per fold."""

def summarize_cv_results(results) -> CvSummary:
    """Mean ± std across folds (course requirement)."""

def learning_curve_points() -> list[LearningCurvePoint]:
    """Train/val MAE, RMSE, MAPE per expanding window; pre-TEST_START only."""

def psi_structural_train_vs_holdout_actual() -> float:
    """Train-era actual vs holdout actual PSI — NOT D20."""
```

**Dependencies:** Reuse `evaluate.py` for `evaluate_forecast`, `mean_squared_error` path; reuse `psi_score` **logic** in a new function with different inputs — do not change `psi_score` signature for D20.

---

## Visual aids (V9–V10)

### V9 — Learning curve

| Field | Value |
| ----- | ----- |
| **Purpose** | Show bias/variance vs training size on train era |
| **Chart type** | Line chart |
| **Title** | `Learning Curve — Random Forest (Train Era Only)` |
| **X-axis label** | `Featured training months (count)` or `Last training month` |
| **Y-axis label** | `MAPE (%)` |
| **Legend** | `Training MAPE`, `Validation MAPE (temporal)` |
| **Caption** | Holdout 2024–2025 excluded from curve fitting; see context-19 V4 for final holdout. |
| **Output file** | `docs/forecasting/outputs/v9_learning_curve.png` |

### V10 — CV fold metrics

| Field | Value |
| ----- | ----- |
| **Purpose** | Show temporal stability before holdout |
| **Chart type** | Bar chart (or line across folds) |
| **Title** | `Walk-Forward CV — Validation MAPE by Fold` |
| **X-axis label** | `Validation year` (2019 / 2020 / 2021 / 2022 / 2023) |
| **Y-axis label** | `Validation RMSE (USD)` or MAPE (%) — report shows mean ± std in caption |
| **Optional reference** | Horizontal line: context-19 holdout MAPE ~6% — labeled, not a CV fold |
| **Caption** | Folds use pre-2024 data only; 2024–2025 is the single final holdout. |
| **Output file** | `docs/forecasting/outputs/v10_cv_fold_metrics.png` |

**Cross-reference (no re-export required):** V5 binned distribution, V7 seasonality, V8 residuals — cite paths in report and notebook.

---

## Notebook structure (`evaluating_regression.ipynb`)

| Section | Purpose |
| ------- | ------- |
| Setup | Repo root on path; kernel **Brasaland Forecasting (Python 3.12)**; `random_state` note |
| Context-19 baseline | `train_sales_model()` + `evaluate_forecast()` — print `as_dict()`; must match V4 |
| Walk-forward CV | `run_walk_forward_cv()` + `summarize_cv_results()` — fold table + mean ± std |
| Learning curve | `learning_curve_points()` + V9 |
| Structural PSI | `psi_structural_train_vs_holdout_actual()` vs D20 from baseline |
| Link to context-19 visuals | Markdown links to V5, V7, V8 PNGs |
| V10 | CV fold chart |
| Summary | Bullet summary → paste into `EVALUATION-report.md` |

**Do not:** re-export V1–V8 over existing filenames; retrain with different hyperparams; add XGBoost cells.

---

## Technical report outline (`docs/forecasting/EVALUATION-report.md`)

1. **Executive summary** — Partially fit for purpose: Gini ~0.74 (ranking); PSI/K2 poor (distribution/range); MAPE ~6% alone insufficient.
2. **Frozen baseline** — Copy holdout table from V4 / `v4_metrics_summary.md` (unchanged numbers).
3. **Walk-forward CV** — Fold table (E6/E7); stability vs holdout MAPE.
4. **Learning curve** — Over/underfitting read (E5/E9).
5. **PSI diagnosis** — D20 vs structural PSI (E8); tie to V5.
6. **Seasonality & residuals** — Reference V7, V8.
7. **Bias/variance conclusion** — Structural bias > classic high-variance overfit (E9).
8. **Recommendations (prose only)** — Future retrain/features/data; **not implemented in this ticket**.

---

## Testing

**Path:** `services/api/tests/pipelines/test_sales_forecast_diagnose.py`

| Test | Asserts |
| ---- | ------- |
| `test_cv_folds_exclude_holdout` | **5 folds**; all months `< TEST_START`; train before val |
| `test_cv_folds_chronological_order` | `assert_cv_folds_chronological` — course temporal order |
| `test_learning_curve_pre_holdout_only` | 6 curve steps; MAE/RMSE on train; pre-holdout only |
| `test_run_walk_forward_cv_returns_five_folds_with_finite_metrics` | `len(results) == 5`; finite MAE, RMSE, MSE, MAPE |
| `test_summarize_cv_results_mean_std` | `CvSummary` mean ± std across 5 folds |
| `test_diagnose_uses_random_state_42` | `random_state == 42` |
| `test_walk_forward_cv_expected_row_counts` | Train rows 24/36/48/60/72; val 12 each |
| `test_context19_holdout_metrics_unchanged` | E1 regression guard |

**Regression:** All **11** context-19 tests must still pass unchanged.

```bash
cd services/api && uv run pytest tests/pipelines/test_sales_forecast_split.py \
  tests/pipelines/test_sales_forecast_model.py \
  tests/pipelines/test_sales_forecast_visualize.py \
  tests/pipelines/test_sales_forecast_diagnose.py -q
```

---

## Explicit non-goals

- Editing context-19 modules (`train.py`, `evaluate.py`, `split.py`, `features.py`, `visualize.py`)
- Changing D20 PSI formula or V4 holdout snapshot
- Retuning RF (`max_depth`, `n_estimators`) or changing features (E9)
- XGBoost or `uv add xgboost` (R1, D14 context-19)
- Per-market features (R3)
- Shuffled k-fold or random month subsampling
- Using 2024–2025 in CV or learning-curve fit/validation
- Overwriting V1–V8 PNGs or extending `sales_forecasting.ipynb` as the evaluation deliverable
- FastAPI / backoffice forecast UI

---

## Acceptance criteria

- [x] `data/forecasting/diagnose.py` implements walk-forward CV (**≥5 folds**), learning curve (MAE/RMSE/MAPE), structural PSI, `summarize_cv_results()` mean ± std
- [x] V9 and V10 PNG export via `save_evaluation_visuals()` — `v9_learning_curve.png`, `v10_cv_fold_metrics.png`
- [x] All CV and curve date slices strictly before `TEST_START` (2024-01-01)
- [x] `train_sales_model()` + `evaluate_forecast()` holdout metrics unchanged from context-19 snapshot
- [x] D20 PSI still computed only in `evaluate.py`; structural PSI only in `diagnose.py`
- [x] `notebooks/evaluating_regression.ipynb` runs end-to-end
- [x] `docs/forecasting/EVALUATION-report.md` complete with recommendations prose-only (no model changes)
- [x] V9 and V10 PNGs exported with title, axes, legend (captions in `EVAL_CAPTIONS` for notebook/report Phase 3)
- [x] `test_sales_forecast_diagnose.py` passes; **11** context-19 tests still pass
- [x] No edits to context-19 acceptance artifacts required for green CI

---

## Evaluation map (rubric → evidence)

| Rubric theme | Evidence |
| ------------ | -------- |
| Honest evaluation / no holdout leakage | E5/E6/E12 tests; holdout only via context-19 baseline cell |
| Temporal validation (not random CV) | Walk-forward fold table + `test_cv_folds_exclude_holdout` |
| Learning curve / bias-variance | V9 + report §4 |
| Explains holdout metrics | Report §1, §5 — MAPE vs PSI/K2 |
| Reproducible | `RANDOM_STATE=42`; imports frozen `create_model()` |
| Technical report | `docs/forecasting/EVALUATION-report.md` |
| Unit tests | `test_sales_forecast_diagnose.py` + 11 context-19 tests |
| Extends without churn | V9/V10 new files; context-19 notebook untouched |

---

## Implementation order

1. [x] Add this context file + update `context-index.md`
2. [x] Implement `diagnose.py` — fold definitions + `run_walk_forward_cv()` first
3. [x] Add `test_sales_forecast_diagnose.py` (TDD on date guards)
4. [x] Add learning curve + `psi_structural_train_vs_holdout_actual()`
5. [x] Add V9/V10 plot helpers + `save_evaluation_visuals()`
6. [x] Create `evaluating_regression.ipynb`
7. [x] Write `docs/forecasting/EVALUATION-report.md`
8. [x] Optional: one-line pointer in `docs/forecasting/README.md`
9. [x] Full pytest (11 + diagnose) green; notebook Run All

---

## Verification notes

```bash
# Context-19 baseline unchanged (holdout snapshot)
cd services/api && uv run python -c "
import sys; sys.path.insert(0, '../..')
from data.forecasting.train import train_sales_model
from data.forecasting.evaluate import evaluate_forecast
artifacts, m = train_sales_model()
pred = artifacts.model.predict(m.x_test)
print(evaluate_forecast(m.y_test, pred).as_dict())
"

# Full test suite (after diagnose tests exist)
cd services/api && uv run pytest tests/pipelines/test_sales_forecast_*.py -q

# Evaluation notebook
jupyter notebook notebooks/evaluating_regression.ipynb
# Kernel: Brasaland Forecasting (Python 3.12)
```

**Expected holdout keys (unchanged):** `mse`, `mape_pct`, `psi`, `gini`, `k2` — values match context-19 snapshot within floating-point tolerance.

---

## Handoff from context-19

Use these artifacts as read-only inputs — do not regenerate with different code paths for the official score:

| Artifact | Path |
| -------- | ---- |
| Holdout metrics table | `docs/forecasting/outputs/v4_metrics_summary.md` |
| Charts V1–V8 | `docs/forecasting/outputs/v1_*.png` … `v8_*.png` |
| Finance metrics guide | `docs/forecasting/README.md` |
| Domain context | `docs/forecasting/CONTEXT-brasaland.md` |
| Forecasting notebook | `notebooks/sales_forecasting.ipynb` |
| Implementation plan | `memory-bank/historical-reference/context-19-sales-forecasting-regression.md` |
