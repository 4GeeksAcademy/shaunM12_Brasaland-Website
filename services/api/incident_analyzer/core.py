from __future__ import annotations

import io
import re
from collections import Counter
from typing import Any

import pandas as pd

VALID_CATEGORIES = (
    "CUSTOMER_COMPLAINT",
    "EQUIPMENT",
    "SUPPLY",
    "FOOD_QUALITY",
    "STAFF",
)

VALID_STATUSES = ("OPEN", "CLOSED", "DISCARDED")

APPROVED_LOCATION_IDS = frozenset(
    {
        "COL-01",
        "COL-02",
        "COL-03",
        "COL-04",
        "COL-05",
        "COL-06",
        "COL-07",
        "COL-08",
        "COL-09",
        "COL-10",
        "FLA-01",
        "FLA-02",
        "FLA-03",
        "FLA-04",
    }
)

REQUIRED_FIELDS = (
    "incidentId",
    "reportedAt",
    "locationId",
    "category",
    "status",
    "reportedBy",
    "description",
)

COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "incidentId": ("incidentid", "incident_id"),
    "reportedAt": ("reportedat", "reported_at", "date"),
    "locationId": ("locationid", "location_id"),
    "category": ("category",),
    "status": ("status",),
    "reportedBy": ("reportedby", "reported_by", "reporter_id"),
    "description": ("description",),
    "customerId": ("customerid", "customer_id"),
    "satisfactionIndex": (
        "satisfactionindex",
        "satisfaction_index",
        "satisfaction_score",
    ),
}

STATUS_ALIASES: dict[str, str] = {
    "open": "OPEN",
    "abierto": "OPEN",
    "closed": "CLOSED",
    "cerrado": "CLOSED",
    "close": "CLOSED",
    "discarded": "DISCARDED",
    "descartado": "DISCARDED",
    "discard": "DISCARDED",
}

CATEGORY_ALIASES: dict[str, str] = {
    "queja_cliente": "CUSTOMER_COMPLAINT",
    "customer_complaint": "CUSTOMER_COMPLAINT",
    "equipamiento": "EQUIPMENT",
    "equipment": "EQUIPMENT",
    "abastecimiento": "SUPPLY",
    "supply": "SUPPLY",
    "calidad_alimento": "FOOD_QUALITY",
    "food_quality": "FOOD_QUALITY",
    "personal": "STAFF",
    "staff": "STAFF",
}

INVALID_RULE_KEYS = (
    "missing_location_id",
    "invalid_or_missing_category",
    "empty_description",
    "missing_reporter_id",
    "closed_case_no_score",
    "out_of_range_satisfaction_score",
)

INVALID_RULE_LABELS: dict[str, str] = {
    "missing_location_id": "Missing location_id",
    "invalid_or_missing_category": "Invalid or missing category",
    "empty_description": "Empty description",
    "missing_reporter_id": "Missing reporter_id",
    "closed_case_no_score": "Closed case, no score",
    "out_of_range_satisfaction_score": "Out-of-range satisfaction_score",
}

SATISFACTION_LABELS: dict[int, str] = {
    1: "Very dissatisfied",
    2: "Dissatisfied",
    3: "Neutral",
    4: "Satisfied",
    5: "Very satisfied",
}

MAX_INVALID_ROW_SAMPLES = 10


def _normalize_key(name: str) -> str:
    return re.sub(r"[\s_]+", "", name.strip().lower())


def _resolve_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    lookup = {_normalize_key(col): col for col in df.columns}
    rename_map: dict[str, str] = {}
    missing: list[str] = []

    for canonical, aliases in COLUMN_ALIASES.items():
        source = None
        for alias in aliases:
            key = _normalize_key(alias)
            if key in lookup:
                source = lookup[key]
                break
        if source is not None:
            if source != canonical:
                rename_map[source] = canonical
        elif canonical in REQUIRED_FIELDS:
            missing.append(canonical)

    return df.rename(columns=rename_map), missing


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def normalize_category(raw: Any) -> str | None:
    if _is_missing(raw):
        return None
    text = str(raw).strip()
    if text in VALID_CATEGORIES:
        return text
    mapped = CATEGORY_ALIASES.get(text.lower().replace(" ", "_"))
    if mapped:
        return mapped
    return CATEGORY_ALIASES.get(text.lower())


def normalize_status(raw: Any) -> str | None:
    if _is_missing(raw):
        return None
    text = str(raw).strip()
    if not text:
        return None
    if text in VALID_STATUSES:
        return text
    mapped = STATUS_ALIASES.get(text.lower().replace(" ", "_"))
    if mapped:
        return mapped
    return STATUS_ALIASES.get(text.lower())


