"""Personal-use scoring (context-25 P25-L11c, P25-L11e).

Assessment logic implemented in P25-2.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

DEFAULT_BLOCK_THRESHOLD = 0.55
DEFAULT_FAMILY_BLOCK_THRESHOLD = 0.50


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning(
            "Invalid %s=%r — using default %s",
            name,
            raw,
            default,
        )
        return default


def block_threshold() -> float:
    return _float_env("AGENT_PERSONAL_USE_BLOCK_THRESHOLD", DEFAULT_BLOCK_THRESHOLD)


def family_block_threshold() -> float:
    return _float_env(
        "AGENT_PERSONAL_USE_FAMILY_THRESHOLD",
        DEFAULT_FAMILY_BLOCK_THRESHOLD,
    )


@dataclass(frozen=True)
class GeneralTaskAssessment:
    score: float
    families: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)

    @property
    def should_block(self) -> bool:
        if self.families and self.score >= family_block_threshold():
            return True
        return self.score >= block_threshold()


FAMILY_SCORE = 0.35
DELEGATION_SCORE = 0.20
DELIVERABLE_SCORE = 0.15
PERSONAL_POSSESSIVE_SCORE = 0.15
ROLEPLAY_SCORE = 0.25
LONG_OFF_TOPIC_SCORE = 0.10
LONG_OFF_TOPIC_MIN_WORDS = 25
DELEGATION_DELIVERABLE_BONUS = 0.10


def _match_families(text: str) -> tuple[list[str], list[str]]:
    from .patterns_personal import PERSONAL_TASK_FAMILIES

    families: list[str] = []
    signals: list[str] = []
    for pattern, family_id in PERSONAL_TASK_FAMILIES:
        if pattern.search(text):
            if family_id not in families:
                families.append(family_id)
            signals.append(f"family:{family_id}")
    return families, signals


def assess_general_assistant_task(question: str) -> GeneralTaskAssessment:
    """Score off-domain personal / general-AI task signals (P25-L11c)."""
    from .patterns_personal import (
        DELIVERABLE_REQUEST,
        PERSONAL_POSSESSIVE,
        ROLEPLAY_REQUEST,
        TASK_DELEGATION,
    )

    text = (question or "").strip()
    if not text:
        return GeneralTaskAssessment(score=0.0)

    score = 0.0
    families, signals = _match_families(text)
    if families:
        score += FAMILY_SCORE

    if TASK_DELEGATION.search(text):
        score += DELEGATION_SCORE
        signals.append("task_delegation")

    if DELIVERABLE_REQUEST.search(text):
        score += DELIVERABLE_SCORE
        signals.append("deliverable_request")

    if PERSONAL_POSSESSIVE.search(text):
        score += PERSONAL_POSSESSIVE_SCORE
        signals.append("personal_possessive")

    if ROLEPLAY_REQUEST.search(text):
        score += ROLEPLAY_SCORE
        signals.append("roleplay_request")

    if len(text.split()) >= LONG_OFF_TOPIC_MIN_WORDS:
        score += LONG_OFF_TOPIC_SCORE
        signals.append("long_off_topic")

    if "task_delegation" in signals and "deliverable_request" in signals:
        score += DELEGATION_DELIVERABLE_BONUS
        signals.append("delegation_plus_deliverable")

    return GeneralTaskAssessment(
        score=min(score, 1.0),
        families=families,
        signals=signals,
    )


def primary_personal_reason(assessment: GeneralTaskAssessment) -> str:
    """Stable reason code for logging and messages."""
    if assessment.families:
        return f"personal_use:{assessment.families[0]}"
    if "roleplay_request" in assessment.signals:
        return "personal_use:roleplay"
    if "task_delegation" in assessment.signals:
        return "personal_use:task_delegation"
    return "personal_use:general"
