"""Support Agent generation — tool + RAG context (P2-L35, P24-OPT-J)."""

from __future__ import annotations

import asyncio
from typing import Any

from data.pipelines.rag import _generation_settings, _load_env, generation_client
from agent.guardrails.prompts import (
    SUPPORT_SYSTEM_PROMPT,
    build_support_user_prompt,
    support_system_prompt,
)
from agent.guardrails.sanitize import (
    is_sanitized_rag_context,
    sanitize_rag_context,
    sanitize_tool_context_block,
    sanitize_tool_envelope,
)
from packages.shared.restaurant_locations import format_location_label

MAX_TOOL_ROWS = 10


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
    for raw_envelope in tool_results:
        envelope = sanitize_tool_envelope(raw_envelope)
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
    formatted = "\n\n".join(parts).strip()
    if not formatted:
        return ""
    return sanitize_tool_context_block(formatted)


def build_combined_context(
    *,
    rag_context: str = "",
    tool_results: list[dict[str, Any]] | None = None,
    caveat: str | None = None,
    memory_context: str = "",
) -> str:
    """Merge tool operational data, optional memory, and RAG context."""
    parts: list[str] = []
    if caveat and caveat.strip():
        parts.append(caveat.strip())
    tool_block = build_tool_context(tool_results)
    if tool_block:
        parts.append(tool_block)
    memory_block = (memory_context or "").strip()
    if memory_block:
        parts.append(
            "## Approved operational memory (user-confirmed; may differ from official KB)\n"
            f"{memory_block}"
        )
    rag_block = rag_context.strip()
    if rag_block and not is_sanitized_rag_context(rag_block):
        rag_block = sanitize_rag_context(rag_block)
    if rag_block:
        parts.append(f"## Knowledge base\n{rag_block}")
    return "\n\n".join(parts).strip()


def _invoke_structured_completion(*, system_prompt: str, user_prompt: str) -> str:
    _load_env()
    _, _, model_id = _generation_settings()
    client = generation_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
    except TypeError:
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.2,
        )
    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise RuntimeError("Generation model returned an empty answer")
    return content


def _scoped_location_for_question(question: str) -> int | None:
    from agent.memory.location_hint import resolve_injection_scope

    return resolve_injection_scope(question).resolved_id


def generate_structured_support_response(
    question: str,
    *,
    rag_context: str = "",
    tool_results: list[dict[str, Any]] | None = None,
    caveat: str | None = None,
    memory_context: str = "",
    pending_proposal_active: bool = False,
):
    """Generate JSON ``{ answer, memory_proposal }`` for tool/RAG paths (P26-L8, P26-L12)."""
    from agent.memory.correction_intent import user_wants_memory_proposal
    from agent.memory.schemas import GenerationResult
    from agent.memory.structured_generation import build_generation_result
    from agent.guardrails.prompts import build_support_user_prompt, support_system_prompt_with_memory

    if not question or not question.strip():
        raise ValueError("generate_structured_support_response() requires a non-empty question")

    context = build_combined_context(
        rag_context=rag_context,
        tool_results=tool_results,
        caveat=caveat,
        memory_context=memory_context,
    )
    if not context:
        raise ValueError("generate_structured_support_response() requires non-empty combined context")

    user_prompt = build_support_user_prompt(
        question=question.strip(),
        context=context,
        memory_context="",
        scoped_location_id=_scoped_location_for_question(question),
    )
    raw = _invoke_structured_completion(
        system_prompt=support_system_prompt_with_memory(),
        user_prompt=user_prompt,
    )
    return build_generation_result(
        raw,
        allow_proposal=not pending_proposal_active and user_wants_memory_proposal(question),
        question=question.strip(),
    )


def generate_structured_rag_response(
    question: str,
    rag_context: str,
    *,
    memory_context: str = "",
    pending_proposal_active: bool = False,
):
    """Structured generation for pure RAG path — Knowledge ``generate_answer`` unchanged (P26-L8)."""
    from agent.memory.correction_intent import user_wants_memory_proposal
    from agent.memory.schemas import GenerationResult
    from agent.memory.structured_generation import build_generation_result
    from agent.guardrails.prompts import build_support_user_prompt, support_system_prompt_with_memory

    if not question or not question.strip():
        raise ValueError("generate_structured_rag_response() requires a non-empty question")
    if not rag_context or not rag_context.strip():
        raise ValueError("generate_structured_rag_response() requires non-empty context")

    rag_block = rag_context.strip()
    if not is_sanitized_rag_context(rag_block):
        rag_block = sanitize_rag_context(rag_block)

    combined = f"## Knowledge base\n{rag_block}"
    user_prompt = build_support_user_prompt(
        question=question.strip(),
        context=combined,
        memory_context=memory_context,
        scoped_location_id=_scoped_location_for_question(question),
    )
    raw = _invoke_structured_completion(
        system_prompt=support_system_prompt_with_memory(),
        user_prompt=user_prompt,
    )
    return build_generation_result(
        raw,
        allow_proposal=not pending_proposal_active and user_wants_memory_proposal(question),
        question=question.strip(),
    )


