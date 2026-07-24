"""Random Forest training for sales forecasting (context-19)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

from data.forecasting.features import FEATURE_COLUMNS, build_feature_frame, feature_matrix
from data.forecasting.load import load_sales
from data.forecasting.split import temporal_train_test_split

RANDOM_STATE = 42

# Algorithm choice (context-19 D3):
# - Data size: ~96 monthly training rows after lags — too small for heavy XGBoost tuning.
# - Explainability: Finance stakeholder needs feature importance and plain-language metrics.
# - Tuning time: Random Forest works well with modest defaults and yields a natural tree band.
# - Uncertainty: Per-tree predictions support the required 10th–90th percentile visualization.


@dataclass(frozen=True)
class ScaledMatrices:
    x_train: np.ndarray
    y_train: np.ndarray
    x_test: np.ndarray
    y_test: np.ndarray
    train_months: pd.Series
    test_months: pd.Series
    feature_names: tuple[str, ...]


@dataclass
class TrainArtifacts:
    model: RandomForestRegressor
    scaler: StandardScaler
    feature_names: tuple[str, ...]


def create_model(
    *,
    random_state: int = RANDOM_STATE,
    n_estimators: int = 100,
    max_depth: int = 8,
) -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
    )


def prepare_scaled_matrices(frame: pd.DataFrame | None = None) -> tuple[ScaledMatrices, StandardScaler]:
    """Load (optional), feature, split, and scale — scaler fit on train only."""
    raw = load_sales() if frame is None else frame
    featured = build_feature_frame(raw)
    train_frame, test_frame = temporal_train_test_split(featured)

    x_train, y_train, train_months = feature_matrix(train_frame)
    x_test, y_test, test_months = feature_matrix(test_frame)

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    matrices = ScaledMatrices(
        x_train=x_train_scaled,
        y_train=y_train.to_numpy(dtype=float),
        x_test=x_test_scaled,
        y_test=y_test.to_numpy(dtype=float),
        train_months=train_months,
        test_months=test_months,
        feature_names=FEATURE_COLUMNS,
    )
    return matrices, scaler


def fit_random_forest(
    x_train: np.ndarray,
    y_train: np.ndarray,
    *,
    random_state: int = RANDOM_STATE,
) -> RandomForestRegressor:
    model = create_model(random_state=random_state)
    model.fit(x_train, y_train)
    return model


def train_sales_model(
    frame: pd.DataFrame | None = None,
) -> tuple[TrainArtifacts, ScaledMatrices]:
    """End-to-end train pipeline returning fitted model and scaled holdout matrices."""
    matrices, scaler = prepare_scaled_matrices(frame)
    model = fit_random_forest(matrices.x_train, matrices.y_train)
    return (
        TrainArtifacts(
            model=model,
            scaler=scaler,
            feature_names=matrices.feature_names,
        ),
        matrices,
    )


def predict_mean(model: RandomForestRegressor, x: np.ndarray) -> np.ndarray:
    return model.predict(x)


def predict_tree_matrix(model: RandomForestRegressor, x: np.ndarray) -> np.ndarray:
    """Shape ``(n_trees, n_samples)`` for variability bands."""
    return np.vstack([tree.predict(x) for tree in model.estimators_])


def predict_with_uncertainty(
    model: RandomForestRegressor,
    x: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return mean prediction and 10th/90th percentile across trees."""
    tree_preds = predict_tree_matrix(model, x)
    mean = tree_preds.mean(axis=0)
    low = np.percentile(tree_preds, 10, axis=0)
    high = np.percentile(tree_preds, 90, axis=0)
    return mean, low, high