def _parse_satisfaction_score(value: Any) -> tuple[bool, int | None]:
    if _is_missing(value):
        return True, None
    try:
        if isinstance(value, float) and value.is_integer():
            score = int(value)
        elif isinstance(value, int):
            score = value
        else:
            text = str(value).strip()
            if not re.fullmatch(r"\d+", text):
                return False, None
            score = int(text)
        if score < 1 or score > 5:
            return False, None
        return True, score
    except (TypeError, ValueError):
        return False, None


def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    df, _ = _resolve_columns(df)

    if "category" in df.columns:
        for idx, row in df.iterrows():
            category = normalize_category(row.get("category"))
            if category:
                df.at[idx, "category"] = category

    if "status" in df.columns:
        for idx, row in df.iterrows():
            status = normalize_status(row.get("status"))
            if status:
                df.at[idx, "status"] = status

    return df


def validate_record(row: pd.Series) -> tuple[list[str], dict[str, Any] | None]:
    errors: list[str] = []
    normalized: dict[str, Any] = {}

    location_id = row.get("locationId")
    if _is_missing(location_id):
        errors.append("missing_location_id")
    else:
        location_str = str(location_id).strip()
        if location_str not in APPROVED_LOCATION_IDS:
            errors.append("missing_location_id")
        else:
            normalized["locationId"] = location_str

    category = normalize_category(row.get("category"))
    if category is None:
        errors.append("invalid_or_missing_category")
    else:
        normalized["category"] = category

    description = row.get("description")
    if _is_missing(description) or len(str(description).strip()) < 5:
        errors.append("empty_description")
    else:
        normalized["description"] = str(description).strip()

    reported_by = row.get("reportedBy")
    if _is_missing(reported_by):
        errors.append("missing_reporter_id")
    else:
        normalized["reportedBy"] = str(reported_by).strip()

    status = normalize_status(row.get("status"))
    if status is None:
        if not _is_missing(row.get("status")):
            errors.append("invalid_status")
    else:
        normalized["status"] = status

    score_ok, score = _parse_satisfaction_score(row.get("satisfactionIndex"))
    if not score_ok:
        errors.append("out_of_range_satisfaction_score")
    elif score is not None:
        normalized["satisfactionIndex"] = score

    if status == "CLOSED" and score is None:
        errors.append("closed_case_no_score")

    if not _is_missing(row.get("incidentId")):
        normalized["incidentId"] = str(row.get("incidentId")).strip()
    if not _is_missing(row.get("reportedAt")):
        normalized["reportedAt"] = str(row.get("reportedAt")).strip()

    if errors:
        return errors, None
    return [], normalized


def load_csv_bytes(payload: bytes) -> pd.DataFrame:
    if not payload.strip():
        raise ValueError("CSV file is empty")
    try:
        df = pd.read_csv(io.BytesIO(payload))
    except Exception as exc:
        raise ValueError(f"Incorrect CSV format: {exc}") from exc
    if df.empty:
        raise ValueError("CSV file is empty")
    df.columns = [str(col).strip() for col in df.columns]
    return df


def _empty_result(source_path: str) -> dict[str, Any]:
    return {
        "sourcePath": source_path,
        "schemaError": None,
        "totalProcessed": 0,
        "validCount": 0,
        "invalidCount": 0,
        "invalidReasons": {},
        "invalidRowSamples": [],
        "byCategory": {cat: 0 for cat in VALID_CATEGORIES},
        "byStatus": {status: 0 for status in VALID_STATUSES},
        "avgSatisfactionClosed": None,
        "satisfactionClosedCount": 0,
        "closedCaseCount": 0,
        "satisfactionScoreBreakdown": {str(score): 0 for score in range(1, 6)},
    }


def analyze_dataframe(df: pd.DataFrame, source_path: str = "uploaded.csv") -> dict[str, Any]:
    df = preprocess_dataframe(df)
    df, missing_columns = _resolve_columns(df)

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
            "byCategory": {cat: 0 for cat in VALID_CATEGORIES},
            "byStatus": {status: 0 for status in VALID_STATUSES},
            "avgSatisfactionClosed": None,
            "satisfactionClosedCount": 0,
            "closedCaseCount": 0,
            "satisfactionScoreBreakdown": {str(score): 0 for score in range(1, 6)},
        }

    invalid_reasons: Counter[str] = Counter()
    invalid_row_samples: list[int] = []
    valid_records: list[dict[str, Any]] = []

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


def analyze_from_bytes(payload: bytes, source_path: str = "uploaded.csv") -> dict[str, Any]:
    df = load_csv_bytes(payload)
    return analyze_dataframe(df, source_path)


