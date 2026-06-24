"""CSV loading and incident dataset analysis."""

from __future__ import annotations

import io
from collections import Counter
from typing import Any

import pandas as pd

from errors import get_logger
from .constants import INVALID_RULE_LABELS, VALID_CATEGORIES, VALID_STATUSES
from .schemas import AnalysisResult, NormalizedIncidentRecord
from .validators import preprocess_dataframe, resolve_columns, validate_record

logger = get_logger("incident_analyzer")


def load_csv_bytes(payload: bytes) -> pd.DataFrame:
    if not payload.strip():
        raise ValueError("CSV file is empty")
    try:
        df = pd.read_csv(io.BytesIO(payload))
    except Exception as exc:
        # Keep the raw parser detail in the server log only; the message that
        # propagates to the API/CLI is generic (no library internals leaked).
        logger.error("Failed to parse uploaded CSV", exc_info=exc)
        raise ValueError("Incorrect CSV format") from exc
    if df.empty:
        raise ValueError("CSV file is empty")
    df.columns = [str(col).strip() for col in df.columns]
    return df


def _empty_breakdowns() -> dict[str, Any]:
    return {
        "byCategory": {cat: 0 for cat in VALID_CATEGORIES},
        "byStatus": {status: 0 for status in VALID_STATUSES},
        "avgSatisfactionClosed": None,
        "satisfactionClosedCount": 0,
        "closedCaseCount": 0,
        "satisfactionScoreBreakdown": {str(score): 0 for score in range(1, 6)},
    }


def analyze_dataframe(df: pd.DataFrame, source_path: str = "uploaded.csv") -> AnalysisResult:
    df = preprocess_dataframe(df)
    df, missing_columns = resolve_columns(df)

    if missing_columns:
        return {
            "sourcePath": source_path,
            "schemaError": "Missing required columns: " + ", ".join(sorted(missing_columns)),
            "totalProcessed": len(df),
            "validCount": 0,
            "invalidCount": len(df),
            "invalidReasons": {
                f"Missing column {col}": len(df) for col in missing_columns
            },
            "invalidRowSamples": list(range(2, len(df) + 2)),
            **_empty_breakdowns(),
        }

    invalid_reasons: Counter[str] = Counter()
    invalid_row_samples: list[int] = []
    valid_records: list[NormalizedIncidentRecord] = []

    for idx, row in df.iterrows():
        row_number = int(idx) + 2
        errors, normalized = validate_record(row)
        if errors:
            invalid_row_samples.append(row_number)
            for error in errors:
                label = INVALID_RULE_LABELS.get(error, error)
                invalid_reasons[label] += 1
        elif normalized is not None:
            valid_records.append(normalized)

    by_category = {cat: 0 for cat in VALID_CATEGORIES}
    by_status = {status: 0 for status in VALID_STATUSES}
    satisfaction_scores: list[int] = []
    satisfaction_breakdown = {str(score): 0 for score in range(1, 6)}
    closed_case_count = 0

    for record in valid_records:
        by_category[record["category"]] += 1
        by_status[record["status"]] += 1
        if record["status"] == "CLOSED":
            closed_case_count += 1
            score = record.get("satisfactionIndex")
            if score is not None:
                satisfaction_scores.append(int(score))
                satisfaction_breakdown[str(int(score))] += 1

    avg_satisfaction = (
        sum(satisfaction_scores) / len(satisfaction_scores)
        if satisfaction_scores
        else None
    )

    return {
        "sourcePath": source_path,
        "schemaError": None,
        "totalProcessed": len(df),
        "validCount": len(valid_records),
        "invalidCount": len(df) - len(valid_records),
        "invalidReasons": dict(invalid_reasons),
        "invalidRowSamples": invalid_row_samples,
        "byCategory": by_category,
        "byStatus": by_status,
        "avgSatisfactionClosed": avg_satisfaction,
        "satisfactionClosedCount": len(satisfaction_scores),
        "closedCaseCount": closed_case_count,
        "satisfactionScoreBreakdown": satisfaction_breakdown,
    }


def analyze_from_bytes(payload: bytes, source_path: str = "uploaded.csv") -> AnalysisResult:
    df = load_csv_bytes(payload)
    return analyze_dataframe(df, source_path)
