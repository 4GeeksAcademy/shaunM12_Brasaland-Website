"""Parse structured LLM output for Support Agent memory (context-26 P26-L8)."""

from __future__ import annotations

import json
import re
from typing import Any

from .keys import MemoryKeyError
from .schemas import GenerationResult, MemoryProposal, ProposalValidationError, validate_proposal_shape

_JSON_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.I)

_SAFE_ANSWER_FALLBACK = "I couldn't return that response safely."

# Exported for graph fallback when structured JSON lacks a user-visible answer.
SAFE_ANSWER_FALLBACK = _SAFE_ANSWER_FALLBACK


def _looks_like_json_object_text(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        return False
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        # Malformed structured output must not leak to the user as the answer.
        return True
    return isinstance(parsed, dict)


looks_like_json_object_text = _looks_like_json_object_text


def _resolve_user_visible_answer(*, payload: dict[str, Any], raw: str) -> str:
    """Prefer parsed answer text; never surface raw JSON blobs to the user."""
    answer = str(payload.get("answer") or "").strip()
    if answer and not _looks_like_json_object_text(answer):
        return answer

    raw_stripped = raw.strip()
    if raw_stripped and not _looks_like_json_object_text(raw_stripped):
        return raw_stripped

    return _SAFE_ANSWER_FALLBACK


def _coerce_proposal_payload(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    return None


def parse_structured_payload(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse JSON object from model output; return (payload, error_reason)."""
    text = (raw or "").strip()
    if not text:
        return None, "parse_failed"

    candidates = [text]
    fence_match = _JSON_FENCE_PATTERN.search(text)
    if fence_match:
        candidates.insert(0, fence_match.group(1).strip())

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed, None

    return None, "parse_failed"


def build_generation_result(
    raw: str,
    *,
    allow_proposal: bool = True,
    question: str | None = None,
) -> GenerationResult:
    """Build validated generation result from raw LLM text (P26-L8, P26-L8c)."""
    payload, parse_error = parse_structured_payload(raw)

    if payload is None:
        fallback_answer = raw.strip()
        if not fallback_answer or _looks_like_json_object_text(fallback_answer):
            fallback_answer = _SAFE_ANSWER_FALLBACK
        return GenerationResult(
            answer=fallback_answer,
            memory_proposal=None,
            proposal_trace=parse_error or "parse_failed",
        )

    answer = _resolve_user_visible_answer(payload=payload, raw=raw)

    if not allow_proposal:
        return GenerationResult(
            answer=answer,
            memory_proposal=None,
            proposal_trace="suppressed_pending",
        )

    proposal_payload = _coerce_proposal_payload(payload.get("memory_proposal"))
    if proposal_payload is None:
        return GenerationResult(answer=answer, memory_proposal=None, proposal_trace=None)

    try:
        validated = validate_proposal_shape(proposal_payload, question=question)
    except (ProposalValidationError, MemoryKeyError) as exc:
        reason = getattr(exc, "reason", None) or "invalid_key"
        return GenerationResult(
            answer=answer,
            memory_proposal=None,
            proposal_trace=f"validation_failed:{reason}",
        )

    return GenerationResult(
        answer=answer,
        memory_proposal=validated,
        proposal_trace=None,
    )
