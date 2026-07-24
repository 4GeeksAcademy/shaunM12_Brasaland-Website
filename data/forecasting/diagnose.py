"""Model evaluation diagnostics for sales forecasting (context-20).

Read-only on context-19 training code: imports ``fit_random_forest``, ``evaluate_forecast``,
and feature pipeline without modifying holdout metrics or D20 PSI in ``evaluate.py``.

Course alignment: temporal walk-forward CV with **at least 5 folds** on the training era only,
MAE + RMSE (and MAPE for stakeholder readability), mean ± std across folds.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler

from data.forecasting.evaluate import (
    DEFAULT_BIN_COUNT,
    EPSILON,
    mean_absolute_percentage_error,
)
from data.forecasting.features import TARGET_COLUMN, build_feature_frame, feature_matrix
from data.forecasting.load import load_sales
from data.forecasting.split import TEST_START, assert_no_split_leakage, temporal_train_test_split
from data.forecasting.train import RANDOM_STATE, fit_random_forest

FEATURED_TRAIN_START = pd.Timestamp("2017-01-01")
MIN_CV_FOLDS = 5

# Walk-forward CV (context-20 D7 / course): ≥5 folds, val years 2019–2023 on training era only.
CV_FOLD_SPECS: tuple[tuple[int, int], ...] = (
    (2018, 2019),
    (2019, 2020),
    (2020, 2021),
    (2021, 2022),
    (2022, 2023),
)

# Learning curve steps (context-20 D8): expanding train through train_end_year, inner val val_year.
LEARNING_CURVE_SPECS: tuple[tuple[int, int | None], ...] = (
    (2018, 2019),
    (2019, 2020),
    (2020, 2021),
    (2021, 2022),
    (2022, 2023),
    (2023, None),
)


@dataclass(frozen=True)
class SliceMetrics:
    mse: float
    mae: float
    rmse: float
    mape_pct: float


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


def _month_series(frame: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(frame["month"])


def _year_end(year: int) -> pd.Timestamp:
    return pd.Timestamp(f"{year}-12-01")


def _year_start(year: int) -> pd.Timestamp:
    return pd.Timestamp(f"{year}-01-01")


def _regression_errors(y_true: np.ndarray, y_pred: np.ndarray) -> SliceMetrics:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mse = float(mean_squared_error(y_true, y_pred))
    return SliceMetrics(
        mse=mse,
        mae=float(mean_absolute_error(y_true, y_pred)),
        rmse=float(np.sqrt(mse)),
        mape_pct=mean_absolute_percentage_error(y_true, y_pred),
    )


def _assert_pre_holdout(frame: pd.DataFrame, label: str) -> None:
    months = _month_series(frame)
    if len(months) == 0:
        raise ValueError(f"{label}: empty frame")
    if months.max() >= TEST_START:
        raise ValueError(f"{label}: dates must be before holdout {TEST_START.date()}")


def _slice_train_val(
    featured: pd.DataFrame,
    train_end_year: int,
    val_year: int | None,
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Slice featured rows: train from 2017 through train_end_year; optional val calendar year."""
    months = _month_series(featured)
    train_mask = (months >= FEATURED_TRAIN_START) & (months <= _year_end(train_end_year))
    train_frame = featured.loc[train_mask].copy().reset_index(drop=True)
    _assert_pre_holdout(train_frame, "train slice")

    if val_year is None:
        return train_frame, None

    val_mask = (months >= _year_start(val_year)) & (months <= _year_end(val_year))
    val_frame = featured.loc[val_mask].copy().reset_index(drop=True)
    _assert_pre_holdout(val_frame, "validation slice")
    assert_no_split_leakage(train_frame, val_frame)
    return train_frame, val_frame


def _fit_predict_metrics(
    train_frame: pd.DataFrame,
    val_frame: pd.DataFrame | None,
) -> tuple[SliceMetrics, SliceMetrics | None]:
    """Fit RF on train slice; return train metrics and validation metrics when provided."""
    x_train, y_train, train_months = feature_matrix(train_frame)
    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)

    model = fit_random_forest(x_train_scaled, y_train.to_numpy(dtype=float))
    if model.random_state != RANDOM_STATE:
        raise ValueError(f"Expected random_state={RANDOM_STATE}, got {model.random_state}")

    train_metrics = _regression_errors(y_train.to_numpy(), model.predict(x_train_scaled))

    if val_frame is None:
        return train_metrics, None

    x_val, y_val, val_months = feature_matrix(val_frame)
    if val_months.min() <= train_months.max():
        raise ValueError("Validation months must be strictly after training months (temporal CV).")

    x_val_scaled = scaler.transform(x_val)
    val_metrics = _regression_errors(y_val.to_numpy(), model.predict(x_val_scaled))
    return train_metrics, val_metrics


