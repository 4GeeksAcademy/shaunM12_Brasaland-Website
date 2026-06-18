"""Domain constants and lookup tables for Brasaland incident CSV analysis."""

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
