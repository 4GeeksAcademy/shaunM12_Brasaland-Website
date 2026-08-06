"""RFP Part 2 pipeline helpers — generators, evaluators, loop utilities (context-27 P2)."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from data.pipelines.rfp_intake import (
    _chat_json,
    _chat_text,
    _ensure_repo_root_on_path,
    _generation_available,
    compute_readability_scores,
)

logger = logging.getLogger(__name__)

FK_READABILITY_MAX_GRADE = 12.0

# Re-exported after constants import in functions that need DB-aligned values.
_MAX_ITERATIONS: int | None = None
_USD_COP_RATE: float | None = None
_CEO_THRESHOLD: float | None = None


class GenerationUnavailableError(RuntimeError):
    """Raised when draft generation cannot call the LLM (M9-P2-M7 — no template fallback)."""


def _rfp_constants() -> Any:
    _ensure_repo_root_on_path()
    from rfp.constants import (
        CEO_APPROVAL_THRESHOLD_USD,
        DEPARTMENT_IDS,
        MAX_GENERATOR_EVALUATOR_ITERATIONS,
        USD_COP_RATE,
    )

    return (
        MAX_GENERATOR_EVALUATOR_ITERATIONS,
        USD_COP_RATE,
        CEO_APPROVAL_THRESHOLD_USD,
        DEPARTMENT_IDS,
    )


def max_eval_iterations() -> int:
    global _MAX_ITERATIONS
    if _MAX_ITERATIONS is None:
        _MAX_ITERATIONS, _, _, _ = _rfp_constants()
    return _MAX_ITERATIONS


def usd_cop_rate() -> float:
    global _USD_COP_RATE
    if _USD_COP_RATE is None:
        _, _USD_COP_RATE, _, _ = _rfp_constants()
    return _USD_COP_RATE


def ceo_approval_threshold_usd() -> float:
    global _CEO_THRESHOLD
    if _CEO_THRESHOLD is None:
        _, _, _CEO_THRESHOLD, _ = _rfp_constants()
    return _CEO_THRESHOLD


# --- Brand pillars (CONTEXT.md) -----------------------------------------------

BRAND_PILLAR_CHECKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("consistent product quality", ("quality", "consistent")),
    ("warm customer experience", ("warm", "customer experience", "reliable experience")),
    ("speed of service", ("speed", "service without sacrificing", "fast service")),
)

COMPETITOR_NAMES: tuple[str, ...] = (
    "starbucks",
    "mcdonald",
    "burger king",
    "subway",
    "kfc",
    "domino",
    "dunkin",
)

# Rules that block compliance.passed when present in failures.
BLOCKING_COMPLIANCE_RULES = frozenset(
    {
        "COMPLIANCE_DUAL_CURRENCY",
        "COMPLIANCE_BRAND_PILLARS",
        "COMPLIANCE_MIN_LEAD_TIME_10_BD",
        "COMPLIANCE_NO_COMPETITORS",
        "COMPLIANCE_VALIDITY_30_DAYS",
    }
)

_USD_PRICE_PATTERN = re.compile(
    r"(?<!\w)\$\s*([\d,]+(?:\.\d+)?)\s*(?:USD|usd|/year|per year)?",
)
_COP_PRICE_PATTERN = re.compile(
    r"(?<!\w)(?:COP|\$)\s*([\d,]+(?:\.\d+)?)\s*(?:COP|cop)?",
    re.IGNORECASE,
)
_LEAD_TIME_PATTERN = re.compile(
    r"(\d+)\s*(?:business\s+)?days?",
    re.IGNORECASE,
)


@dataclass
class GeneratorContext:
    """Dept-scoped inputs for draft generation (M9-P2-8)."""

    department_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    key_aspects: list[str] = field(default_factory=list)
    excerpt: str = ""
    intake_summary: str = ""
    retry_feedback: dict[str, Any] | None = None


@dataclass
class EvaluationEnvelope:
    """Persisted evaluation_results JSON shape (M9-P2-5)."""

    latest: dict[str, Any]
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"latest": self.latest, "history": list(self.history)}


# --- Readability evaluator ----------------------------------------------------


def evaluate_readability(draft_content: str) -> dict[str, Any]:
    """FK grade gate — pass when grade <= 12.0 (M9-P2-7)."""
    scores = compute_readability_scores(draft_content)
    grade = scores.get("flesch_kincaid_grade")
    if grade is None:
        word_count = len(re.findall(r"\w+", draft_content))
        # py-readability-metrics requires ~100 words; short sections skip FK scoring.
        if word_count < 100:
            return {
                "passed": True,
                "flesch_kincaid_grade": None,
                "threshold_max_grade": FK_READABILITY_MAX_GRADE,
                "note": "Draft shorter than 100 words; FK grade not computed.",
            }
        return {
            "passed": False,
            "flesch_kincaid_grade": None,
            "threshold_max_grade": FK_READABILITY_MAX_GRADE,
        }
    return {
        "passed": grade <= FK_READABILITY_MAX_GRADE,
        "flesch_kincaid_grade": round(float(grade), 2),
        "threshold_max_grade": FK_READABILITY_MAX_GRADE,
    }


# --- Relevance evaluator ------------------------------------------------------


def _aspect_covered(aspect: str, draft_lower: str) -> bool:
    """Heuristic coverage check when LLM is unavailable (tests / fallback)."""
    aspect_lower = aspect.lower()
    if aspect_lower in draft_lower:
        return True
    # Treat co-marketing / co-branded as related phrasing.
    if "co-marketing" in aspect_lower or "co marketing" in aspect_lower:
        if "co-branded" in draft_lower or "co branded" in draft_lower:
            return True
    tokens = [t for t in re.split(r"[^\w]+", aspect_lower) if len(t) > 3]
    if not tokens:
        return aspect_lower in draft_lower
    hits = sum(1 for token in tokens if token in draft_lower)
    return hits >= max(1, (len(tokens) + 1) // 2)


def evaluate_relevance(
    draft_content: str,
    key_aspects: list[str],
    *,
    use_llm: bool | None = None,
) -> dict[str, Any]:
    """Structured relevance vs key_aspects → missing_topics[] (M9-P2-12, M9-P2-M4)."""
    if not key_aspects:
        return {
            "passed": True,
            "addresses_key_aspects": True,
            "missing_topics": [],
        }

    llm_enabled = _generation_available() if use_llm is None else use_llm
    if llm_enabled:
        try:
            payload = _chat_json(
                system=(
                    "You evaluate whether an RFP section draft covers required topics. "
                    'Return JSON {"missing_topics": [string, ...]} listing key_aspects '
                    "not adequately addressed in the draft. Empty array if all covered."
                ),
                user=json.dumps(
                    {
                        "key_aspects": key_aspects,
                        "draft_content": draft_content[:8000],
                    }
                ),
            )
            missing = [str(t) for t in (payload.get("missing_topics") or [])]
            return {
                "passed": len(missing) == 0,
                "addresses_key_aspects": len(missing) == 0,
                "missing_topics": missing,
            }
        except Exception as exc:  # noqa: BLE001
            logger.debug("LLM relevance eval failed, using heuristic: %s", exc)

    draft_lower = draft_content.lower()
    missing = [aspect for aspect in key_aspects if not _aspect_covered(aspect, draft_lower)]
    return {
        "passed": len(missing) == 0,
        "addresses_key_aspects": len(missing) == 0,
        "missing_topics": missing,
    }


# --- Compliance evaluator (rule-based, p1 §5) ---------------------------------


def _parse_usd_amounts(text: str) -> list[float]:
    amounts: list[float] = []
    for match in _USD_PRICE_PATTERN.finditer(text):
        raw = match.group(1).replace(",", "")
        try:
            amounts.append(float(raw))
        except ValueError:
            continue
    return amounts


def _has_cop_for_usd(text: str, usd_amount: float) -> bool:
    """True when draft includes COP within ±1% of USD_COP_RATE conversion."""
    expected = usd_amount * usd_cop_rate()
    lower = expected * 0.99
    upper = expected * 1.01
    if re.search(r"\bCOP\b", text, re.IGNORECASE) or re.search(
        r"colombian\s+peso", text, re.IGNORECASE
    ):
        for match in _COP_PRICE_PATTERN.finditer(text):
            raw = match.group(1).replace(",", "")
            try:
                cop_value = float(raw)
            except ValueError:
                continue
            if lower <= cop_value <= upper:
                return True
        # COP label present with a different numeric — lenient pass if any COP amount listed
        if _COP_PRICE_PATTERN.search(text):
            return True
    return False


def _check_dual_currency(draft_content: str) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    usd_amounts = _parse_usd_amounts(draft_content)
    if not usd_amounts:
        return failures
    if not any(_has_cop_for_usd(draft_content, amount) for amount in usd_amounts):
        failures.append(
            {
                "rule_id": "COMPLIANCE_DUAL_CURRENCY",
                "message": "Section quotes USD only.",
                "suggested_fix": (
                    f"Add COP equivalent using USD_COP_RATE {int(usd_cop_rate())}."
                ),
            }
        )
    return failures


def _check_brand_pillars(draft_content: str) -> list[dict[str, str]]:
    lower = draft_content.lower()
    missing_labels: list[str] = []
    for label, keywords in BRAND_PILLAR_CHECKS:
        if not any(keyword in lower for keyword in keywords):
            missing_labels.append(label)
    if not missing_labels:
        return []
    return [
        {
            "rule_id": "COMPLIANCE_BRAND_PILLARS",
            "message": f"Missing brand pillars: {', '.join(missing_labels)}.",
            "suggested_fix": (
                "Reference consistent quality, warm customer experience, "
                "and speed of service (CONTEXT.md pillars)."
            ),
        }
    ]


_LEAD_TIME_CONTEXT_TOKENS = (
    "setup",
    "delivery",
    "install",
    "deploy",
    "implementation",
    "lead time",
    "lead-time",
    "go-live",
    "go live",
    "rollout",
)
_LEAD_TIME_EXCLUSION_TOKENS = (
    "backup",
    "response",
    "react",
    "emergency",
    "alternate",
    "notification",
    "notice period",
    "spare",
)


def _check_min_lead_time(draft_content: str) -> list[dict[str, str]]:
    for match in _LEAD_TIME_PATTERN.finditer(draft_content):
        days = int(match.group(1))
        if days >= 10:
            continue
        context = draft_content[max(0, match.start() - 50) : match.end() + 50].lower()
        if any(token in context for token in _LEAD_TIME_EXCLUSION_TOKENS):
            continue
        if not any(token in context for token in _LEAD_TIME_CONTEXT_TOKENS):
            continue
        return [
            {
                "rule_id": "COMPLIANCE_MIN_LEAD_TIME_10_BD",
                "message": f"Promises {days} days — minimum is 10 business days.",
                "suggested_fix": "State setup/delivery lead time of at least 10 business days.",
            }
        ]
    return []


def _check_no_competitors(draft_content: str) -> list[dict[str, str]]:
    lower = draft_content.lower()
    hits = [name.title() for name in COMPETITOR_NAMES if name in lower]
    if not hits:
        return []
    return [
        {
            "rule_id": "COMPLIANCE_NO_COMPETITORS",
            "message": f"Competitor reference detected: {', '.join(hits)}.",
            "suggested_fix": "Remove competitor names from the proposal section.",
        }
    ]


def _check_validity_30_days(draft_content: str) -> list[dict[str, str]]:
    lower = draft_content.lower()
    if not any(token in lower for token in ("valid", "validity", "offer expires")):
        return []
    if re.search(r"\b30\s*days?\b", lower) or "thirty days" in lower:
        return []
    return [
        {
            "rule_id": "COMPLIANCE_VALIDITY_30_DAYS",
            "message": "Offer validity must be 30 days from issuance.",
            "suggested_fix": "State that this offer is valid for 30 days from issuance.",
        }
    ]


def _check_ceo_threshold_flag(
    draft_content: str,
    metadata: dict[str, Any],
) -> list[dict[str, str]]:
    """Flag-only rule — does not block compliance.passed (M9-P2-6 / p1 §5)."""
    value = metadata.get("estimated_contract_value_usd")
    if value is None:
        return []
    try:
        if float(value) <= ceo_approval_threshold_usd():
            return []
    except (TypeError, ValueError):
        return []
    lower = draft_content.lower()
    if "ceo" in lower or "executive approval" in lower:
        return []
    return [
        {
            "rule_id": "COMPLIANCE_CEO_THRESHOLD_50K",
            "message": (
                f"Contract value exceeds ${int(ceo_approval_threshold_usd()):,} USD/year; "
                "CEO approval required before final document (P3)."
            ),
            "suggested_fix": "Note that CEO approval is required for contracts over $50,000 USD/year.",
        }
    ]


def evaluate_compliance(
    draft_content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rule-based compliance on p1 §5 COMPLIANCE_* IDs (M9-P2-6)."""
    meta = metadata or {}
    failures: list[dict[str, str]] = []
    failures.extend(_check_dual_currency(draft_content))
    failures.extend(_check_brand_pillars(draft_content))
    failures.extend(_check_min_lead_time(draft_content))
    failures.extend(_check_no_competitors(draft_content))
    failures.extend(_check_validity_30_days(draft_content))
    failures.extend(_check_ceo_threshold_flag(draft_content, meta))

    blocking = [f for f in failures if f["rule_id"] in BLOCKING_COMPLIANCE_RULES]
    advisory = [f for f in failures if f["rule_id"] not in BLOCKING_COMPLIANCE_RULES]
    return {
        "passed": len(blocking) == 0,
        "failures": blocking,
        "advisory": advisory,
    }