def _featured_pre_holdout(frame: pd.DataFrame | None = None) -> pd.DataFrame:
    raw = load_sales() if frame is None else frame
    featured = build_feature_frame(raw)
    pre_holdout = featured.loc[_month_series(featured) < TEST_START].copy()
    _assert_pre_holdout(pre_holdout, "featured pre-holdout")
    return pre_holdout.reset_index(drop=True)


def walk_forward_cv_folds(
    frame: pd.DataFrame | None = None,
) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    """Return (train_frame, val_frame) pairs — temporal walk-forward, ≥ ``MIN_CV_FOLDS``."""
    if len(CV_FOLD_SPECS) < MIN_CV_FOLDS:
        raise ValueError(f"CV_FOLD_SPECS must define at least {MIN_CV_FOLDS} folds")

    featured = _featured_pre_holdout(frame)
    folds: list[tuple[pd.DataFrame, pd.DataFrame]] = []
    for train_end_year, val_year in CV_FOLD_SPECS:
        train_frame, val_frame = _slice_train_val(featured, train_end_year, val_year)
        if val_frame is None or len(val_frame) == 0:
            raise ValueError(f"CV fold val_year={val_year} produced empty validation frame")
        folds.append((train_frame, val_frame))
    return folds


def assert_cv_folds_chronological(folds: list[tuple[pd.DataFrame, pd.DataFrame]]) -> None:
    """
    Verify temporal CV preserves chronological order (course requirement).

    - Within each fold: every train month is strictly before every val month.
    - Across folds: validation years are strictly increasing (walk-forward).
    """
    previous_val_year: int | None = None
    for fold_id, (train_frame, val_frame) in enumerate(folds, start=1):
        train_months = _month_series(train_frame)
        val_months = _month_series(val_frame)
        if train_months.max() >= val_months.min():
            raise ValueError(f"Fold {fold_id}: train months overlap or follow validation months")
        if not train_months.is_monotonic_increasing:
            raise ValueError(f"Fold {fold_id}: train months are not chronological")
        if not val_months.is_monotonic_increasing:
            raise ValueError(f"Fold {fold_id}: validation months are not chronological")

        val_year = int(val_months.iloc[0].year)
        if previous_val_year is not None and val_year <= previous_val_year:
            raise ValueError("Validation years must increase across walk-forward folds")
        previous_val_year = val_year


def run_walk_forward_cv(frame: pd.DataFrame | None = None) -> list[CvFoldResult]:
    """Run walk-forward CV; validation MAE, RMSE, MSE, MAPE per fold (course + E7)."""
    folds = walk_forward_cv_folds(frame)
    assert_cv_folds_chronological(folds)

    results: list[CvFoldResult] = []
    for fold_id, (train_frame, val_frame) in enumerate(folds, start=1):
        _, val_metrics = _fit_predict_metrics(train_frame, val_frame)
        assert val_metrics is not None
        val_months = _month_series(val_frame)
        results.append(
            CvFoldResult(
                fold_id=fold_id,
                train_end=str(_month_series(train_frame).max().date()),
                val_start=str(val_months.min().date()),
                val_end=str(val_months.max().date()),
                mse=val_metrics.mse,
                mae=val_metrics.mae,
                rmse=val_metrics.rmse,
                mape_pct=val_metrics.mape_pct,
            )
        )
    return results


def summarize_cv_results(results: list[CvFoldResult]) -> CvSummary:
    """Aggregate validation metrics as mean ± std across folds (course requirement)."""
    if len(results) < MIN_CV_FOLDS:
        raise ValueError(f"Need at least {MIN_CV_FOLDS} fold results, got {len(results)}")

    def _mean_std(values: list[float]) -> tuple[float, float]:
        arr = np.asarray(values, dtype=float)
        return float(arr.mean()), float(arr.std(ddof=0))

    mae_mean, mae_std = _mean_std([r.mae for r in results])
    rmse_mean, rmse_std = _mean_std([r.rmse for r in results])
    mse_mean, mse_std = _mean_std([r.mse for r in results])
    mape_mean, mape_std = _mean_std([r.mape_pct for r in results])

    return CvSummary(
        fold_count=len(results),
        val_mae_mean=mae_mean,
        val_mae_std=mae_std,
        val_rmse_mean=rmse_mean,
        val_rmse_std=rmse_std,
        val_mse_mean=mse_mean,
        val_mse_std=mse_std,
        val_mape_pct_mean=mape_mean,
        val_mape_pct_std=mape_std,
    )


