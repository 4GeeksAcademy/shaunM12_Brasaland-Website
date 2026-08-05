"""Brasaland RAG retrieval + generation — Phase 2 (context-21); Phase 0 split (context-23).

Public functions:
  - ``retrieve(query, *, k, min_score)`` — embed query, search Qdrant, threshold filter
  - ``assemble_context(chunks)`` — format chunk payloads for the generation prompt
  - ``refusal_message()`` — honest refusal when retrieval is empty
  - ``generate_answer(question, context)`` — generation LLM only (no retrieve)
  - ``query(question)`` — thin wrapper: retrieve → generate_answer (Knowledge API)

Does not return raw Qdrant objects to callers of ``query()``.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from openai import OpenAI

from data.process.rag import (
    _collection_name,
    _load_env,
    _qdrant_url,
    embed,
    get_qdrant_client,
)
from data.pipelines.prompt_security import (
    SYSTEM_PROMPT,
    build_knowledge_user_prompt,
    knowledge_system_prompt,
)

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5
# Tuned for pplx-embed cosine scores on this corpus (context-21 L6).
DEFAULT_MIN_SCORE = 0.30


def _default_min_score() -> float:
    raw = os.getenv("RAG_MIN_SCORE", "").strip()
    if not raw:
        return DEFAULT_MIN_SCORE
    return float(raw)


def _default_top_k() -> int:
    raw = os.getenv("RAG_TOP_K", "").strip()
    if not raw:
        return DEFAULT_TOP_K
    return int(raw)


def _generation_settings() -> tuple[str, str, str]:
    """Dedicated generation client settings (L8) — never the embeddings model."""
    _load_env()
    base_url = os.getenv("GENERATION_BASE_URL", "").strip()
    api_key = os.getenv("GENERATION_API_KEY", "").strip()
    model_id = os.getenv("GENERATION_MODEL_ID", "").strip()

    # Same 4Geeks gateway often serves both; allow mirroring base/key only.
    if not base_url:
        base_url = os.getenv("EMBEDDING_BASE_URL", "").strip()
    if not api_key:
        api_key = os.getenv("EMBEDDING_API_KEY", "").strip() or "not-needed"

    if not base_url or not model_id:
        raise RuntimeError(
            "GENERATION_BASE_URL (or EMBEDDING_BASE_URL) and GENERATION_MODEL_ID "
            "must be set for generate_answer() / query(). Use a chat/completion "
            "model — not the embeddings model."
        )

    embedding_id = os.getenv("EMBEDDING_MODEL_ID", "").strip()
    if embedding_id and embedding_id == model_id:
        raise RuntimeError(
            "GENERATION_MODEL_ID must differ from EMBEDDING_MODEL_ID (context-21 L8)."
        )
    return base_url, api_key, model_id


def generation_client() -> OpenAI:
    """Dedicated chat/completion client wrapper (L8) — not for embeddings."""
    base_url, api_key, _ = _generation_settings()
    return OpenAI(base_url=base_url, api_key=api_key)


def retrieve(
    query: str,
    *,
    k: int = DEFAULT_TOP_K,
    min_score: float | None = None,
) -> list[dict[str, Any]]:
    """Embed ``query``, search Qdrant top-k, drop hits below ``min_score``.

    Returns payload dicts plus ``score`` (L10). Never returns raw Qdrant SDK objects.
    May return fewer than ``k`` results (or zero).
    """
    if not query or not query.strip():
        raise ValueError("retrieve() requires a non-empty query")

    _load_env()
    threshold = _default_min_score() if min_score is None else float(min_score)
    top_k = int(k) if k is not None else _default_top_k()
    if top_k < 1:
        raise ValueError("k must be >= 1")

    vector = embed(query.strip())
    client = get_qdrant_client(_qdrant_url())
    response = client.query_points(
        collection_name=_collection_name(),
        query=vector,
        limit=top_k,
        score_threshold=threshold,
        with_payload=True,
    )
    hits = response.points

    results: list[dict[str, Any]] = []
    for hit in hits:
        score = float(hit.score) if hit.score is not None else 0.0
        if score < threshold:
            logger.debug(
                "Dropping hit score=%.4f < min_score=%.4f id=%s",
                score,
                threshold,
                hit.id,
            )
            continue
        payload = dict(hit.payload or {})
        results.append(
            {
                "company": payload.get("company"),
                "source_document": payload.get("source_document"),
                "section": payload.get("section"),
                "language": payload.get("language"),
                "chunk_index": payload.get("chunk_index"),
                "text": payload.get("text"),
                "score": score,
            }
        )

    logger.info(
        "retrieve(%r) → %s/%s hits above min_score=%.3f",
        query[:60],
        len(results),
        top_k,
        threshold,
    )
    return results


def assemble_context(chunks: list[dict[str, Any]]) -> str:
    """Format retrieved chunk payloads for ``generate_answer()`` / graph generate node."""
    blocks: list[str] = []
    for i, ch in enumerate(chunks, start=1):
        source = ch.get("source_document") or "unknown"
        section = ch.get("section") or "unknown"
        text = (ch.get("text") or "").strip()
        blocks.append(f"[{i}] source={source} | section={section}\n{text}")
    return "\n\n".join(blocks)


def refusal_message() -> str:
    """Honest refusal when no chunk clears ``min_score`` (context-21 S5, P25-L4c)."""
    return (
        "I don't have enough information in Brasaland's official knowledge base "
        "to answer that reliably. Please rephrase, or check the loyalty, allergen, "
        "waste, or supplier manuals with a manager."
        "\n\nI'm Brasaland's Support Agent — what can I help you with for operations support?"
    )


def generate_answer(question: str, context: str) -> str:
    """Generate an answer from pre-retrieved context — does not call ``retrieve()``.

    Used by the LangGraph generate node (context-23). ``query()`` delegates here
    after retrieval for backward-compatible Knowledge API behavior.
    """
    if not question or not question.strip():
        raise ValueError("generate_answer() requires a non-empty question")
    if not context or not context.strip():
        raise ValueError("generate_answer() requires non-empty context")

    _load_env()
    cleaned_question = question.strip()
    user_prompt = build_knowledge_user_prompt(
        question=cleaned_question,
        context=context,
    )

    _, _, model_id = _generation_settings()
    client = generation_client()
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": knowledge_system_prompt()},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    answer = (response.choices[0].message.content or "").strip()
    if not answer:
        raise RuntimeError("Generation model returned an empty answer")
    return answer


def query(question: str) -> str:
    """Retrieve → ``generate_answer()`` — backward-compatible Knowledge API entry point."""
    if not question or not question.strip():
        raise ValueError("query() requires a non-empty question")

    _load_env()
    chunks = retrieve(
        question.strip(),
        k=_default_top_k(),
        min_score=_default_min_score(),
    )

    if not chunks:
        logger.info("query() empty retrieval — returning honest refusal")
        return refusal_message()

    return generate_answer(question, assemble_context(chunks))
