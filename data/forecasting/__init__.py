"""Sales forecasting utilities (context-19)."""

from data.forecasting.evaluate import ForecastMetrics, evaluate_forecast, mean_absolute_percentage_error
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
from data.forecasting.diagnose import (
    CvFoldResult,
    CvSummary,
    LearningCurvePoint,
    MIN_CV_FOLDS,
    SliceMetrics,
    assert_cv_folds_chronological,
    learning_curve_points,
    psi_structural_train_vs_holdout_actual,
    run_walk_forward_cv,
    summarize_cv_results,
    save_evaluation_visuals,
    walk_forward_cv_folds,
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
    "assert_cv_folds_chronological",
    "CvFoldResult",
    "CvSummary",
    "evaluate_forecast",
    "learning_curve_points",
    "LearningCurvePoint",
    "MIN_CV_FOLDS",
    "psi_structural_train_vs_holdout_actual",
    "run_walk_forward_cv",
    "SliceMetrics",
    "summarize_cv_results",
    "save_evaluation_visuals",
    "walk_forward_cv_folds",
    "feature_matrix",
    "fit_random_forest",
    "load_sales",
    "mean_absolute_percentage_error",
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
