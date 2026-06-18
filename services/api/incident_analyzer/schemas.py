"""Typed shapes for incident records and analysis results."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

IncidentCategory = Literal[
    "CUSTOMER_COMPLAINT",
    "EQUIPMENT",
    "SUPPLY",
    "FOOD_QUALITY",
    "STAFF",
]

IncidentStatus = Literal["OPEN", "CLOSED", "DISCARDED"]


class NormalizedIncidentRecord(TypedDict, total=False):
    incidentId: str
    reportedAt: str
    locationId: str
    category: IncidentCategory
    status: IncidentStatus
    reportedBy: str
    description: str
    satisfactionIndex: int


class AnalysisResult(TypedDict):
    sourcePath: str
    schemaError: str | None
    totalProcessed: int
    validCount: int
    invalidCount: int
    invalidReasons: dict[str, int]
    invalidRowSamples: list[int]
    byCategory: dict[IncidentCategory, int]
    byStatus: dict[IncidentStatus, int]
    avgSatisfactionClosed: float | None
    satisfactionClosedCount: int
    closedCaseCount: int
    satisfactionScoreBreakdown: dict[str, int]


class ResultMetricRow(TypedDict):
    metric: str
    value: str
    percentage: NotRequired[str]