def _percentage(count: int, total: int) -> str | None:
    if total <= 0:
        return None
    return f"{(count / total) * 100:.1f}%"


def build_results_rows(result: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = [
        {"metric": "total_processed", "value": str(result["totalProcessed"])},
        {"metric": "valid_count", "value": str(result["validCount"])},
        {"metric": "invalid_count", "value": str(result["invalidCount"])},
    ]

    if result.get("schemaError"):
        rows.append({"metric": "schema_error", "value": result["schemaError"]})

    for reason, count in sorted(result["invalidReasons"].items()):
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", reason).strip("_").lower()
        rows.append({"metric": f"invalid_{slug}", "value": str(count)})

    valid_total = result["validCount"]
    for category, count in result["byCategory"].items():
        row: dict[str, str] = {
            "metric": f"category_{category}",
            "value": str(count),
        }
        pct = _percentage(count, valid_total)
        if pct:
            row["percentage"] = pct
        rows.append(row)

    for status, count in result["byStatus"].items():
        row = {"metric": f"status_{status}", "value": str(count)}
        pct = _percentage(count, valid_total)
        if pct:
            row["percentage"] = pct
        rows.append(row)

    if result["avgSatisfactionClosed"] is not None:
        rows.append(
            {
                "metric": "avg_satisfaction_closed",
                "value": f"{result['avgSatisfactionClosed']:.2f}",
            }
        )
    else:
        rows.append({"metric": "avg_satisfaction_closed", "value": "N/A"})

    rows.append(
        {
            "metric": "satisfaction_closed_count",
            "value": str(result["satisfactionClosedCount"]),
        }
    )

    for score, count in result["satisfactionScoreBreakdown"].items():
        rows.append({"metric": f"satisfaction_score_{score}", "value": str(count)})

    return rows


def format_summary(result: dict[str, Any]) -> str:
    separator_major = "=" * 60
    lines = [
        separator_major,
        "  BRASALAND — INCIDENT REPORT ANALYSIS",
        f"  Source file: {result['sourcePath']}",
        separator_major,
        "",
        f"TOTAL RECORDS IN FILE .......... {result['totalProcessed']}",
        f"  ├─ Valid records ................ {result['validCount']}",
        f"  └─ Invalid / incomplete .......... {result['invalidCount']}",
        "",
        "INVALID RECORDS BREAKDOWN",
    ]

    if result.get("schemaError"):
        lines.append(f"  ├─ Schema error .................. {result['schemaError']}")
        lines.append(separator_major)
        return "\n".join(lines)

    breakdown_order = [
        "Missing location_id",
        "Invalid or missing category",
        "Empty description",
        "Missing reporter_id",
        "Closed case, no score",
        "Out-of-range satisfaction_score",
    ]
    reasons = result["invalidReasons"]
    for label in breakdown_order:
        count = reasons.get(label, 0)
        if count > 0:
            dots = "." * max(1, 28 - len(label))
            lines.append(f"  ├─ {label} {dots} {count}")

    if not reasons:
        lines.append("  └─ (none)")

    valid_total = result["validCount"]
    lines.extend(["", "BREAKDOWN BY CATEGORY (valid records)"])
    for category, count in result["byCategory"].items():
        pct = _percentage(count, valid_total) or "0.0%"
        dots = "." * max(1, 28 - len(category))
        lines.append(f"  ├─ {category} {dots} {count:>3}  ({pct})")

    lines.extend(["", "BREAKDOWN BY STATUS (valid records)"])
    for status, count in result["byStatus"].items():
        pct = _percentage(count, valid_total) or "0.0%"
        dots = "." * max(1, 28 - len(status))
        lines.append(f"  ├─ {status} {dots} {count:>3}  ({pct})")

    lines.extend(["", "SATISFACTION INDEX (closed cases)"])
    closed = result["closedCaseCount"]
    scored = result["satisfactionClosedCount"]
    lines.append(f"  Scored cases: {scored} of {closed}")
    if result["avgSatisfactionClosed"] is not None:
        lines.append(f"  Average score: {result['avgSatisfactionClosed']:.2f} / 5.00")
    else:
        lines.append("  Average score: N/A")

    for score in range(1, 6):
        count = result["satisfactionScoreBreakdown"][str(score)]
        label = SATISFACTION_LABELS[score]
        dots = "." * max(1, 28 - len(f"Score {score} ({label})"))
        lines.append(f"  ├─ Score {score} ({label}) {dots} {count}")

    lines.extend(["", separator_major])
    return "\n".join(lines)
