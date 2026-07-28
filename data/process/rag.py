"""Brasaland RAG indexing — Phase 1 (context-21).

Public functions:
  - ``embed(text)`` — dedicated embeddings model → vector
  - ``setup()`` — load corpus, chunk, embed, upsert into Qdrant

Idempotency (L2/L13): deterministic UUID5 point IDs + upsert.
Collection recreate only when vector size or distance metric mismatches.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

logger = logging.getLogger(__name__)

# Fixed namespace for deterministic point IDs (L13). Do not change once indexed.
BRASALAND_RAG_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-4789-a012-3456789abcde")

COMPANY = "brasaland"
LANGUAGE = "en"
DISTANCE = qmodels.Distance.COSINE
MAX_SECTION_CHARS = 1000
MIN_CHUNKS_PER_DOC = 3

SOURCE_FILES: dict[str, str] = {
    "brasaland-loyalty-program.en.md": "loyalty-program",
    "brasaland-waste-protocol.en.md": "waste-protocol",
    "brasaland-menu-allergens.en.md": "menu-allergens",
    "brasaland-supplier-ordering.en.md": "supplier-ordering",
}

# Section cues for flat manuals that lack ## / ### headings (L7).
# Match either a lone header line or an inline "Header: rest of paragraph…".
_SECTION_START_RE = re.compile(
    r"^(?P<title>"
    r"Program tiers|"
    r"Frequently asked customer questions|"
    r"Main dishes and their declared allergens|"
    r"Protocol for customer-reported allergies|"
    r"Supplier categories and order frequency|"
    r"Minimum stock rule|"
    r"Daily procedure|"
    r"Common causes of waste accepted without an additional note|"
    r"Causes that require direct escalation to Felipe Guerrero|"
    r"Operational target"
    r"):\s*(?P<rest>.*)$",
    re.IGNORECASE,
)


def _load_env() -> None:
    """Load repo-root ``.env`` if present (same idea as ``services/api/config``)."""
    here = Path(__file__).resolve()
    for root in [here.parent, *here.parents]:
        candidate = root / ".env"
        if candidate.exists():
            load_dotenv(candidate)
            return


def resolve_knowledge_base_dir() -> Path:
    """L9 corpus path resolver (host + Docker)."""
    override = os.getenv("BRASALAND_KNOWLEDGE_BASE_DIR", "").strip()
    if override:
        path = Path(override)
        if path.is_dir():
            return path.resolve()
        raise FileNotFoundError(
            f"BRASALAND_KNOWLEDGE_BASE_DIR is set but not a directory: {override}"
        )

    docker_path = Path("/app/docs/company-knowledge-base")
    if docker_path.is_dir():
        return docker_path.resolve()

    repo_root = Path(__file__).resolve().parents[2]
    local_path = repo_root / "docs" / "company-knowledge-base"
    if local_path.is_dir():
        return local_path.resolve()

    raise FileNotFoundError(
        "Could not resolve company knowledge base directory. Set "
        "BRASALAND_KNOWLEDGE_BASE_DIR or place docs under "
        "docs/company-knowledge-base/."
    )


def _qdrant_url() -> str:
    return os.getenv("QDRANT_URL", "http://127.0.0.1:6333").strip() or (
        "http://127.0.0.1:6333"
    )


def _collection_name() -> str:
    return (
        os.getenv("QDRANT_COLLECTION", "brasaland_knowledge").strip()
        or "brasaland_knowledge"
    )


def _embedding_settings() -> tuple[str, str, str]:
    base_url = os.getenv("EMBEDDING_BASE_URL", "").strip()
    api_key = os.getenv("EMBEDDING_API_KEY", "").strip()
    model_id = os.getenv("EMBEDDING_MODEL_ID", "").strip()
    if not base_url or not model_id:
        raise RuntimeError(
            "EMBEDDING_BASE_URL and EMBEDDING_MODEL_ID must be set (4Geeks "
            "student portal). EMBEDDING_API_KEY is required by the client "
            "(use any non-empty value if the portal does not issue a key)."
        )
    if not api_key:
        api_key = "not-needed"
    generation_id = os.getenv("GENERATION_MODEL_ID", "").strip()
    if generation_id and generation_id == model_id:
        raise RuntimeError(
            "EMBEDDING_MODEL_ID must differ from GENERATION_MODEL_ID "
            "(context-21 L8)."
        )
    return base_url, api_key, model_id


def embed_client() -> OpenAI:
    """Dedicated embeddings client wrapper (L8) — not for generation."""
    base_url, api_key, _ = _embedding_settings()
    return OpenAI(base_url=base_url, api_key=api_key)


def embed(text: str) -> list[float]:
    """Generate a vector for a single text using the embeddings model only."""
    if not text or not text.strip():
        raise ValueError("embed() requires non-empty text")
    _, _, model_id = _embedding_settings()
    client = embed_client()
    response = client.embeddings.create(model=model_id, input=text.strip())
    vector = list(response.data[0].embedding)
    if not vector:
        raise RuntimeError("Embeddings API returned an empty vector")
    return vector


def point_id(source_document: str, chunk_index: int) -> str:
    """Deterministic Qdrant point id (L13)."""
    return str(
        uuid.uuid5(BRASALAND_RAG_NAMESPACE, f"{source_document}:{chunk_index}")
    )


def _split_on_markdown_headings(text: str) -> list[tuple[str, str]]:
    """Split on ## / ### headings. Returns (section_title, body) pairs."""
    lines = text.splitlines()
    sections: list[tuple[str, str]] = []
    current_title = "Introduction"
    current_body: list[str] = []

    heading_re = re.compile(r"^(#{2,3})\s+(.+?)\s*$")

    for line in lines:
        match = heading_re.match(line)
        if match:
            body = "\n".join(current_body).strip()
            if body:
                sections.append((current_title, body))
            current_title = match.group(2).strip()
            current_body = []
            continue
        # Skip a lone H1 from the body title line when collecting intro
        if re.match(r"^#\s+", line) and not current_body and current_title == "Introduction":
            current_title = re.sub(r"^#\s+", "", line).strip() or current_title
            continue
        current_body.append(line)

    body = "\n".join(current_body).strip()
    if body:
        sections.append((current_title, body))
    return sections


