"""Support Agent generation — tool + RAG context (P2-L35, P24-OPT-J)."""

from __future__ import annotations

from typing import Any

from data.pipelines.rag import SYSTEM_PROMPT, _generation_settings, _load_env, generation_client
from packages.shared.restaurant_locations import format_location_label

MAX_TOOL_ROWS = 10

SUPPORT_SYSTEM_PROMPT = """You are a Brasaland Support Agent helping backoffice operations staff.
Use live operational data for current incidents, inventory, and stock facts.
When operational data includes filters or a location scope, state that scope in your first sentence.
Use knowledge base sections for policies, loyalty, allergens, and procedures.
If a source is missing or insufficient, say so clearly — do not invent incident IDs, stock levels, or policies.
Keep USD and COP amounts exactly as written in the context; do not convert currencies.
Answer in English, clearly and professionally.
Do not mention tools, HTTP APIs, vector search, chunks, or that you are an AI."""


def _scope_header_for_envelope(envelope: dict[str, Any]) -> str:
    source = envelope.get("source", "tool")
    filters = envelope.get("filters") or {}

    if source == "incidents_api":
        if envelope.get("action") == "summary" or envelope.get("summary"):
            return "scope=incident_summary"
        filter_bits = [f"{key}={value}" for key, value in sorted(filters.items()) if value]
        if filter_bits:
            return f"scope=incidents filters={', '.join(filter_bits)}"
        incident_id = envelope.get("incident_id")
        if incident_id is not None:
            return f"scope=incident_id={incident_id}"
        return "scope=incidents"

    if source == "inventory_api":
        location_id = filters.get("location_id")
        if location_id is not None:
            return f"scope=location_id={location_id} ({format_location_label(int(location_id))})"
        return "scope=inventory"

    return f"scope={source}"


def _cap_rows(rows: list[dict[str, Any]], envelope: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    if len(rows) <= MAX_TOOL_ROWS:
        return rows, None
    note = (
        f"Showing first {MAX_TOOL_ROWS} of {len(rows)} matching rows; "
        "ask with a narrower filter if you need a specific item."
    )
    return rows[:MAX_TOOL_ROWS], note


def format_inventory_rows(rows: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for row in rows:
        location = row.get("location_id")
        location_suffix = f" location_id={location}" if location is not None else ""
        blocks.append(
            "Product #{id}: {name} (SKU {sku})\n"
            "  current_stock={current_stock} {unit} min_threshold={min_stock_threshold}"
            " category={category} country={country}{location_suffix}".format(
                id=row.get("id", "?"),
                name=row.get("name") or "",
                sku=row.get("sku") or "",
                current_stock=row.get("current_stock", "?"),
                unit=row.get("unit") or "",
                min_stock_threshold=row.get("min_stock_threshold", "?"),
                category=row.get("category") or "",
                country=row.get("country") or "",
                location_suffix=location_suffix,
            )
        )
    return "\n\n".join(blocks)


def format_incident_summary(summary: dict[str, Any]) -> str:
    lines: list[str] = ["Incident summary:"]
    for section, label in (
        ("by_status", "By status"),
        ("by_category", "By category"),
        ("by_origin", "By origin"),
        ("by_branch", "By branch"),
    ):
        bucket = summary.get(section)
        if not isinstance(bucket, dict):
            continue
        entries = [f"{key}={value}" for key, value in bucket.items() if value]
        if entries:
            lines.append(f"{label}: " + ", ".join(entries))
    return "\n".join(lines)


def format_incident_rows(rows: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for row in rows:
        blocks.append(
            "Incident #{id}: {title}\n"
            "  status={status} origin={origin} branch={branch} category={category}\n"
            "  {description}".format(
                id=row.get("id", "?"),
                title=row.get("title") or "",
                status=row.get("status") or "",
                origin=row.get("origin") or "",
                branch=row.get("branch") or "",
                category=row.get("category") or "",
                description=(row.get("description") or "").strip(),
            )
        )
    return "\n\n".join(blocks)


def build_tool_context(tool_results: list[dict[str, Any]] | None) -> str:
    """Build operational context block from successful tool envelopes."""
    if not tool_results:
        return ""
    parts: list[str] = []
    for envelope in tool_results:
        if not envelope.get("ok"):
            continue
        scope_header = _scope_header_for_envelope(envelope)
        summary = envelope.get("summary")
        if isinstance(summary, dict):
            parts.append(f"## Live operational data (incident summary)\n{scope_header}\n")
            parts.append(format_incident_summary(summary))
            continue
        rows = envelope.get("rows") or []
        if not rows:
            continue
        capped_rows, cap_note = _cap_rows(rows, envelope)
        source = envelope.get("source", "tool")
        if source == "incidents_api":
            parts.append(f"## Live operational data (incidents)\n{scope_header}\n")
            parts.append(format_incident_rows(capped_rows))
        elif source == "inventory_api":
            parts.append(f"## Live operational data (inventory)\n{scope_header}\n")
            parts.append(format_inventory_rows(capped_rows))
        else:
            parts.append(f"## Live operational data ({source})\n{scope_header}\n")
            parts.append(str(capped_rows))
        truncated_note = envelope.get("truncated_note")
        if cap_note:
            parts.append(cap_note)
        if truncated_note:
            parts.append(str(truncated_note))
    return "\n\n".join(parts).strip()


def build_combined_context(
    *,
    rag_context: str = "",
    tool_results: list[dict[str, Any]] | None = None,
    caveat: str | None = None,
) -> str:
    """Merge tool operational data and optional RAG context for ``generate_support_answer``."""
    parts: list[str] = []
    if caveat and caveat.strip():
        parts.append(caveat.strip())
    tool_block = build_tool_context(tool_results)
    if tool_block:
        parts.append(tool_block)
    if rag_context and rag_context.strip():
        parts.append(f"## Knowledge base\n{rag_context.strip()}")
    return "\n\n".join(parts).strip()


def generate_support_answer(
    question: str,
    *,
    rag_context: str = "",
    tool_results: list[dict[str, Any]] | None = None,
    caveat: str | None = None,
) -> str:
    """Generate an answer from live tool data and/or RAG context — does not call ``retrieve()``."""
    if not question or not question.strip():
        raise ValueError("generate_support_answer() requires a non-empty question")

    context = build_combined_context(
        rag_context=rag_context,
        tool_results=tool_results,
        caveat=caveat,
    )
    if not context:
        raise ValueError("generate_support_answer() requires non-empty combined context")

    _load_env()
    cleaned_question = question.strip()
    user_prompt = (
        f"Context:\n{context}\n\n"
        f"Support question:\n{cleaned_question}\n\n"
        "Write the answer using operational data for live facts and the knowledge base "
        "for policies and procedures. State clearly when information is missing."
    )

    _, _, model_id = _generation_settings()
    client = generation_client()
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": SUPPORT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    answer = (response.choices[0].message.content or "").strip()
    if not answer:
        raise RuntimeError("Generation model returned an empty answer")
    return answer


def knowledge_system_prompt_for_tests() -> str:
    """Knowledge API system prompt (P1) — for tests comparing prompt separation."""
    return SYSTEM_PROMPT