MEMORY_CORRECTION_CONTEXT = (
    "No knowledge-base sections matched this question. "
    "The user may be sharing a recurring local operational correction for a Brasaland location. "
    "If they ask you to remember a local practice or exception, propose memory even when "
    "a general policy might sound similar — local confirmations are stored per location_id."
)


def generate_structured_memory_correction_response(
    question: str,
    *,
    memory_context: str = "",
    pending_proposal_active: bool = False,
):
    """Structured generation when retrieval is empty but the user offers a local correction."""
    from agent.memory.correction_intent import user_wants_memory_proposal
    from agent.memory.structured_generation import build_generation_result
    from agent.guardrails.prompts import build_support_user_prompt, support_system_prompt_with_memory

    if not question or not question.strip():
        raise ValueError(
            "generate_structured_memory_correction_response() requires a non-empty question"
        )

    combined = f"## Knowledge base\n{MEMORY_CORRECTION_CONTEXT}"
    user_prompt = build_support_user_prompt(
        question=question.strip(),
        context=combined,
        memory_context=memory_context,
        scoped_location_id=_scoped_location_for_question(question),
    )
    raw = _invoke_structured_completion(
        system_prompt=support_system_prompt_with_memory(),
        user_prompt=user_prompt,
    )
    return build_generation_result(
        raw,
        allow_proposal=not pending_proposal_active and user_wants_memory_proposal(question),
        question=question.strip(),
    )


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
    user_prompt = build_support_user_prompt(
        question=cleaned_question,
        context=context,
    )

    _, _, model_id = _generation_settings()
    client = generation_client()
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": support_system_prompt()},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    answer = (response.choices[0].message.content or "").strip()
    if not answer:
        raise RuntimeError("Generation model returned an empty answer")
    return answer


def knowledge_system_prompt_for_tests() -> str:
    """Knowledge API system prompt — for tests comparing prompt separation."""
    from data.pipelines.prompt_security import knowledge_system_prompt

    return knowledge_system_prompt()


def chunk_text_for_streaming(text: str) -> list[str]:
    """Split visible answer text into word-sized stream tokens."""
    import re

    cleaned = text or ""
    if not cleaned:
        return []
    tokens = re.findall(r"\S+\s*", cleaned)
    return tokens or [cleaned]


def _stream_completion_tokens_sync(*, system_prompt: str, user_prompt: str):
    """Yield raw LLM deltas with ``stream=True`` (sync iterator for thread offload)."""
    _load_env()
    _, _, model_id = _generation_settings()
    client = generation_client()
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        stream=True,
    )
    for chunk in response:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta


async def iter_llm_completion_tokens(*, question: str, graph_state: dict[str, Any]):
    """Stream visible answer text when graph returned no final ``answer`` (WS fallback path)."""
    rag_context = graph_state.get("context_text") or ""
    tool_results = graph_state.get("tool_results")
    memory_context = graph_state.get("memory_context") or ""
    context = build_combined_context(
        rag_context=rag_context,
        tool_results=tool_results,
        memory_context=memory_context,
    )
    if not context:
        for token in chunk_text_for_streaming(
            "I couldn't find enough context to answer that yet. Try rephrasing your question."
        ):
            yield token
            await asyncio.sleep(0)
        return

    user_prompt = build_support_user_prompt(
        question=question.strip(),
        context=context,
        memory_context=memory_context,
        scoped_location_id=_scoped_location_for_question(question),
    )

    def _produce_tokens():
        return list(
            _stream_completion_tokens_sync(
                system_prompt=support_system_prompt(),
                user_prompt=user_prompt,
            )
        )

    tokens = await asyncio.to_thread(_produce_tokens)
    for token in tokens:
        yield token
        await asyncio.sleep(0)
