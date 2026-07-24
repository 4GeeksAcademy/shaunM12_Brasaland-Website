# Technical Evaluation Report — Brasaland Sales Forecast (Context-20)

**Model:** Random Forest from context-19 (`random_state=42`, unchanged)  
**Evaluator audience:** Tech lead (formal evaluation before staging promotion)  
**Holdout:** 2024–2025 (24 months — never used in CV or learning-curve fit)  
**Companion notebook:** [notebooks/evaluating_regression.ipynb](../../notebooks/evaluating_regression.ipynb)  
**Context-19 artifacts:** [notebooks/sales_forecasting.ipynb](../../notebooks/sales_forecasting.ipynb), [v4_metrics_summary.md](./outputs/v4_metrics_summary.md)

---

## 1. Executive summary

The context-19 Random Forest is **partially fit for purpose** but **not promotion-ready on distribution metrics alone**.

| Signal | Read |
| ------ | ---- |
| **Holdout MAPE ~6%** | Moderate average dollar error — acceptable at a glance for Mariana/Felipe |
| **Holdout Gini ~0.74** | Ranking is useful — model often knows which months are stronger |
| **Holdout PSI ~4.48 (D20)** | Forecast revenue **mix** does not match actual mix |
| **Holdout K2 ~16M** | Systematic bias across revenue buckets (peaks/slow months) |
| **5-fold temporal CV** | Validation MAPE **5.87% ± 0.86%** — stable and aligned with holdout ~6% |
| **Learning curve** | Training MAPE ~**1.4%** vs validation ~**5–7%** — wide persistent gap |

**Explicit diagnosis (course):** **Overfitting** on the training era (low train error, higher validation error with a stable gap), compounded by **structural calibration failure** on the holdout (high PSI/K2 despite moderate MAPE).

**Verdict:** Do not promote to staging based on MAPE alone. The model ranks months reasonably but does not reproduce the holdout revenue distribution reliably.

---

## 2. Frozen baseline (context-19 holdout — unchanged)

Reproduced via `train_sales_model()` + `evaluate_forecast()` on 2024–2025. Same numbers as V4 / `v4_metrics_summary.md`.

| Metric | Value | Finance read |
| ------ | ----- | ------------ |
| MSE | 3,386,101,902.59 | RMSE ≈ **$58,190**/month |
| MAPE | **6.00%** | Average % error vs actual revenue |
| PSI (D20) | **4.48** | Predicted vs actual revenue mix mismatch |
| Gini | **0.74** | Decent month ranking |
| K2 | **~16,000,000** | Range-level distributional bias |

Low MAPE does **not** override high PSI/K2 — see [README.md](./README.md) narrative.

---

## 3. Walk-forward temporal cross-validation

**Method:** 5 expanding-window folds on featured train era only (validation years 2019–2023). No shuffle. Holdout 2024–2025 excluded from all folds.

| Fold | Val year | Val MAE (USD) | Val RMSE (USD) | Val MAPE |
| ---- | -------- | --------------- | -------------- | -------- |
| 1 | 2019 | 41,621 | 45,983 | 6.85% |
| 2 | 2020 | 28,193 | 35,071 | 4.56% |
| 3 | 2021 | 36,288 | 43,447 | 5.45% |
| 4 | 2022 | 38,030 | 44,269 | 5.69% |
| 5 | 2023 | 50,540 | 57,569 | 6.79% |

**Aggregate (course requirement — mean ± std on validation):**

| Metric | Mean ± std |
| ------ | ---------- |
| MAE | **$38,935 ± $7,282** |
| RMSE | **$45,268 ± $7,213** |
| MAPE | **5.87% ± 0.86%** |

**Stability vs holdout:** CV mean MAPE (5.87%) is close to holdout MAPE (6.00%) — the holdout result is **not an outlier** relative to pre-2024 validation years. Fold 5 (2023 val) is the hardest (6.79%), suggesting recent train-era years are harder to generalize to.

**Chart:** [v10_cv_fold_metrics.png](./outputs/v10_cv_fold_metrics.png)

---

## 4. Learning curve (bias / variance)

**Method:** Expanding featured training windows (2017→2018 … 2017→2023) with one-year temporal validation slices; full train-era step at 84 rows. Pre-2024 only.

| Train rows | Train MAPE | Val MAPE |
| ---------- | ---------- | -------- |
| 24 | 1.42% | 6.85% |
| 36 | 1.36% | 4.56% |
| 48 | 1.31% | 5.45% |
| 60 | 1.46% | 5.69% |
| 72 | 1.47% | 6.79% |
| 84 | 1.46% | — |

**Pattern:**

- **Training error stays very low (~1.4% MAPE)** as data grows.
- **Validation error stays flat at ~5–7% MAPE** — does not converge down toward training.
- **Wide, persistent train/validation gap** → classic **overfitting** signature (model memorizes train-era noise; does not generalize proportionally).

This is **not** primarily underfitting (validation error would stay high while training error also stays high). Validation error is moderate, not “reasonably well fitted” in the sense of converging train/val curves.

**Chart:** [v9_learning_curve.png](./outputs/v9_learning_curve.png)

---

## 5. PSI diagnosis — D20 vs structural

