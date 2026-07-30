"""Support Agent generation — tool + RAG context (P2-L35)."""

from __future__ import annotations

from typing import Any

from data.pipelines.rag import SYSTEM_PROMPT, _generation_settings, _load_env, generation_client

SUPPORT_SYSTEM_PROMPT = """You are a Brasaland Support Agent helping backoffice operations staff.
Use live operational data for current incidents, inventory, and stock facts.
Use knowledge base sections for policies, loyalty, allergens, and procedures.
If a source is missing or insufficient, say so clearly — do not invent incident IDs, stock levels, or policies.
Keep USD and COP amounts exactly as written in the context; do not convert currencies.
Answer in English, clearly and professionally.
Do not mention tools, HTTP APIs, vector search, chunks, or that you are an AI."""


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
        rows = envelope.get("rows") or []
        if not rows:
            continue
        source = envelope.get("source", "tool")
        if source == "incidents_api":
            parts.append("## Live operational data (incidents)\n")
            parts.append(format_incident_rows(rows))
        elif source == "inventory_api":
            parts.append("## Live operational data (inventory)\n")
            parts.append(format_inventory_rows(rows))
        else:
            parts.append(f"## Live operational data ({source})\n")
            parts.append(str(rows))
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
