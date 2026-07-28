"""Brasaland RAG retrieval + generation — Phase 2 (context-21).

Public functions:
  - ``retrieve(query, *, k, min_score)`` — embed query, search Qdrant, threshold filter
  - ``query(question)`` — retrieve → salesperson prompt → generation LLM → answer str

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

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5
# Tuned for pplx-embed cosine scores on this corpus (context-21 L6).
# Observed on-topic tops ~0.32–0.65; off-topic ~0.06. Start was 0.55 (too strict).
DEFAULT_MIN_SCORE = 0.30

SYSTEM_PROMPT = """You are a Brasaland commercial assistant answering like a trained salesperson.
Use ONLY the retrieved context below. Do not invent policies, prices, points, allergens, or procedures.
If the context is missing or insufficient, say clearly that the knowledge base does not have enough information.
Never say there is "zero risk" of cross-contamination or allergens — follow allergen wording in the context literally.
Keep USD and COP amounts exactly as written in the context; do not convert currencies.
Answer in English, confidently and helpfully, from a salesperson's perspective.
Do not mention vector search, chunks, scores, or that you are an AI retrieving documents."""


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
            "must be set for query(). Use a chat/completion model — not the "
            "embeddings model."
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


def _assemble_context(chunks: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for i, ch in enumerate(chunks, start=1):
        source = ch.get("source_document") or "unknown"
        section = ch.get("section") or "unknown"
        text = (ch.get("text") or "").strip()
        blocks.append(f"[{i}] source={source} | section={section}\n{text}")
    return "\n\n".join(blocks)


def _refusal_message() -> str:
    return (
        "I don't have enough information in Brasaland's official knowledge base "
        "to answer that reliably. Please rephrase, or check the loyalty, allergen, "
        "waste, or supplier manuals with a manager."
    )


def query(question: str) -> str:
    """Orchestrate retrieve → prompt assembly → generation LLM → answer string.

    External consumers (API/UI) should call only this function for answers.
    """
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
        return _refusal_message()

    context = _assemble_context(chunks)
    user_prompt = (
        f"Retrieved context:\n{context}\n\n"
        f"Customer / manager question:\n{question.strip()}\n\n"
        "Write the answer using only the retrieved context."
    )

    _, _, model_id = _generation_settings()
    client = generation_client()
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    answer = (response.choices[0].message.content or "").strip()
    if not answer:
        raise RuntimeError("Generation model returned an empty answer")
    return answer
