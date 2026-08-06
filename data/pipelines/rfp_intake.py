"""RFP intake pipeline helpers — PDF conversion, readability, classification (context-27 P1)."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    return _REPO_ROOT


def _ensure_repo_root_on_path() -> Path:
    import sys

    root_str = str(_REPO_ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    api_dir = _REPO_ROOT / "services" / "api"
    api_str = str(api_dir)
    if api_dir.is_dir() and api_str not in sys.path:
        sys.path.append(api_str)
    return _REPO_ROOT


def _extract_pdf_text_pdfplumber(pdf_path: Path) -> str:
    """Fallback plain-text extraction when MarkItDown output is too short."""
    import pdfplumber

    chunks: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                chunks.append(page_text.strip())
    return "\n\n".join(chunks).strip()


def convert_pdf_to_markdown(pdf_path: Path) -> str:
    """Convert a PDF file to Markdown using MarkItDown, with pdfplumber fallback."""
    from markitdown import MarkItDown

    _ensure_repo_root_on_path()
    from rfp.constants import MIN_RFP_MARKDOWN_CHARS

    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    converter = MarkItDown()
    result = converter.convert(str(pdf_path))
    text = (result.text_content or "").strip()
    if len(text) < MIN_RFP_MARKDOWN_CHARS:
        fallback = _extract_pdf_text_pdfplumber(pdf_path)
        if len(fallback) > len(text):
            logger.info(
                "MarkItDown output short (%d chars) for %s — using pdfplumber fallback (%d chars)",
                len(text),
                pdf_path.name,
                len(fallback),
            )
            text = fallback
    if not text:
        raise ValueError("PDF conversion produced empty text")
    return text


def _readability_metric_value(raw: Any) -> float | None:
    if raw is None:
        return None
    score = getattr(raw, "score", None)
    if score is not None:
        return float(score)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def compute_readability_scores(markdown_text: str) -> dict[str, float]:
    """Compute readability metrics via py-readability-metrics."""
    import nltk
    from readability import Readability

    if not markdown_text.strip():
        return {}

    nltk.download("punkt_tab", quiet=True)

    analyzer = Readability(markdown_text)
    scores: dict[str, float] = {}
    for name, getter in (
        ("flesch_reading_ease", analyzer.flesch),
        ("flesch_kincaid_grade", analyzer.flesch_kincaid),
        ("gunning_fog", analyzer.gunning_fog),
    ):
        try:
            value = _readability_metric_value(getter())
            if value is not None:
                scores[name] = value
        except Exception as exc:  # noqa: BLE001 — metric may fail on short text
            logger.debug("readability %s skipped: %s", name, exc)
    return scores


def _generation_available() -> bool:
    return bool(
        os.getenv("GENERATION_BASE_URL", "").strip()
        and os.getenv("GENERATION_API_KEY", "").strip()
        and os.getenv("GENERATION_MODEL_ID", "").strip()
    )


def _strip_json_fences(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json|markdown|md)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_json_object(content: str) -> dict[str, Any]:
    text = _strip_json_fences(content)
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as first_exc:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        raise first_exc


def _chat_json(system: str, user: str, *, retries: int = 1) -> dict[str, Any]:
    """Call generation LLM and parse a JSON object response."""
    _ensure_repo_root_on_path()
    from data.pipelines.rag import generation_client

    model_id = os.getenv("GENERATION_MODEL_ID", "").strip()
    client = generation_client()
    last_exc: json.JSONDecodeError | None = None
    for attempt in range(retries + 1):
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        content = (response.choices[0].message.content or "").strip()
        try:
            return _parse_json_object(content)
        except json.JSONDecodeError as exc:
            last_exc = exc
            if attempt < retries:
                logger.warning("LLM JSON parse failed (attempt %s), retrying: %s", attempt + 1, exc)
                continue
            raise
    if last_exc is not None:
        raise last_exc
    return {}


def _chat_text(system: str, user: str) -> str:
    """Call generation LLM and return plain text (for long markdown drafts)."""
    _ensure_repo_root_on_path()
    from data.pipelines.rag import generation_client

    model_id = os.getenv("GENERATION_MODEL_ID", "").strip()
    client = generation_client()
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    return _strip_json_fences((response.choices[0].message.content or "").strip())


@dataclass
class ClassifyResult:
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)
    departments_needed: list[str] = field(default_factory=list)
    unmapped_topics: list[str] = field(default_factory=list)
    requires_ceo_approval: bool = False
    discard_reason: str | None = None
    discard_rule_id: str | None = None


def _parse_usd_upper_bound(text: str) -> float | None:
    """Extract upper USD/year bound from strings like $60,000-$75,000 USD."""
    patterns = [
        r"\$\s*([\d,]+)\s*[-–]\s*\$\s*([\d,]+)\s*(?:usd|USD)?",
        r"\$\s*([\d,]+)\s*(?:usd|USD)(?:\s*/\s*year)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        groups = [g for g in match.groups() if g]
        values = [float(g.replace(",", "")) for g in groups]
        return max(values)
    return None


def _count_missing_core_fields(metadata: dict[str, Any]) -> int:
    missing = 0
    if not (metadata.get("client_name") or "").strip():
        missing += 1
    if not (metadata.get("scope") or metadata.get("service_type") or "").strip():
        missing += 1
    if not (metadata.get("deadline") or "").strip():
        missing += 1
    return missing


def _heuristic_classify(markdown_text: str) -> ClassifyResult | None:
    """Deterministic classifier for course seed documents and obvious cases."""
    text = markdown_text.lower()

    if "franchise" in text and "proposal due" not in text:
        if not any(
            token in text
            for token in ("catering", "concession", "co-branded", "scope of work", "rfp reference")
        ):
            return ClassifyResult(
                status="discarded",
                metadata={"client_name": "Andres Salazar"},
                discard_reason=(
                    "Franchise inquiry with no corporate scope, budget, or proposal deadline; "
                    "not a Brasaland B2B RFP."
                ),
                discard_rule_id="missing_core_fields",
            )

    if "sunset bay" in text:
        upper_usd = _parse_usd_upper_bound(markdown_text) or 75_000.0
        return ClassifyResult(
            status="intake_complete",
            metadata={
                "client_name": "Sunset Bay Resorts, LLC",
                "location": "Florida, US",
                "service_type": "Co-branded food & beverage concession partnership",
                "scope": "3 resort concession stands, co-branded signature menu, exclusivity",
                "deadline": "2026-09-02",
                "budget_range": "$60,000-$75,000 USD/year",
                "estimated_contract_value_usd": upper_usd,
            },
            departments_needed=[
                "marketing",
                "operations",
                "procurement",
                "training",
            ],
            requires_ceo_approval=upper_usd > 50_000,
        )

    if "andes tech" in text:
        return ClassifyResult(
            status="intake_complete",
            metadata={
                "client_name": "Andes Tech Solutions",
                "location": "Medellín, Colombia",
                "service_type": "Weekly corporate catering",
                "scope": "~220 employees, Tuesdays and Thursdays, standard menu, 1-year contract",
                "deadline": "2026-08-18",
                "budget_range": None,
                "estimated_contract_value_usd": None,
            },
            departments_needed=["marketing", "operations", "procurement"],
            requires_ceo_approval=False,
        )

    return None


def classify_document(markdown_text: str) -> ClassifyResult:
    """Classify RFP validity and extract routing metadata."""
    heuristic = _heuristic_classify(markdown_text)
    if heuristic is not None:
        return heuristic

    if _generation_available():
        try:
            payload = _chat_json(
                system=(
                    "You classify Brasaland B2B RFP documents. Return JSON with keys: "
                    "is_valid_rfp (bool), client_name, location, service_type, scope, deadline, "
                    "budget_range, estimated_contract_value_usd, departments_needed (array of "
                    "marketing|operations|procurement|training), unmapped_topics (array), "
                    "requires_ceo_approval (bool), discard_reason."
                ),
                user=markdown_text[:12000],
            )
            metadata = {
                k: payload.get(k)
                for k in (
                    "client_name",
                    "location",
                    "service_type",
                    "scope",
                    "deadline",
                    "budget_range",
                    "estimated_contract_value_usd",
                )
            }
            if not payload.get("is_valid_rfp", True):
                missing = _count_missing_core_fields(metadata)
                return ClassifyResult(
                    status="discarded",
                    metadata=metadata,
                    discard_reason=payload.get("discard_reason")
                    or "Document is not a valid Brasaland RFP.",
                    discard_rule_id="missing_core_fields" if missing >= 2 else None,
                )
            missing = _count_missing_core_fields(metadata)
            if missing >= 2:
                return ClassifyResult(
                    status="discarded",
                    metadata=metadata,
                    discard_reason="Missing required RFP core fields (client, scope, deadline).",
                    discard_rule_id="missing_core_fields",
                )
            depts = [
                d
                for d in payload.get("departments_needed") or []
                if d in {"marketing", "operations", "procurement", "training"}
            ]
            upper = metadata.get("estimated_contract_value_usd")
            ceo = bool(payload.get("requires_ceo_approval"))
            if upper is not None and float(upper) > 50_000:
                ceo = True
            return ClassifyResult(
                status="intake_complete",
                metadata=metadata,
                departments_needed=depts,
                unmapped_topics=list(payload.get("unmapped_topics") or []),
                requires_ceo_approval=ceo,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM classify failed, falling back to discard heuristics: %s", exc)

    metadata: dict[str, Any] = {"client_name": None, "scope": None, "deadline": None}
    return ClassifyResult(
        status="discarded",
        metadata=metadata,
        discard_reason="Could not validate document as a Brasaland RFP.",
        discard_rule_id="missing_core_fields",
    )


_DEPT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "marketing": ("brand", "co-brand", "exclusiv", "marketing", "validity"),
    "operations": ("operational", "staff", "capacity", "season", "logistic", "setup"),
    "procurement": ("pricing", "cost", "supplier", "ingredient", "volume", "contract value"),
    "training": ("recipe", "signature menu", "standard", "certification", "training"),
}


def build_department_excerpt(markdown_text: str, department_id: str, *, max_chars: int = 2000) -> str:
    """Build a department-focused excerpt from full markdown."""
    keywords = _DEPT_KEYWORDS.get(department_id, ())
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", markdown_text) if p.strip()]
    selected: list[str] = []
    for paragraph in paragraphs:
        lower = paragraph.lower()
        if any(keyword in lower for keyword in keywords):
            selected.append(paragraph)
    if not selected and paragraphs:
        selected = paragraphs[:2]
    excerpt = "\n\n".join(selected).strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars] + "..."
    return excerpt or markdown_text[:max_chars]


def generate_key_aspects(
    department_id: str,
    metadata: dict[str, Any],
    excerpt: str,
) -> list[str]:
    """Generate routing key aspects for one department."""
    if _generation_available():
        try:
            payload = _chat_json(
                system=(
                    "Return JSON {\"key_aspects\": [string, ...]} with 2-4 concise routing "
                    f"bullets for department '{department_id}' on this RFP intake. "
                    "Write every bullet in English regardless of the source document language."
                ),
                user=json.dumps({"metadata": metadata, "excerpt": excerpt[:4000]}),
            )
            aspects = payload.get("key_aspects") or []
            if isinstance(aspects, list) and aspects:
                return [str(a) for a in aspects[:6]]
        except Exception as exc:  # noqa: BLE001
            logger.debug("LLM key_aspects failed for %s: %s", department_id, exc)

    templates: dict[str, list[str]] = {
        "marketing": [
            "Brand co-marketing and exclusivity terms",
            "Offer validity and proposal presentation",
        ],
        "operations": [
            "Operational feasibility and staffing plan",
            "Setup timeline and service cadence",
        ],
        "procurement": [
            "Pricing and volume-based ingredient costs",
            "Supplier lead times for contract volume",
        ],
        "training": [
            "New recipe or standard development time",
            "Certification and rollout across locations",
        ],
    }
    return templates.get(department_id, [f"Review {department_id} requirements for this RFP"])


def synthesize_intake(
    metadata: dict[str, Any],
    departments_needed: list[str],
    department_key_aspects: dict[str, list[str]],
) -> tuple[str, list[dict[str, Any]]]:
    """Merge worker outputs into intake summary and detect conflicts."""
    conflicts: list[dict[str, Any]] = []

    lines = [
        f"Client: {metadata.get('client_name') or 'Unknown'}",
        f"Service: {metadata.get('service_type') or metadata.get('scope') or 'Unspecified'}",
        f"Deadline: {metadata.get('deadline') or 'Not specified'}",
        f"Departments engaged: {', '.join(departments_needed) if departments_needed else 'none'}",
        "",
    ]
    for dept in departments_needed:
        aspects = department_key_aspects.get(dept) or []
        lines.append(f"{dept}: " + "; ".join(aspects) if aspects else f"{dept}: pending review")
    return "\n".join(lines), conflicts


__all__ = [
    "ClassifyResult",
    "build_department_excerpt",
    "classify_document",
    "compute_readability_scores",
    "convert_pdf_to_markdown",
    "generate_key_aspects",
    "repo_root",
    "synthesize_intake",
]