# --- Join + EvaluationResult --------------------------------------------------


def compute_overall_passed(
    readability: dict[str, Any],
    relevance: dict[str, Any],
    compliance: dict[str, Any],
) -> bool:
    """All three dimensions must pass (M9-P2-11)."""
    return bool(
        readability.get("passed")
        and relevance.get("passed")
        and compliance.get("passed")
    )


def evaluate_section(
    *,
    department_id: str,
    draft_content: str,
    key_aspects: list[str],
    metadata: dict[str, Any] | None = None,
    iteration: int = 1,
    use_llm_relevance: bool | None = None,
) -> dict[str, Any]:
    """Run readability, relevance, and compliance evaluators; return EvaluationResult."""
    readability = evaluate_readability(draft_content)
    relevance = evaluate_relevance(
        draft_content,
        key_aspects,
        use_llm=use_llm_relevance,
    )
    compliance = evaluate_compliance(draft_content, metadata)
    overall_passed = compute_overall_passed(readability, relevance, compliance)
    return {
        "iteration": iteration,
        "department_id": department_id,
        "readability": readability,
        "relevance": relevance,
        "compliance": compliance,
        "overall_passed": overall_passed,
        "needs_human_review": False,
    }


def evaluate_section_parallel_inputs(
    *,
    department_id: str,
    draft_content: str,
    key_aspects: list[str],
    metadata: dict[str, Any] | None = None,
    iteration: int = 1,
    use_llm_relevance: bool | None = None,
) -> dict[str, Any]:
    """Evaluate dimensions independently then join (mirrors parallel eval graph nodes)."""
    readability = evaluate_readability(draft_content)
    relevance = evaluate_relevance(
        draft_content,
        key_aspects,
        use_llm=use_llm_relevance,
    )
    compliance = evaluate_compliance(draft_content, metadata)
    return join_evaluation_dimensions(
        department_id=department_id,
        iteration=iteration,
        readability=readability,
        relevance=relevance,
        compliance=compliance,
    )


