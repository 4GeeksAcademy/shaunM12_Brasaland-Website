"""Human-readable summaries and CSV export rows for analysis results."""

from __future__ import annotations

import re

from .constants import SATISFACTION_LABELS
from .schemas import AnalysisResult, ResultMetricRow


def _percentage(count: int, total: int) -> str | None:
    if total <= 0:
        return None
    return f"{(count / total) * 100:.1f}%"


def build_results_rows(result: AnalysisResult) -> list[ResultMetricRow]:
    rows: list[ResultMetricRow] = [
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
        row: ResultMetricRow = {
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


def format_summary(result: AnalysisResult) -> str:
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
