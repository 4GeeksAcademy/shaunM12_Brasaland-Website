"""Sales forecast evaluation diagnostics tests (context-20 phase 1)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from data.forecasting.diagnose import (
    CV_FOLD_SPECS,
    LEARNING_CURVE_SPECS,
    MIN_CV_FOLDS,
    assert_cv_folds_chronological,
    assert_diagnose_no_holdout_leakage,
    learning_curve_points,
    psi_structural_train_vs_holdout_actual,
    run_walk_forward_cv,
    save_evaluation_visuals,
    summarize_cv_results,
    walk_forward_cv_folds,
)
from data.forecasting.load import load_sales
from data.forecasting.split import TEST_START, assert_no_split_leakage
from data.forecasting.train import RANDOM_STATE, create_model, train_sales_model


def test_cv_folds_exclude_holdout():
    assert len(CV_FOLD_SPECS) >= MIN_CV_FOLDS == 5
    folds = walk_forward_cv_folds()
    assert len(folds) == len(CV_FOLD_SPECS) == 5

    for train_frame, val_frame in folds:
        train_months = pd.to_datetime(train_frame["month"])
        val_months = pd.to_datetime(val_frame["month"])
        assert train_months.max() < TEST_START
        assert val_months.max() < TEST_START
        assert train_months.min() >= pd.Timestamp("2017-01-01")
        assert train_months.max() < val_months.min()
        assert_no_split_leakage(train_frame, val_frame)


def test_cv_folds_chronological_order():
    folds = walk_forward_cv_folds()
    assert_cv_folds_chronological(folds)


def test_learning_curve_pre_holdout_only():
    points = learning_curve_points()
    assert len(points) == len(LEARNING_CURVE_SPECS) == 6

    featured = load_sales()
    assert_diagnose_no_holdout_leakage(featured)

    last_point = points[-1]
    assert last_point.val_mape_pct is None
    assert last_point.val_mae is None
    assert last_point.val_rmse is None
    assert last_point.train_rows == 84
    assert last_point.train_end == "2023-12-01"
    assert last_point.train_mae >= 0.0
    assert last_point.train_rmse >= 0.0


def test_run_walk_forward_cv_returns_five_folds_with_finite_metrics():
    results = run_walk_forward_cv()
    assert len(results) == 5

    expected_val_years = [2019, 2020, 2021, 2022, 2023]
    for result, val_year in zip(results, expected_val_years, strict=True):
        assert result.fold_id in {1, 2, 3, 4, 5}
        assert result.val_start.startswith(f"{val_year}-01")
        assert result.val_end.startswith(f"{val_year}-12")
        assert result.mse >= 0.0
        assert result.mae >= 0.0
        assert result.rmse >= 0.0
        assert np.isfinite(result.mse)
        assert np.isfinite(result.mae)
        assert np.isfinite(result.rmse)
        assert result.mape_pct >= 0.0
        assert np.isfinite(result.mape_pct)
        assert abs(result.rmse - np.sqrt(result.mse)) < 1e-6


def test_summarize_cv_results_mean_std():
    results = run_walk_forward_cv()
    summary = summarize_cv_results(results)
    assert summary.fold_count == 5
    assert summary.val_mae_mean > 0.0
    assert summary.val_rmse_mean > 0.0
    assert summary.val_mape_pct_mean > 0.0
    assert summary.val_mae_std >= 0.0
    assert summary.val_rmse_std >= 0.0
    assert summary.val_mape_pct_std >= 0.0


def test_diagnose_uses_random_state_42():
    model = create_model()
    assert model.random_state == RANDOM_STATE == 42

    artifacts, _ = train_sales_model()
    assert artifacts.model.random_state == RANDOM_STATE


def test_walk_forward_cv_expected_row_counts():
    folds = walk_forward_cv_folds()
    expected_train_rows = [24, 36, 48, 60, 72]
    expected_val_rows = [12, 12, 12, 12, 12]

    for (train_frame, val_frame), train_n, val_n in zip(
        folds, expected_train_rows, expected_val_rows, strict=True
    ):
        assert len(train_frame) == train_n
        assert len(val_frame) == val_n


def test_psi_structural_train_vs_holdout_actual_is_finite():
    structural = psi_structural_train_vs_holdout_actual()
    assert np.isfinite(structural)
    assert structural >= 0.0


def test_context19_holdout_metrics_unchanged():
    """Regression guard (E1): baseline pipeline still produces expected metric keys."""
    artifacts, matrices = train_sales_model()
    y_pred = artifacts.model.predict(matrices.x_test)
    from data.forecasting.evaluate import evaluate_forecast

    metrics = evaluate_forecast(matrices.y_test, y_pred)
    payload = metrics.as_dict()
    assert set(payload) == {"mse", "mape_pct", "psi", "gini", "k2"}
    assert payload["mape_pct"] > 0.0
    assert payload["psi"] > 0.0


def test_save_evaluation_visuals_writes_v9_v10(tmp_path):
    from data.forecasting.visualize import save_all_visuals, build_visual_context

    saved = save_evaluation_visuals(output_dir=tmp_path)
    assert set(saved) == {"v9", "v10"}
    assert saved["v9"].name == "v9_learning_curve.png"
    assert saved["v10"].name == "v10_cv_fold_metrics.png"
    for path in saved.values():
        assert path.is_file()
        assert path.stat().st_size > 0

    # E11: context-19 V1–V8 keys unchanged; v9/v10 are additive only
    ctx = build_visual_context()
    v1_v8 = save_all_visuals(ctx, output_dir=tmp_path / "context19")
    assert set(v1_v8) == {"v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8"}
