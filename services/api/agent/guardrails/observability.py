"""Guardrail event counters and logging helpers (context-25 P25-L20, P25-L21b)."""

from __future__ import annotations

import hashlib
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

SUMMARY_SCOPE_LABEL = "since_process_start"


@dataclass
class GuardrailSummary:
    """Snapshot of counters since process start (P25-L22b)."""

    since: str = SUMMARY_SCOPE_LABEL
    by_failure_type: dict[str, int] = field(default_factory=dict)
    by_reason: dict[str, int] = field(default_factory=dict)
    blocks: int = 0
    redirects: int = 0
    validation_failures: int = 0


_lock = Lock()
_by_failure_type: dict[str, int] = defaultdict(int)
_by_reason: dict[str, int] = defaultdict(int)
_blocks = 0
_redirects = 0
_validation_failures = 0


def question_hash_prefix(question: str | None) -> str | None:
    """Stable short hash prefix for observability — never log full question text."""
    if not question:
        return None
    digest = hashlib.sha256(question.strip().encode("utf-8")).hexdigest()
    return digest[:12]


def record_guardrail_event(
    *,
    action: str,
    failure_type: str | None = None,
    reason: str | None = None,
    question: str | None = None,
    **extra: Any,
) -> None:
    """Increment in-memory counters and emit structured INFO log (P25-L20)."""
    global _blocks, _redirects, _validation_failures

    question_len = extra.get("question_len")
    if question_len is None and question is not None:
        question_len = len(question.strip())
    q_hash = extra.get("question_hash")
    if q_hash is None:
        q_hash = question_hash_prefix(question)

    with _lock:
        if action == "block":
            _blocks += 1
        elif action == "redirect":
            _redirects += 1
        elif action == "validation_failure":
            _validation_failures += 1
        if failure_type:
            _by_failure_type[failure_type] += 1
        if reason:
            _by_reason[reason] += 1

    log_parts: list[str] = [f"action={action}"]
    if failure_type:
        log_parts.append(f"failure_type={failure_type}")
    if reason:
        log_parts.append(f"reason={reason}")
    if question_len is not None:
        log_parts.append(f"question_len={question_len}")
    if q_hash:
        log_parts.append(f"question_hash={q_hash}")
    logger.info("guardrail %s", " ".join(log_parts))


def get_guardrail_summary() -> GuardrailSummary:
    """Return counter snapshot for CLI (P25-L22)."""
    with _lock:
        return GuardrailSummary(
            since=SUMMARY_SCOPE_LABEL,
            by_failure_type=dict(_by_failure_type),
            by_reason=dict(_by_reason),
            blocks=_blocks,
            redirects=_redirects,
            validation_failures=_validation_failures,
        )


def reset_guardrail_counters_for_tests() -> None:
    """Test helper — reset in-memory counters."""
    global _blocks, _redirects, _validation_failures
    with _lock:
        _by_failure_type.clear()
        _by_reason.clear()
        _blocks = 0
        _redirects = 0
        _validation_failures = 0
