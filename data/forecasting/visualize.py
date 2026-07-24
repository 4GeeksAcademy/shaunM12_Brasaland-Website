"""Visualization helpers for sales forecasting (context-19 V1–V8)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter
from sklearn.ensemble import RandomForestRegressor

from data.forecasting.evaluate import DEFAULT_BIN_COUNT, ForecastMetrics, evaluate_forecast
from data.forecasting.load import load_sales
from data.forecasting.split import TEST_START, temporal_train_test_split
from data.forecasting.train import (
    ScaledMatrices,
    TrainArtifacts,
    predict_with_uncertainty,
    train_sales_model,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = _REPO_ROOT / "docs" / "forecasting" / "outputs"

CAPTIONS = {
    "v1": "Shows whether monthly forecasts match actual sales and how wide the model's uncertainty is.",
    "v2": "The model was fit only on the training period; holdout months were unseen during training.",
    "v3": "Positive bars = underprediction; negative = overprediction.",
    "v4": "Low MSE alone does not guarantee a good model; PSI, Gini, and K2 catch drift, ranking, and range-level bias.",
    "v5": "Supports PSI and K2: mismatched bar heights indicate systematic bias in certain revenue ranges.",
    "v6": "Shows which inputs (e.g. last month's revenue, seasonality) matter most.",
    "v7": "Validates whether the model captures recurring monthly effects (e.g. year-end peaks).",
    "v8": "A clear trend in residuals suggests the model under- or over-predicts at certain revenue levels.",
}


@dataclass(frozen=True)
class ForecastVisualContext:
    artifacts: TrainArtifacts
    matrices: ScaledMatrices
    y_pred: np.ndarray
    y_low: np.ndarray
    y_high: np.ndarray
    metrics: ForecastMetrics
    raw_frame: pd.DataFrame


def usd_formatter(value: float, _pos: int) -> str:
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}"


def ensure_output_dir(output_dir: Path | None = None) -> Path:
    target = output_dir or DEFAULT_OUTPUT_DIR
    target.mkdir(parents=True, exist_ok=True)
    return target


def build_visual_context(frame: pd.DataFrame | None = None) -> ForecastVisualContext:
    raw = load_sales() if frame is None else frame
    artifacts, matrices = train_sales_model(raw)
    y_pred, y_low, y_high = predict_with_uncertainty(artifacts.model, matrices.x_test)
    metrics = evaluate_forecast(matrices.y_test, y_pred)
    return ForecastVisualContext(
        artifacts=artifacts,
        matrices=matrices,
        y_pred=y_pred,
        y_low=y_low,
        y_high=y_high,
        metrics=metrics,
        raw_frame=raw,
    )


def _apply_usd_axis(ax: plt.Axes, axis: str = "y") -> None:
    formatter = FuncFormatter(usd_formatter)
    if axis == "y":
        ax.yaxis.set_major_formatter(formatter)
    else:
        ax.xaxis.set_major_formatter(formatter)


def _save_figure(fig: plt.Figure, path: Path, *, close: bool = True) -> Path:
    fig.savefig(path, dpi=150, bbox_inches="tight")
    if close:
        plt.close(fig)
    return path


def plot_v2_train_test_timeline(
    raw_frame: pd.DataFrame,
    *,
    output_path: Path | None = None,
) -> plt.Figure:
    train, test = temporal_train_test_split(raw_frame.sort_values("month"))
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(
        pd.to_datetime(train["month"]),
        train["revenue_usd"],
        label="Training period (2016–2023)",
        color="#2563eb",
        linewidth=2,
    )
    ax.plot(
        pd.to_datetime(test["month"]),
        test["revenue_usd"],
        label="Holdout period (2024–2025)",
        color="#dc2626",
        linewidth=2,
    )
    ax.axvline(TEST_START, color="#6b7280", linestyle="--", linewidth=1)
    ax.set_title("Brasaland Revenue History — Training vs Holdout Period")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue (USD)")
    _apply_usd_axis(ax, "y")
    ax.legend()
    fig.autofmt_xdate()
    if output_path:
        _save_figure(fig, output_path, close=False)
    return fig


def plot_v1_forecast_with_band(
    ctx: ForecastVisualContext,
    *,
    output_path: Path | None = None,
) -> plt.Figure:
    months = ctx.matrices.test_months
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.fill_between(
        months,
        ctx.y_low,
        ctx.y_high,
        alpha=0.25,
        color="#2563eb",
        label="Prediction range (10th–90th percentile)",
    )
    ax.plot(months, ctx.matrices.y_test, label="Actual revenue", color="#111827", linewidth=2)
    ax.plot(
        months,
        ctx.y_pred,
        label="Mean prediction",
        color="#2563eb",
        linestyle="--",
        linewidth=2,
    )
    ax.set_title("Brasaland Monthly Revenue — Holdout Forecast (2024–2025)")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue (USD)")
    _apply_usd_axis(ax, "y")
    ax.legend()
    fig.autofmt_xdate()
    if output_path:
        _save_figure(fig, output_path, close=False)
    return fig


def plot_v3_monthly_errors(
    ctx: ForecastVisualContext,
    *,
    output_path: Path | None = None,
) -> plt.Figure:
    errors = ctx.matrices.y_test - ctx.y_pred
    months = ctx.matrices.test_months
    colors = ["#dc2626" if value > 0 else "#059669" for value in errors]
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(months, errors, color=colors, width=20)
    ax.axhline(0, color="#6b7280", linewidth=1)
    ax.set_title("Monthly Forecast Error on Holdout Data (2024–2025)")
    ax.set_xlabel("Month")
    ax.set_ylabel("Error (USD): Actual − Predicted")
    _apply_usd_axis(ax, "y")
    fig.autofmt_xdate()
    if output_path:
        _save_figure(fig, output_path, close=False)
    return fig


def metrics_table_markdown(metrics: ForecastMetrics) -> str:
    rmse = metrics.mse**0.5
    rows = [
        ("MSE", f"{metrics.mse:,.2f}", "Average squared error in USD²; lower is better."),
        (
            "Avg. % error (MAPE)",
            f"{metrics.mape_pct:.2f}%",
            "Average absolute forecast error as a share of actual revenue; easier for stakeholders than USD².",
        ),
        (
            "RMSE (from MSE)",
            f"${rmse:,.0f}",
            "Typical monthly error scale in USD (√MSE); complements MAPE.",
        ),
        ("PSI", f"{metrics.psi:.4f}", "Distribution drift between actual and predicted revenue."),
        ("Gini", f"{metrics.gini:.4f}", "Ranking quality of predictions vs actuals (1.0 = perfect)."),
        ("K2", f"{metrics.k2:,.2f}", "Chi-square on binned distributions; closer to 0 is better."),
    ]
    lines = [
        "### Model Evaluation on Holdout Period (2024–2025)",
        "",
        "| Metric | Value | What it means |",
        "| ------ | ----- | ------------- |",
    ]
    for name, value, meaning in rows:
        lines.append(f"| {name} | {value} | {meaning} |")
    lines.append("")
    lines.append(CAPTIONS["v4"])
    return "\n".join(lines)


def write_metrics_summary(metrics: ForecastMetrics, output_path: Path) -> Path:
    output_path.write_text(metrics_table_markdown(metrics), encoding="utf-8")
    return output_path


def plot_v5_binned_distribution(
    ctx: ForecastVisualContext,
    *,
    n_bins: int = DEFAULT_BIN_COUNT,
    output_path: Path | None = None,
) -> plt.Figure:
    y_true = ctx.matrices.y_test
    y_pred = ctx.y_pred
    breakpoints = np.unique(np.quantile(y_true, np.linspace(0.0, 1.0, n_bins + 1)))
    actual_counts, _ = np.histogram(y_true, bins=breakpoints)
    pred_counts, _ = np.histogram(y_pred, bins=breakpoints)
    actual_pct = actual_counts / len(y_true) * 100
    pred_pct = pred_counts / len(y_pred) * 100
    labels = [
        f"${breakpoints[i] / 1000:.0f}K–${breakpoints[i + 1] / 1000:.0f}K"
        for i in range(len(breakpoints) - 1)
    ]
    x = np.arange(len(labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x - width / 2, actual_pct, width, label="Actual", color="#111827")
    ax.bar(x + width / 2, pred_pct, width, label="Predicted", color="#2563eb")
    ax.set_title("Distribution of Actual vs Predicted Revenue (Holdout)")
    ax.set_xlabel("Revenue bin (USD)")
    ax.set_ylabel("Share of months (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.legend()
    if output_path:
        _save_figure(fig, output_path, close=False)
    return fig


def plot_v6_feature_importance(
    model: RandomForestRegressor,
    feature_names: tuple[str, ...] | list[str],
    *,
    output_path: Path | None = None,
) -> plt.Figure:
    importances = model.feature_importances_
    order = np.argsort(importances)
    names = [feature_names[i] for i in order]
    values = importances[order]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(names, values, color="#2563eb")
    ax.set_title("What Drives Revenue Predictions — Feature Importance")
    ax.set_xlabel("Importance (relative)")
    ax.set_ylabel("Feature")
    if output_path:
        _save_figure(fig, output_path, close=False)
    return fig


def plot_v7_seasonality_by_month(
    ctx: ForecastVisualContext,
    *,
    output_path: Path | None = None,
) -> plt.Figure:
    frame = pd.DataFrame(
        {
            "month": ctx.matrices.test_months,
            "actual": ctx.matrices.y_test,
            "predicted": ctx.y_pred,
        }
    )
    frame["calendar_month"] = frame["month"].dt.month
    grouped = frame.groupby("calendar_month")[["actual", "predicted"]].mean()
    x = grouped.index.to_numpy()
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width / 2, grouped["actual"], width, label="Actual", color="#111827")
    ax.bar(x + width / 2, grouped["predicted"], width, label="Predicted", color="#2563eb")
    ax.set_title("Seasonal Pattern — Actual vs Predicted Revenue by Month (Holdout)")
    ax.set_xlabel("Calendar month")
    ax.set_ylabel("Revenue (USD)")
    ax.set_xticks(x)
    _apply_usd_axis(ax, "y")
    ax.legend()
    if output_path:
        _save_figure(fig, output_path, close=False)
    return fig


def plot_v8_residuals(
    ctx: ForecastVisualContext,
    *,
    output_path: Path | None = None,
) -> plt.Figure:
    residuals = ctx.matrices.y_test - ctx.y_pred
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(ctx.y_pred, residuals, color="#2563eb", alpha=0.85)
    ax.axhline(0, color="#6b7280", linestyle="--", linewidth=1)
    ax.set_title("Residual Analysis — Holdout Predictions")
    ax.set_xlabel("Predicted revenue (USD)")
    ax.set_ylabel("Residual (USD): Actual − Predicted")
    _apply_usd_axis(ax, "x")
    _apply_usd_axis(ax, "y")
    if output_path:
        _save_figure(fig, output_path, close=False)
    return fig


def save_all_visuals(
    ctx: ForecastVisualContext | None = None,
    *,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """Render V1–V8 in locked notebook order and save PNGs."""
    context = ctx or build_visual_context()
    out = ensure_output_dir(output_dir)
    saved: dict[str, Path] = {}

    plot_v2_train_test_timeline(context.raw_frame, output_path=out / "v2_train_test_timeline.png")
    plt.close()
    saved["v2"] = out / "v2_train_test_timeline.png"

    plot_v1_forecast_with_band(context, output_path=out / "v1_forecast_with_band.png")
    saved["v1"] = out / "v1_forecast_with_band.png"

    plot_v3_monthly_errors(context, output_path=out / "v3_monthly_errors.png")
    saved["v3"] = out / "v3_monthly_errors.png"

    plot_v5_binned_distribution(context, output_path=out / "v5_binned_distribution.png")
    saved["v5"] = out / "v5_binned_distribution.png"

    saved["v4"] = write_metrics_summary(context.metrics, out / "v4_metrics_summary.md")

    plot_v6_feature_importance(
        context.artifacts.model,
        context.artifacts.feature_names,
        output_path=out / "v6_feature_importance.png",
    )
    saved["v6"] = out / "v6_feature_importance.png"

    plot_v7_seasonality_by_month(context, output_path=out / "v7_seasonality_by_month.png")
    saved["v7"] = out / "v7_seasonality_by_month.png"

    plot_v8_residuals(context, output_path=out / "v8_residuals.png")
    saved["v8"] = out / "v8_residuals.png"
    plt.close("all")
    return saved