def _split_on_semantic_cues(text: str) -> list[tuple[str, str]]:
    """Split flat Brasaland manuals using known section labels + H1 title."""
    lines = text.splitlines()
    doc_title = "Introduction"
    start_idx = 0
    if lines and lines[0].startswith("# "):
        doc_title = lines[0][2:].strip() or doc_title
        start_idx = 1

    sections: list[tuple[str, str]] = []
    current_title = doc_title
    current_body: list[str] = []

    for line in lines[start_idx:]:
        match = _SECTION_START_RE.match(line.strip())
        if match:
            body = "\n".join(current_body).strip()
            if body:
                sections.append((current_title, body))
            current_title = match.group("title").strip()
            rest = (match.group("rest") or "").strip()
            current_body = [rest] if rest else []
            continue
        current_body.append(line)

    body = "\n".join(current_body).strip()
    if body:
        sections.append((current_title, body))

    # Trailing single-paragraph notes after a list section (e.g. BBQ gluten note)
    # stay attached to the previous section — already handled by linear scan.
    return sections if sections else [(doc_title, text.strip())]


def _split_long_section(title: str, body: str) -> list[tuple[str, str]]:
    """If a section exceeds MAX_SECTION_CHARS, split on blank-line paragraphs."""
    if len(body) <= MAX_SECTION_CHARS:
        return [(title, body)]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    if len(paragraphs) <= 1:
        return [(title, body)]

    chunks: list[tuple[str, str]] = []
    buf: list[str] = []
    buf_len = 0
    part = 1
    for para in paragraphs:
        extra = len(para) + (2 if buf else 0)
        if buf and buf_len + extra > MAX_SECTION_CHARS:
            label = title if part == 1 else f"{title} (cont. {part})"
            chunks.append((label, "\n\n".join(buf)))
            part += 1
            buf = [para]
            buf_len = len(para)
        else:
            buf.append(para)
            buf_len += extra
    if buf:
        label = title if part == 1 else f"{title} (cont. {part})"
        chunks.append((label, "\n\n".join(buf)))
    return chunks