| Metric | Value | Compares | Question |
| ------ | ----- | -------- | -------- |
| **D20 PSI** | 4.48 | Holdout actual vs holdout **predicted** | Does forecast mix match reality? |
| **Structural PSI** | 8.37 | Train-era actual vs holdout **actual** | Did the world shift between eras? |

**Both are elevated.**

- **Structural PSI high** → holdout actual revenue distribution differs from train-era history (regime / scale shift).
- **D20 PSI also high** → the model’s predicted mix on holdout still does not align with actuals, even beyond era shift alone.

**Supporting visuals (context-19, not regenerated):**

- [v5_binned_distribution.png](./outputs/v5_binned_distribution.png) — binned actual vs predicted mix
- [v7_seasonality_by_month.png](./outputs/v7_seasonality_by_month.png) — seasonal shape on holdout
- [v8_residuals.png](./outputs/v8_residuals.png) — systematic residual patterns by revenue level

---

## 6. Seasonality and residuals

Context-19 charts V7 and V8 (holdout only) show where dollar-level error hides:

- **V7** — December/January seasonality is visible on holdout; the model captures direction (Gini ~0.74) but not bucket-level proportions (PSI/K2).
- **V8** — Residuals are not symmetric across revenue levels; peak months show systematic under- or over-prediction patterns that MAPE alone averages away.

These visuals support the conclusion that **structural bias** (distribution/range) is the primary holdout failure mode, not random noise.

---

## 7. Metric selection and business justification

**Metrics computed:** MAE, RMSE, MAPE (training and validation in diagnostics; holdout rubric in context-19).

| Metric | Strength for Brasaland |
| ------ | ---------------------- |
| **MAPE** | Stakeholder-friendly (% language for Mariana/Felipe) — context-19 R5 |
| **MAE** | Typical dollar miss per month — easy to explain |
| **RMSE** | Penalizes large misses more (December peaks, January drops) |

**Primary metric for operations planning: RMSE**

Felipe (Operations) uses forecasts for **ingredient purchasing**. Missing a **large month** (December +20–30% seasonality) causes understocking and service failures; the cost of error scales with **magnitude of revenue miss**, not just average percentage. RMSE (√MSE) weights big misses more heavily than MAE, matching asymmetric operational pain when peak months are wrong.

**MAPE remains the stakeholder summary metric** on the holdout (context-19 R5). **RMSE is the primary technical metric** for this evaluation ticket when comparing CV folds and diagnosing peak-month risk.

Underestimating a high-revenue month is typically more costly than overestimating a low-revenue month for a chain with strong December seasonality — RMSE aligns with that asymmetry better than MAE alone.

---

## 8. Bias / variance conclusion

| Question | Answer |
| -------- | ------ |
| Underfitting, overfitting, or well fitted? | **Overfitting** (train/val MAPE gap), with **structural holdout bias** (PSI/K2) |
| Stable when train window changes? | **Yes** — CV MAPE 5.87% ± 0.86% tracks holdout ~6% |
| Safe for Finance on MAPE alone? | **No** — PSI/K2 show distribution/range failure |
| Safe for ranking months? | **Partially** — Gini ~0.74 supports prioritization, not bucket-level planning |

The learning curve shows classic **variance/overfitting** on the train era. Holdout PSI/K2 add **structural bias** — the model does not match the holdout revenue mix even when average percentage error looks moderate.

---

## 9. Recommendations (prose only — not implemented in context-20)

Per E9, no retraining was performed in this ticket. **Specific** actions consistent with the diagnosis:

1. **Regularize the existing RF** — reduce `max_depth` (currently 8) or increase `min_samples_leaf` to narrow the train/validation gap seen in V9; root cause: memorizing train-era noise on ~84 rows.
2. **Seasonality features** — explicit December/January indicators or stronger year-over-year terms to address V7/V8 peak/slack bias without using same-month covers/ticket (still D5-safe).
3. **Retrain after era shift** — structural PSI 8.37 suggests holdout era differs from train history; consider refit when 2024–2025-like regimes accumulate (future data ticket, not holdout tuning).
4. **Do not promote on MAPE alone** — require improved PSI/K2 or planning bands (context-19 V1 band) for Finance sign-off.

---

## Evaluation criteria checklist (course)

| Criterion | Evidence |
| --------- | -------- |
| Learning curve generated and interpreted | V9 + §4 — overfitting pattern |
| Temporal CV ≥5 folds, no shuffle, mean ± std | §3 + `diagnose.py` + V10 |
| ≥2 metrics with business justification | §7 — MAE, RMSE, MAPE; **RMSE primary** for ops |
| Explicit diagnosis backed by evidence | §1, §8 — **overfitting** + structural bias |
| Specific corrective action | §9 — regularization + seasonality (not generic) |
| Unit test on chronological folds | `test_cv_folds_chronological_order` |

---

## Artifacts

| Artifact | Path |
| -------- | ---- |
| V9 learning curve | [outputs/v9_learning_curve.png](./outputs/v9_learning_curve.png) |
| V10 CV folds | [outputs/v10_cv_fold_metrics.png](./outputs/v10_cv_fold_metrics.png) |
| Context-19 holdout table | [outputs/v4_metrics_summary.md](./outputs/v4_metrics_summary.md) |
| Diagnostics code | `data/forecasting/diagnose.py` |
| Tests | `services/api/tests/pipelines/test_sales_forecast_diagnose.py` |
