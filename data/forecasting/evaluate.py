"""Evaluation metrics for sales forecasting (context-19, test set only)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import normaltest
from sklearn.metrics import mean_squared_error

DEFAULT_BIN_COUNT = 10
EPSILON = 1e-6
# D'Agostino-Pearson K² critical region (~p<0.05, df=2) for residual normality checks.
K2_RESIDUAL_ALERT_THRESHOLD = 6.0


@dataclass(frozen=True)
class ForecastMetrics:
    mse: float
    mape_pct: float
    psi: float
    gini: float
    k2: float

    def as_dict(self) -> dict[str, float]:
        return {
            "mse": self.mse,
            "mape_pct": self.mape_pct,
            "psi": self.psi,
            "gini": self.gini,
            "k2": self.k2,
        }


def mean_absolute_percentage_error(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> float:
    """Mean absolute percentage error on holdout, as a percentage (e.g. 5.2 = 5.2%)."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if len(y_true) == 0:
        return 0.0
    return float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100.0)


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


def _bin_breakpoints(reference: np.ndarray, *, n_bins: int) -> np.ndarray:
    return np.unique(np.quantile(reference, np.linspace(0.0, 1.0, n_bins + 1)))


def psi_score(
    y_reference: np.ndarray,
    y_comparison: np.ndarray,
    *,
    n_bins: int = DEFAULT_BIN_COUNT,
) -> float:
    """
    Population Stability Index: target distribution shift (reference → comparison).

    Finance use: compare **training-period revenue** (reference) to **holdout revenue**
    (comparison). Bin edges come from the reference sample only.
    """
    y_ref = np.asarray(y_reference, dtype=float)
    y_cmp = np.asarray(y_comparison, dtype=float)
    breakpoints = _bin_breakpoints(y_ref, n_bins=n_bins)
    if len(breakpoints) < 2:
        return 0.0

    ref_counts, _ = np.histogram(y_ref, bins=breakpoints)
    cmp_counts, _ = np.histogram(y_cmp, bins=breakpoints)
    ref_pct = ref_counts / len(y_ref)
    cmp_pct = cmp_counts / len(y_cmp)

    ref_pct = np.clip(ref_pct, EPSILON, None)
    cmp_pct = np.clip(cmp_pct, EPSILON, None)
    return float(np.sum((cmp_pct - ref_pct) * np.log(cmp_pct / ref_pct)))


def k2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    D'Agostino-Pearson K² on holdout residuals (actual − predicted).

    Lower values suggest errors look closer to random noise; elevated values suggest
    systematic error shape (skew, heavy tails) — see V8 residual plot.
    """
    residuals = np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float)
    if len(residuals) < 8:
        return 0.0
    if float(np.std(residuals)) < EPSILON:
        return 0.0

    stat, _p_value = normaltest(residuals)
    return float(stat)


def forecast_mix_chi2_score(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    *,
    n_bins: int = DEFAULT_BIN_COUNT,
) -> float:
    """
    Supplementary chi-square on binned holdout actual vs predicted revenue mix.

    Supports V5 (forecast calibration visual). Not the Finance K² residual test.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    breakpoints = _bin_breakpoints(y_true, n_bins=n_bins)
    if len(breakpoints) < 2:
        return 0.0

    actual_counts, _ = np.histogram(y_true, bins=breakpoints)
    pred_counts, _ = np.histogram(y_pred, bins=breakpoints)
    n = len(y_true)
    expected = (pred_counts / n) * n
    expected = np.clip(expected, EPSILON, None)
    chi2 = np.sum((actual_counts - expected) ** 2 / expected)
    return float(chi2)


def evaluate_forecast(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    *,
    y_train: np.ndarray,
) -> ForecastMetrics:
    """Compute MSE, MAPE, PSI, normalized Gini, and K2 on the holdout set."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    y_train = np.asarray(y_train, dtype=float)
    return ForecastMetrics(
        mse=float(mean_squared_error(y_true, y_pred)),
        mape_pct=mean_absolute_percentage_error(y_true, y_pred),
        psi=psi_score(y_train, y_true),
        gini=normalized_gini(y_true, y_pred),
        k2=k2_score(y_true, y_pred),
    )
