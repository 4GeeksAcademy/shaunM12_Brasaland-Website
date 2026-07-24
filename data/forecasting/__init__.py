"""Sales forecasting utilities (context-19)."""

from data.forecasting.evaluate import ForecastMetrics, evaluate_forecast
from data.forecasting.features import FEATURE_COLUMNS, TARGET_COLUMN, build_feature_frame, feature_matrix
from data.forecasting.load import (
    DEFAULT_SALES_CSV,
    EXPECTED_COLUMNS,
    EXPECTED_ROW_COUNT,
    load_sales,
)
from data.forecasting.split import (
    TEST_START,
    TRAIN_END,
    temporal_train_test_split,
)
from data.forecasting.train import (
    RANDOM_STATE,
    ScaledMatrices,
    TrainArtifacts,
    fit_random_forest,
    predict_mean,
    predict_with_uncertainty,
    prepare_scaled_matrices,
    train_sales_model,
)
from data.forecasting.visualize import (
    DEFAULT_OUTPUT_DIR,
    build_visual_context,
    metrics_table_markdown,
    save_all_visuals,
    write_metrics_summary,
)

__all__ = [
    "DEFAULT_SALES_CSV",
    "EXPECTED_COLUMNS",
    "EXPECTED_ROW_COUNT",
    "FEATURE_COLUMNS",
    "ForecastMetrics",
    "RANDOM_STATE",
    "ScaledMatrices",
    "TARGET_COLUMN",
    "TEST_START",
    "TRAIN_END",
    "TrainArtifacts",
    "build_feature_frame",
    "evaluate_forecast",
    "feature_matrix",
    "fit_random_forest",
    "load_sales",
    "predict_mean",
    "predict_with_uncertainty",
    "prepare_scaled_matrices",
    "temporal_train_test_split",
    "train_sales_model",
    "DEFAULT_OUTPUT_DIR",
    "build_visual_context",
    "metrics_table_markdown",
    "save_all_visuals",
    "write_metrics_summary",
]
