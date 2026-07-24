"""Sales forecast feature, train, and evaluate tests (context-19 step 4)."""

from __future__ import annotations

import numpy as np

from data.forecasting.evaluate import evaluate_forecast, k2_score, normalized_gini, psi_score
from data.forecasting.features import FEATURE_COLUMNS, build_feature_frame, feature_matrix
from data.forecasting.load import load_sales
from data.forecasting.split import temporal_train_test_split
from data.forecasting.train import RANDOM_STATE, predict_with_uncertainty, train_sales_model


def test_feature_frame_uses_lags_only_and_drops_initial_rows():
    frame = load_sales()
    featured = build_feature_frame(frame)
    assert list(FEATURE_COLUMNS) == [
        "calendar_month",
        "months_since_start",
        "revenue_lag_1",
        "revenue_lag_3",
        "revenue_lag_12",
    ]
    assert "covers_served" not in FEATURE_COLUMNS
    assert "avg_ticket_usd" not in FEATURE_COLUMNS
    assert len(featured) == len(frame) - 12

    x, y, _ = feature_matrix(featured)
    assert len(x.columns) == 5
    assert len(y) == len(featured)


def test_train_and_evaluate_on_holdout():
    artifacts, matrices = train_sales_model()
    assert artifacts.model.random_state == RANDOM_STATE
    assert matrices.x_train.shape[0] == 84
    assert matrices.x_test.shape[0] == 24

    y_pred = artifacts.model.predict(matrices.x_test)
    metrics = evaluate_forecast(matrices.y_test, y_pred)

    assert metrics.mse >= 0.0
    assert np.isfinite(metrics.psi)
    assert np.isfinite(metrics.gini)
    assert metrics.k2 >= 0.0
    assert set(metrics.as_dict()) == {"mse", "psi", "gini", "k2"}


def test_predict_with_uncertainty_band_ordering():
    artifacts, matrices = train_sales_model()
    mean, low, high = predict_with_uncertainty(artifacts.model, matrices.x_test)
    assert len(mean) == len(matrices.y_test)
    assert np.all(low <= mean)
    assert np.all(mean <= high)


def test_metrics_perfect_prediction_near_zero_error():
    y = np.array([500_000.0, 600_000.0, 700_000.0, 800_000.0])
    metrics = evaluate_forecast(y, y)
    assert metrics.mse == 0.0
    assert abs(metrics.psi) < 1e-6
    assert abs(normalized_gini(y, y) - 1.0) < 1e-6
    assert k2_score(y, y) < 1e-5


def test_featured_split_preserves_temporal_boundaries():
    featured = build_feature_frame(load_sales())
    train, test = temporal_train_test_split(featured)
    assert len(train) == 84
    assert len(test) == 24
