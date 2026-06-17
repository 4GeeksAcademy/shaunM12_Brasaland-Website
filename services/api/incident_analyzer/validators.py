"""Normalization and row-level validation for incident CSV records."""

from __future__ import annotations

import re
from typing import Any, cast

import pandas as pd

from .constants import (
    APPROVED_LOCATION_IDS,
    CATEGORY_ALIASES,
    COLUMN_ALIASES,
    REQUIRED_FIELDS,
    STATUS_ALIASES,
    VALID_CATEGORIES,
    VALID_STATUSES,
)
from .schemas import IncidentCategory, IncidentStatus, NormalizedIncidentRecord


def normalize_key(name: str) -> str:
    return re.sub(r"[\s_]+", "", name.strip().lower())


def resolve_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    lookup = {normalize_key(col): col for col in df.columns}
    rename_map: dict[str, str] = {}
    missing: list[str] = []

    for canonical, aliases in COLUMN_ALIASES.items():
        source = None
        for alias in aliases:
            key = normalize_key(alias)
            if key in lookup:
                source = lookup[key]
                break
        if source is not None:
            if source != canonical:
                rename_map[source] = canonical
        elif canonical in REQUIRED_FIELDS:
            missing.append(canonical)

    return df.rename(columns=rename_map), missing


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def normalize_category(raw: Any) -> str | None:
    if is_missing(raw):
        return None
    text = str(raw).strip()
    if text in VALID_CATEGORIES:
        return text
    mapped = CATEGORY_ALIASES.get(text.lower().replace(" ", "_"))
    if mapped:
        return mapped
    return CATEGORY_ALIASES.get(text.lower())


def normalize_status(raw: Any) -> str | None:
    if is_missing(raw):
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


def parse_satisfaction_score(value: Any) -> tuple[bool, int | None]:
    if is_missing(value):
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
    df, _ = resolve_columns(df)

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


def validate_record(row: pd.Series) -> tuple[list[str], NormalizedIncidentRecord | None]:
    errors: list[str] = []
    normalized: NormalizedIncidentRecord = {}

    location_id = row.get("locationId")
    if is_missing(location_id):
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
        normalized["category"] = cast(IncidentCategory, category)

    description = row.get("description")
    if is_missing(description) or len(str(description).strip()) < 5:
        errors.append("empty_description")
    else:
        normalized["description"] = str(description).strip()

    reported_by = row.get("reportedBy")
    if is_missing(reported_by):
        errors.append("missing_reporter_id")
    else:
        normalized["reportedBy"] = str(reported_by).strip()

    status = normalize_status(row.get("status"))
    if status is None:
        if not is_missing(row.get("status")):
            errors.append("invalid_status")
    else:
        normalized["status"] = cast(IncidentStatus, status)

    score_ok, score = parse_satisfaction_score(row.get("satisfactionIndex"))
    if not score_ok:
        errors.append("out_of_range_satisfaction_score")
    elif score is not None:
        normalized["satisfactionIndex"] = score

    if status == "CLOSED" and score is None:
        errors.append("closed_case_no_score")

    if not is_missing(row.get("incidentId")):
        normalized["incidentId"] = str(row.get("incidentId")).strip()
    if not is_missing(row.get("reportedAt")):
        normalized["reportedAt"] = str(row.get("reportedAt")).strip()

    if errors:
        return errors, None
    return [], normalized