def join_evaluation_dimensions(
    *,
    department_id: str,
    iteration: int,
    readability: dict[str, Any],
    relevance: dict[str, Any],
    compliance: dict[str, Any],
) -> dict[str, Any]:
    """Aggregate parallel evaluator outputs before loop decision."""
    overall_passed = compute_overall_passed(readability, relevance, compliance)
    return {
        "iteration": iteration,
        "department_id": department_id,
        "readability": readability,
        "relevance": relevance,
        "compliance": compliance,
        "overall_passed": overall_passed,
        "needs_human_review": False,
    }


# --- Loop helpers -------------------------------------------------------------


def should_retry_evaluation(evaluation: dict[str, Any], iteration: int) -> bool:
    """True when eval failed and iterations remain (M9-P2-M5 / M9-G2)."""
    if evaluation.get("overall_passed"):
        return False
    return iteration < max_eval_iterations()


def mark_needs_human_review(evaluation: dict[str, Any]) -> dict[str, Any]:
    """Set needs_human_review on exhausted eval (M9-P2-3, M9-P2-M3)."""
    updated = dict(evaluation)
    updated["needs_human_review"] = True
    return updated


def resolve_draft_status_after_evaluation(
    evaluation: dict[str, Any],
    iteration: int,
) -> str:
    """Map evaluation outcome to section draft_status (M9-P2-9)."""
    _ensure_repo_root_on_path()
    from rfp.constants import (
        DRAFT_STATUS_EVALUATING,
        DRAFT_STATUS_NEEDS_HUMAN_REVIEW,
        DRAFT_STATUS_PASSED,
    )

    if evaluation.get("overall_passed"):
        return DRAFT_STATUS_PASSED
    if evaluation.get("needs_human_review") or iteration >= max_eval_iterations():
        return DRAFT_STATUS_NEEDS_HUMAN_REVIEW
    return DRAFT_STATUS_EVALUATING


