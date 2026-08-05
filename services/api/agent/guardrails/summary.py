"""CLI guardrail summary (context-25 P25-L22, P25-L22b).

Usage:

- CLI: ``cd services/api && uv run python -m agent.guardrails.summary``
- HTTP: ``GET /agent/guardrails/summary`` (auth required; same process as API)
"""

from __future__ import annotations

from agent.schemas import GuardrailSummaryResponse

from .observability import SUMMARY_SCOPE_LABEL, get_guardrail_summary


def build_guardrail_summary_response() -> GuardrailSummaryResponse:
    """JSON-serializable summary for HTTP and tests."""
    summary = get_guardrail_summary()
    return GuardrailSummaryResponse(
        since=summary.since,
        blocks=summary.blocks,
        redirects=summary.redirects,
        validation_failures=summary.validation_failures,
        by_failure_type=dict(summary.by_failure_type),
        by_reason=dict(summary.by_reason),
    )


def format_guardrail_summary() -> str:
    """Render human-readable summary for CLI or tests."""
    summary = get_guardrail_summary()
    lines = [
        f"Guardrail summary ({SUMMARY_SCOPE_LABEL})",
        f"  blocks:               {summary.blocks}",
        f"  redirects:            {summary.redirects}",
        f"  validation_failures:  {summary.validation_failures}",
    ]
    if summary.by_failure_type:
        lines.append("  by failure_type:")
        for key, count in sorted(summary.by_failure_type.items()):
            lines.append(f"    {key}: {count}")
    if summary.by_reason:
        lines.append("  by reason:")
        for key, count in sorted(summary.by_reason.items()):
            lines.append(f"    {key}: {count}")
    return "\n".join(lines)


def main() -> None:
    print(format_guardrail_summary())


if __name__ == "__main__":
    main()