def _ensure_min_chunks(
    sections: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    """Guarantee ≥ MIN_CHUNKS_PER_DOC by splitting the largest chunks on paragraphs."""
    chunks = list(sections)
    guard = 0
    while len(chunks) < MIN_CHUNKS_PER_DOC and guard < 20:
        guard += 1
        # Find longest chunk that still has paragraph breaks
        idx = max(range(len(chunks)), key=lambda i: len(chunks[i][1]))
        title, body = chunks[idx]
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        if len(paragraphs) < 2:
            # Fall back to splitting bullet/numbered lines into groups
            lines = [ln for ln in body.splitlines() if ln.strip()]
            if len(lines) < 2:
                break
            mid = max(1, len(lines) // 2)
            left = "\n".join(lines[:mid]).strip()
            right = "\n".join(lines[mid:]).strip()
            if not left or not right:
                break
            chunks.pop(idx)
            chunks.insert(idx, (f"{title} (part 1)", left))
            chunks.insert(idx + 1, (f"{title} (part 2)", right))
            continue

        mid = max(1, len(paragraphs) // 2)
        left = "\n\n".join(paragraphs[:mid]).strip()
        right = "\n\n".join(paragraphs[mid:]).strip()
        chunks.pop(idx)
        chunks.insert(idx, (f"{title} (part 1)", left))
        chunks.insert(idx + 1, (f"{title} (part 2)", right))
    return chunks


def chunk_document(markdown: str) -> list[tuple[str, str]]:
    """Return list of (section_title, chunk_text) semantic units (L7)."""
    text = markdown.strip()
    if not text:
        return []

    if re.search(r"^#{2,3}\s+", text, re.MULTILINE):
        sections = _split_on_markdown_headings(text)
    else:
        sections = _split_on_semantic_cues(text)

    expanded: list[tuple[str, str]] = []
    for title, body in sections:
        expanded.extend(_split_long_section(title, body))

    return _ensure_min_chunks(expanded)


def load_corpus_chunks(
    knowledge_dir: Path | None = None,
) -> list[dict]:
    """Load all source docs and produce chunk dicts ready for embedding."""
    base = knowledge_dir or resolve_knowledge_base_dir()
    chunks: list[dict] = []

    for filename, source_document in SOURCE_FILES.items():
        path = base / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing knowledge base file: {path}")
        markdown = path.read_text(encoding="utf-8")
        parts = chunk_document(markdown)
        if len(parts) < MIN_CHUNKS_PER_DOC:
            raise RuntimeError(
                f"{filename} produced {len(parts)} chunks; need ≥ "
                f"{MIN_CHUNKS_PER_DOC}"
            )
        for chunk_index, (section, body) in enumerate(parts):
            chunks.append(
                {
                    "source_document": source_document,
                    "section": section,
                    "chunk_index": chunk_index,
                    "text": body.strip(),
                    "company": COMPANY,
                    "language": LANGUAGE,
                    "id": point_id(source_document, chunk_index),
                }
            )
    return chunks


def get_qdrant_client(url: str | None = None) -> QdrantClient:
    return QdrantClient(
        url=url or _qdrant_url(),
        check_compatibility=False,
    )


def smoke_qdrant(client: QdrantClient | None = None) -> list[str]:
    """Connectivity smoke: list collection names (Phase 0)."""
    client = client or get_qdrant_client()
    response = client.get_collections()
    return [c.name for c in response.collections]


def _collection_vector_size(client: QdrantClient, name: str) -> int | None:
    if not client.collection_exists(name):
        return None
    info = client.get_collection(name)
    vectors = info.config.params.vectors
    if isinstance(vectors, dict):
        # Named vectors — not used; take first
        first = next(iter(vectors.values()), None)
        return int(first.size) if first is not None else None
    return int(vectors.size) if vectors is not None else None


def ensure_collection(client: QdrantClient, vector_size: int) -> None:
    """Create collection or recreate if dimension/metric drift (L2)."""
    name = _collection_name()
    if client.collection_exists(name):
        existing = _collection_vector_size(client, name)
        if existing == vector_size:
            return
        logger.warning(
            "Recreating collection %s (existing size=%s, needed=%s)",
            name,
            existing,
            vector_size,
        )
        client.delete_collection(name)

    client.create_collection(
        collection_name=name,
        vectors_config=qmodels.VectorParams(size=vector_size, distance=DISTANCE),
    )
    logger.info("Collection %s ready (size=%s, distance=Cosine)", name, vector_size)


def setup(*, dry_run: bool = False) -> int:
    """Index all company knowledge docs into Qdrant. Returns chunks upserted.

    Idempotent: re-running upserts the same deterministic point IDs (L2/L13).
    """
    _load_env()
    chunks = load_corpus_chunks()
    logger.info(
        "Prepared %s chunks from %s documents in %s",
        len(chunks),
        len(SOURCE_FILES),
        resolve_knowledge_base_dir(),
    )

    if dry_run:
        for ch in chunks:
            preview = ch["text"][:80].replace("\n", " ")
            logger.info(
                "[%s #%s] %s — %s…",
                ch["source_document"],
                ch["chunk_index"],
                ch["section"],
                preview,
            )
        return len(chunks)

    # Embed first chunk to learn vector dimension, then ensure collection.
    first_vector = embed(chunks[0]["text"])
    dim = len(first_vector)
    client = get_qdrant_client()
    smoke_qdrant(client)
    ensure_collection(client, dim)

    points: list[qmodels.PointStruct] = []
    for i, ch in enumerate(chunks):
        vector = first_vector if i == 0 else embed(ch["text"])
        if len(vector) != dim:
            raise RuntimeError(
                f"Embedding dimension mismatch: got {len(vector)}, expected {dim}"
            )
        points.append(
            qmodels.PointStruct(
                id=ch["id"],
                vector=vector,
                payload={
                    "company": ch["company"],
                    "source_document": ch["source_document"],
                    "section": ch["section"],
                    "language": ch["language"],
                    "chunk_index": ch["chunk_index"],
                    "text": ch["text"],
                },
            )
        )

    client.upsert(collection_name=_collection_name(), points=points)
    logger.info(
        "Upserted %s points into collection %s",
        len(points),
        _collection_name(),
    )
    return len(points)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Brasaland RAG setup — index docs/company-knowledge-base into Qdrant"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chunk only; do not call embeddings or Qdrant",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Only verify Qdrant connectivity (get_collections)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Debug logging",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    _load_env()

    if args.smoke:
        names = smoke_qdrant()
        print(f"Qdrant OK at {_qdrant_url()} — collections: {names}")
        return 0

    count = setup(dry_run=args.dry_run)
    action = "Prepared" if args.dry_run else "Indexed"
    print(f"{action} {count} chunks into {_collection_name()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