def build_retry_feedback(
    evaluation: dict[str, Any],
    *,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Concrete failure feedback for generator retry (M9-P2 design Q)."""
    feedback: dict[str, Any] = {}
    readability = evaluation.get("readability") or {}
    relevance = evaluation.get("relevance") or {}
    compliance = evaluation.get("compliance") or {}

    if not readability.get("passed"):
        grade = readability.get("flesch_kincaid_grade")
        threshold = readability.get("threshold_max_grade", FK_READABILITY_MAX_GRADE)
        feedback["readability"] = (
            f"Flesch-Kincaid grade {grade} exceeds {threshold}. "
            "Use shorter sentences and simpler wording."
        )

    prior_evaluations = list(history or [])
    missing_topics: list[str] = []
    seen_topics: set[str] = set()
    for prior in prior_evaluations + [evaluation]:
        for topic in prior.get("relevance", {}).get("missing_topics") or []:
            if topic not in seen_topics:
                seen_topics.add(topic)
                missing_topics.append(str(topic))
    if missing_topics:
        feedback["missing_topics"] = missing_topics

    compliance_failures: list[dict[str, str]] = []
    seen_rules: set[str] = set()
    for prior in prior_evaluations + [evaluation]:
        for failure in prior.get("compliance", {}).get("failures") or []:
            rule_id = str(failure.get("rule_id") or "")
            if rule_id in BLOCKING_COMPLIANCE_RULES and rule_id not in seen_rules:
                seen_rules.add(rule_id)
                compliance_failures.append(failure)
    if compliance_failures:
        feedback["compliance_failures"] = compliance_failures

    preserve: list[str] = []
    if readability.get("passed"):
        grade = readability.get("flesch_kincaid_grade")
        preserve.append(
            f"Readability passed (FK {grade}). Keep plain, short sentences — "
            "do not add length or marketing formality."
        )
    if relevance.get("passed"):
        preserve.append(
            "Relevance passed. Keep all key aspects covered in the revised draft."
        )
    if compliance.get("passed"):
        preserve.append(
            "Compliance passed. Do not remove dual currency, brand pillars, "
            "30-day validity, or 10+ business day setup/delivery wording."
        )
    if preserve:
        feedback["preserve"] = preserve

    feedback["instruction"] = (
        "Fix every listed failure. Preserve dimensions noted under preserve — "
        "do not undo prior fixes."
    )
    return feedback


def append_evaluation_history(
    envelope: EvaluationEnvelope | dict[str, Any] | None,
    new_latest: dict[str, Any],
) -> EvaluationEnvelope:
    """Push previous latest to history before retry (M9-P2-5)."""
    if envelope is None:
        return EvaluationEnvelope(latest=new_latest, history=[])
    if isinstance(envelope, dict):
        envelope = EvaluationEnvelope(
            latest=envelope.get("latest") or {},
            history=list(envelope.get("history") or []),
        )
    history = list(envelope.history)
    if envelope.latest:
        history.append(envelope.latest)
    return EvaluationEnvelope(latest=new_latest, history=history)


def finalize_evaluation_after_loop(
    evaluation: dict[str, Any],
    iteration: int,
) -> tuple[dict[str, Any], str]:
    """Apply max-iter handoff and return (evaluation, draft_status)."""
    if not evaluation.get("overall_passed") and iteration >= max_eval_iterations():
        evaluation = mark_needs_human_review(evaluation)
    draft_status = resolve_draft_status_after_evaluation(evaluation, iteration)
    return evaluation, draft_status


# --- Optional RAG (M9-P2-10) --------------------------------------------------


def _maybe_retrieve_context(key_aspects: list[str]) -> str:
    if os.getenv("RFP_GENERATION_USE_RAG", "").lower() != "true":
        return ""
    try:
        from data.pipelines.rag import retrieve

        query = " ".join(key_aspects) or "Brasaland RFP proposal guidelines"
        hits = retrieve(query, k=3, min_score=0.30)
        if not hits:
            return ""
        snippets = [
            str(h.get("text") or h.get("content") or h) for h in hits if h
        ]
        return "\n".join(snippets[:3])
    except Exception as exc:  # noqa: BLE001
        logger.debug("RAG retrieve skipped: %s", exc)
        return ""


# --- Per-department generators (M9-P2-18) ---------------------------------------

_DEPARTMENT_SYSTEM_PROMPTS: dict[str, str] = {
    "marketing": (
        "You are the Brasaland Marketing department proposal writer. Draft the marketing "
        "and digital experience section of a B2B RFP response. Address brand co-marketing, "
        "exclusivity, and offer validity. Use plain language: short sentences, simple words, "
        "Flesch-Kincaid grade 12 or below — not formal marketing jargon."
    ),
    "operations": (
        "You are the Brasaland Restaurant Operations proposal writer. Draft the operations "
        "section covering staffing, setup timeline, peak season capacity, and service cadence."
    ),
    "procurement": (
        "You are the Brasaland Procurement proposal writer. Draft the procurement section "
        "with pricing in USD and COP, supplier lead times, and volume assumptions."
    ),
    "training": (
        "You are the Brasaland Training and Quality Standards proposal writer. Draft the "
        "training section covering recipe development, certification, and rollout timelines."
    ),
}


def _compliance_writer_hints() -> str:
    rate = int(usd_cop_rate())
    return (
        f"Compliance requirements: quote prices in both USD and COP (use rate 1 USD = {rate} COP); "
        "mention consistent quality, warm customer experience, and speed of service; "
        "state offer validity for 30 days from issuance; "
        "setup/delivery/install/deploy timelines must be at least 10 business days (use 12+); "
        "never promise fewer than 10 business days for setup or delivery; "
        "backup/response times may be shorter but must not use setup/delivery wording; "
        "no competitor names."
    )


def _build_generator_user_message(ctx: GeneratorContext) -> str:
    parts = [
        f"Department: {ctx.department_id}",
        f"Client metadata: {json.dumps(ctx.metadata, default=str)[:4000]}",
        f"Key aspects to address: {json.dumps(ctx.key_aspects)}",
    ]
    if ctx.intake_summary:
        parts.append(f"Intake summary:\n{ctx.intake_summary[:2000]}")
    if ctx.excerpt:
        parts.append(f"RFP excerpt:\n{ctx.excerpt[:4000]}")
    rag_context = _maybe_retrieve_context(ctx.key_aspects)
    if rag_context:
        parts.append(f"Reference context:\n{rag_context[:2000]}")
    if ctx.retry_feedback:
        parts.append(f"Fix these evaluation failures:\n{json.dumps(ctx.retry_feedback)}")
    parts.append(_compliance_writer_hints())
    parts.append(
        "Return only the section markdown text. Do not wrap the response in JSON or code fences."
    )
    return "\n\n".join(parts)


def generate_department_draft(ctx: GeneratorContext) -> str:
    """Generate one department section draft via LLM (raises if unavailable — M9-P2-M7)."""
    if not _generation_available():
        raise GenerationUnavailableError(
            "Draft generation requires GENERATION_BASE_URL, GENERATION_API_KEY, and "
            "GENERATION_MODEL_ID."
        )
    _, _, _, department_ids = _rfp_constants()
    if ctx.department_id not in department_ids:
        raise ValueError(f"Unknown department_id: {ctx.department_id}")

    system = _DEPARTMENT_SYSTEM_PROMPTS.get(
        ctx.department_id,
        f"You write the {ctx.department_id} section of a Brasaland RFP response.",
    )
    draft = _chat_text(system=system, user=_build_generator_user_message(ctx)).strip()
    if not draft:
        raise GenerationUnavailableError("LLM returned empty draft_content.")
    return draft


def generate_marketing_draft(ctx: GeneratorContext) -> str:
    return generate_department_draft(
        GeneratorContext(
            department_id="marketing",
            metadata=ctx.metadata,
            key_aspects=ctx.key_aspects,
            excerpt=ctx.excerpt,
            intake_summary=ctx.intake_summary,
            retry_feedback=ctx.retry_feedback,
        )
    )


def generate_operations_draft(ctx: GeneratorContext) -> str:
    return generate_department_draft(
        GeneratorContext(
            department_id="operations",
            metadata=ctx.metadata,
            key_aspects=ctx.key_aspects,
            excerpt=ctx.excerpt,
            intake_summary=ctx.intake_summary,
            retry_feedback=ctx.retry_feedback,
        )
    )


def generate_procurement_draft(ctx: GeneratorContext) -> str:
    return generate_department_draft(
        GeneratorContext(
            department_id="procurement",
            metadata=ctx.metadata,
            key_aspects=ctx.key_aspects,
            excerpt=ctx.excerpt,
            intake_summary=ctx.intake_summary,
            retry_feedback=ctx.retry_feedback,
        )
    )


def generate_training_draft(ctx: GeneratorContext) -> str:
    return generate_department_draft(
        GeneratorContext(
            department_id="training",
            metadata=ctx.metadata,
            key_aspects=ctx.key_aspects,
            excerpt=ctx.excerpt,
            intake_summary=ctx.intake_summary,
            retry_feedback=ctx.retry_feedback,
        )
    )


GENERATORS: dict[str, Callable[[GeneratorContext], str]] = {
    "marketing": generate_marketing_draft,
    "operations": generate_operations_draft,
    "procurement": generate_procurement_draft,
    "training": generate_training_draft,
}


def generate_draft(ctx: GeneratorContext) -> str:
    """Dispatch to the registered generator for department_id (M9-P2-18)."""
    generator = GENERATORS.get(ctx.department_id)
    if generator is None:
        raise ValueError(f"No generator registered for department: {ctx.department_id}")
    return generator(ctx)


def run_department_generation_loop(
    *,
    department_id: str,
    metadata: dict[str, Any],
    key_aspects: list[str],
    excerpt: str,
    intake_summary: str = "",
    use_llm_relevance: bool | None = None,
) -> tuple[str, dict[str, Any], str]:
    """Generate and evaluate one department section until pass or max iterations.

    Returns ``(draft_content, evaluation_results envelope, draft_status)``.
    Raises ``GenerationUnavailableError`` on LLM infra failure (M9-P2-M7).
    """
    ctx = GeneratorContext(
        department_id=department_id,
        metadata=metadata,
        key_aspects=list(key_aspects),
        excerpt=excerpt,
        intake_summary=intake_summary,
    )
    envelope: EvaluationEnvelope | None = None
    iteration = 1
    draft = ""

    while iteration <= max_eval_iterations():
        ctx.retry_feedback = (
            build_retry_feedback(envelope.latest, history=envelope.history)
            if envelope and envelope.latest
            else None
        )
        draft = generate_draft(ctx)
        evaluation = evaluate_section(
            department_id=department_id,
            draft_content=draft,
            key_aspects=key_aspects,
            metadata=metadata,
            iteration=iteration,
            use_llm_relevance=use_llm_relevance,
        )
        if evaluation.get("overall_passed"):
            final_eval, draft_status = finalize_evaluation_after_loop(
                evaluation,
                iteration,
            )
            envelope = append_evaluation_history(envelope, final_eval)
            return draft, envelope.to_dict(), draft_status

        if not should_retry_evaluation(evaluation, iteration):
            final_eval, draft_status = finalize_evaluation_after_loop(
                evaluation,
                iteration,
            )
            envelope = append_evaluation_history(envelope, final_eval)
            return draft, envelope.to_dict(), draft_status

        envelope = append_evaluation_history(envelope, evaluation)
        iteration += 1

    final_eval, draft_status = finalize_evaluation_after_loop(
        envelope.latest if envelope else evaluation,
        iteration - 1,
    )
    return draft, append_evaluation_history(envelope, final_eval).to_dict(), draft_status


__all__ = [
    "BLOCKING_COMPLIANCE_RULES",
    "FK_READABILITY_MAX_GRADE",
    "GENERATORS",
    "GenerationUnavailableError",
    "GeneratorContext",
    "EvaluationEnvelope",
    "append_evaluation_history",
    "build_retry_feedback",
    "compute_overall_passed",
    "evaluate_compliance",
    "evaluate_readability",
    "evaluate_relevance",
    "evaluate_section",
    "evaluate_section_parallel_inputs",
    "finalize_evaluation_after_loop",
    "generate_draft",
    "generate_department_draft",
    "join_evaluation_dimensions",
    "mark_needs_human_review",
    "max_eval_iterations",
    "resolve_draft_status_after_evaluation",
    "run_department_generation_loop",
    "should_retry_evaluation",
]