def learning_curve_points(frame: pd.DataFrame | None = None) -> list[LearningCurvePoint]:
    """Expanding windows per context-20 D8; train/val MAE + RMSE + MAPE; pre-TEST_START only."""
    featured = _featured_pre_holdout(frame)
    points: list[LearningCurvePoint] = []
    for train_end_year, val_year in LEARNING_CURVE_SPECS:
        train_frame, val_frame = _slice_train_val(featured, train_end_year, val_year)
        train_metrics, val_metrics = _fit_predict_metrics(train_frame, val_frame)
        points.append(
            LearningCurvePoint(
                train_rows=len(train_frame),
                train_end=str(_year_end(train_end_year).date()),
                train_mae=train_metrics.mae,
                train_rmse=train_metrics.rmse,
                train_mape_pct=train_metrics.mape_pct,
                val_mae=val_metrics.mae if val_metrics else None,
                val_rmse=val_metrics.rmse if val_metrics else None,
                val_mape_pct=val_metrics.mape_pct if val_metrics else None,
            )
        )
    return points


def _psi_from_reference_distribution(
    reference: np.ndarray,
    compare: np.ndarray,
    *,
    n_bins: int = DEFAULT_BIN_COUNT,
) -> float:
    """PSI of ``compare`` vs ``reference`` using quantile bins from ``reference``."""
    reference = np.asarray(reference, dtype=float)
    compare = np.asarray(compare, dtype=float)
    if len(reference) == 0 or len(compare) == 0:
        return 0.0

    breakpoints = np.unique(np.quantile(reference, np.linspace(0.0, 1.0, n_bins + 1)))
    if len(breakpoints) < 2:
        return 0.0

    ref_counts, _ = np.histogram(reference, bins=breakpoints)
    cmp_counts, _ = np.histogram(compare, bins=breakpoints)
    ref_pct = ref_counts / len(reference)
    cmp_pct = cmp_counts / len(compare)
    ref_pct = np.clip(ref_pct, EPSILON, None)
    cmp_pct = np.clip(cmp_pct, EPSILON, None)
    return float(np.sum((cmp_pct - ref_pct) * np.log(cmp_pct / ref_pct)))


def psi_structural_train_vs_holdout_actual(frame: pd.DataFrame | None = None) -> float:
    """
    Structural PSI: train-era actual revenue vs holdout actual revenue (context-20 D10).

    Not D20 (which compares holdout actual vs holdout predicted in ``evaluate.py``).
    """
    raw = load_sales() if frame is None else frame
    featured = build_feature_frame(raw)
    train_frame, holdout_frame = temporal_train_test_split(featured)
    train_actual = train_frame[TARGET_COLUMN].to_numpy(dtype=float)
    holdout_actual = holdout_frame[TARGET_COLUMN].to_numpy(dtype=float)
    return _psi_from_reference_distribution(train_actual, holdout_actual)


def assert_diagnose_no_holdout_leakage(frame: pd.DataFrame | None = None) -> None:
    """Guard used in tests: CV and learning-curve slices exclude holdout months."""
    featured = _featured_pre_holdout(frame)
    for train_end_year, val_year in CV_FOLD_SPECS:
        train_frame, val_frame = _slice_train_val(featured, train_end_year, val_year)
        _assert_pre_holdout(train_frame, "CV train")
        _assert_pre_holdout(val_frame, "CV val")
    for train_end_year, val_year in LEARNING_CURVE_SPECS:
        train_frame, val_frame = _slice_train_val(featured, train_end_year, val_year)
        _assert_pre_holdout(train_frame, "learning curve train")
        if val_frame is not None:
            _assert_pre_holdout(val_frame, "learning curve val")


# --- Phase 2 visuals (V9–V10) — context-20 E11; does not modify V1–V8 in visualize.py ---

EVAL_CAPTIONS = {
    "v9": "Holdout 2024–2025 excluded from curve fitting; see context-19 V4 for final holdout.",
    "v10": "Folds use pre-2024 data only; 2024–2025 is the single final holdout.",
}


def _holdout_mape_pct(frame: pd.DataFrame | None = None) -> float:
    """Context-19 holdout MAPE for reference lines only (E1 read-only)."""
    from data.forecasting.evaluate import evaluate_forecast
    from data.forecasting.train import train_sales_model

    artifacts, matrices = train_sales_model(frame)
    y_pred = artifacts.model.predict(matrices.x_test)
    return evaluate_forecast(matrices.y_test, y_pred).mape_pct


