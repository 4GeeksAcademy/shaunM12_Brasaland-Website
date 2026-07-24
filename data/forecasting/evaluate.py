"""Evaluation metrics for sales forecasting (context-19, test set only)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import mean_squared_error

DEFAULT_BIN_COUNT = 10
EPSILON = 1e-6


@dataclass(frozen=True)
class ForecastMetrics:
    mse: float
    psi: float
    gini: float
    k2: float

    def as_dict(self) -> dict[str, float]:
        return {
            "mse": self.mse,
            "psi": self.psi,
            "gini": self.gini,
            "k2": self.k2,
        }


def gini_coefficient(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Lorenz-style Gini based on ranking by predicted values."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    n = len(y_true)
    if n == 0:
        return 0.0

    ordered = np.lexsort((np.arange(n), -y_pred))
    y_sorted = y_true[ordered]
    total = y_sorted.sum()
    if total == 0.0:
        return 0.0
    cum = np.cumsum(y_sorted)
    return float(cum.sum() / total - (n + 1) / 2.0) / n


def normalized_gini(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Normalized Gini: model ranking quality vs perfect ranking."""
    model_gini = gini_coefficient(y_true, y_pred)
    perfect_gini = gini_coefficient(y_true, y_true)
    if perfect_gini == 0.0:
        return 0.0
    return float(model_gini / perfect_gini)


def psi_score(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    *,
    n_bins: int = DEFAULT_BIN_COUNT,
) -> float:
    """
    Population Stability Index on test actual vs test predicted (binned).

    Lower values indicate closer distributional match.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    breakpoints = np.unique(np.quantile(y_true, np.linspace(0.0, 1.0, n_bins + 1)))
    if len(breakpoints) < 2:
        return 0.0

    actual_counts, _ = np.histogram(y_true, bins=breakpoints)
    pred_counts, _ = np.histogram(y_pred, bins=breakpoints)
    actual_pct = actual_counts / len(y_true)
    pred_pct = pred_counts / len(y_pred)

    actual_pct = np.clip(actual_pct, EPSILON, None)
    pred_pct = np.clip(pred_pct, EPSILON, None)
    return float(np.sum((actual_pct - pred_pct) * np.log(actual_pct / pred_pct)))


def k2_score(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    *,
    n_bins: int = DEFAULT_BIN_COUNT,
) -> float:
    """
    Chi-square-style score on binned actual vs predicted proportions.

    K2 → 0 indicates good distributional fit; large K2 suggests structural bias.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    breakpoints = np.unique(np.quantile(y_true, np.linspace(0.0, 1.0, n_bins + 1)))
    if len(breakpoints) < 2:
        return 0.0

    actual_counts, _ = np.histogram(y_true, bins=breakpoints)
    pred_counts, _ = np.histogram(y_pred, bins=breakpoints)
    n = len(y_true)
    expected = (pred_counts / n) * n
    expected = np.clip(expected, EPSILON, None)
    chi2 = np.sum((actual_counts - expected) ** 2 / expected)
    return float(chi2)


def evaluate_forecast(y_true: np.ndarray, y_pred: np.ndarray) -> ForecastMetrics:
    """Compute MSE, PSI, normalized Gini, and K2 on the holdout set."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return ForecastMetrics(
        mse=float(mean_squared_error(y_true, y_pred)),
        psi=psi_score(y_true, y_pred),
        gini=normalized_gini(y_true, y_pred),
        k2=k2_score(y_true, y_pred),
    )