def plot_v9_learning_curve(
    points: list[LearningCurvePoint] | None = None,
    *,
    holdout_mape_pct: float | None = None,
    output_path: Path | None = None,
    frame: pd.DataFrame | None = None,
) -> plt.Figure:
    """V9 — training vs validation MAPE by featured training size (train era only)."""

    curve = points if points is not None else learning_curve_points(frame)
    holdout_ref = _holdout_mape_pct(frame) if holdout_mape_pct is None else holdout_mape_pct

    train_x = [p.train_rows for p in curve]
    train_y = [p.train_mape_pct for p in curve]
    val_x = [p.train_rows for p in curve if p.val_mape_pct is not None]
    val_y = [p.val_mape_pct for p in curve if p.val_mape_pct is not None]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(train_x, train_y, marker="o", color="#2563eb", label="Training MAPE")
    if val_x:
        ax.plot(val_x, val_y, marker="s", color="#dc2626", label="Validation MAPE (temporal)")
    ax.axhline(
        holdout_ref,
        color="#6b7280",
        linestyle="--",
        linewidth=1,
        label=f"Context-19 holdout MAPE ({holdout_ref:.1f}%)",
    )
    ax.set_title("Learning Curve — Random Forest (Train Era Only)")
    ax.set_xlabel("Featured training months (count)")
    ax.set_ylabel("MAPE (%)")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    if output_path:
        _save_eval_figure(fig, output_path)
    return fig


def plot_v10_cv_fold_metrics(
    results: list[CvFoldResult] | None = None,
    summary: CvSummary | None = None,
    *,
    holdout_mape_pct: float | None = None,
    output_path: Path | None = None,
    frame: pd.DataFrame | None = None,
) -> plt.Figure:
    """V10 — validation MAPE per walk-forward fold with mean ± std annotation."""

    folds = results if results is not None else run_walk_forward_cv(frame)
    agg = summary if summary is not None else summarize_cv_results(folds)
    holdout_ref = _holdout_mape_pct(frame) if holdout_mape_pct is None else holdout_mape_pct

    labels = [r.val_start[:4] for r in folds]
    mapes = [r.mape_pct for r in folds]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(labels, mapes, color="#2563eb", alpha=0.85, label="Validation MAPE")
    ax.axhline(
        holdout_ref,
        color="#6b7280",
        linestyle="--",
        linewidth=1,
        label=f"Holdout MAPE ({holdout_ref:.1f}%)",
    )
    ax.axhline(
        agg.val_mape_pct_mean,
        color="#059669",
        linestyle=":",
        linewidth=1.5,
        label=f"CV mean MAPE ({agg.val_mape_pct_mean:.2f}%)",
    )
    ax.set_title("Walk-Forward CV — Validation MAPE by Fold")
    ax.set_xlabel("Validation year")
    ax.set_ylabel("Validation MAPE (%)")
    ax.legend(loc="best")
    ax.grid(True, axis="y", alpha=0.3)
    ax.text(
        0.02,
        0.98,
        f"Mean ± std MAPE: {agg.val_mape_pct_mean:.2f}% ± {agg.val_mape_pct_std:.2f}%\n"
        f"Mean ± std RMSE: ${agg.val_rmse_mean:,.0f} ± ${agg.val_rmse_std:,.0f}",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
    )

    if output_path:
        _save_eval_figure(fig, output_path)
    return fig


def _save_eval_figure(fig: plt.Figure, path: Path) -> Path:
    """Match context-19 labeling standards (dpi=150, bbox_inches=tight)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def save_evaluation_visuals(
    *,
    output_dir: Path | None = None,
    frame: pd.DataFrame | None = None,
) -> dict[str, Path]:
    """
    Write V9 and V10 PNGs under ``docs/forecasting/outputs/`` (context-20 D14).

    Does not overwrite V1–V8; separate filenames from ``save_all_visuals()``.
    """
    from data.forecasting.visualize import DEFAULT_OUTPUT_DIR, ensure_output_dir

    out = ensure_output_dir(output_dir or DEFAULT_OUTPUT_DIR)
    holdout_mape = _holdout_mape_pct(frame)
    curve = learning_curve_points(frame)
    cv_results = run_walk_forward_cv(frame)
    cv_summary = summarize_cv_results(cv_results)

    v9_path = out / "v9_learning_curve.png"
    v10_path = out / "v10_cv_fold_metrics.png"

    plot_v9_learning_curve(curve, holdout_mape_pct=holdout_mape, output_path=v9_path, frame=frame)
    plot_v10_cv_fold_metrics(
        cv_results,
        cv_summary,
        holdout_mape_pct=holdout_mape,
        output_path=v10_path,
        frame=frame,
    )

    return {"v9": v9_path, "v10": v10_path}
