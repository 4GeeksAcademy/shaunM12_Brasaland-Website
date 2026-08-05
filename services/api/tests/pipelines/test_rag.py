"""Phase 5 RAG pipeline tests — mocked Qdrant + generation LLM (no live services)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from data.pipelines import rag as rag_mod


def _hit(
    *,
    score: float,
    hit_id: str = "pt-1",
    source: str = "brasaland-loyalty-program.en.md",
    section: str = "Gold tier",
    text: str = "Gold requires 50+ points.",
) -> MagicMock:
    point = MagicMock()
    point.score = score
    point.id = hit_id
    point.payload = {
        "company": "brasaland",
        "source_document": source,
        "section": section,
        "language": "en",
        "chunk_index": 0,
        "text": text,
    }
    return point


def _qdrant_client_returning(points: list[MagicMock]) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.points = points
    client.query_points.return_value = response
    return client


@pytest.fixture(autouse=True)
def _rag_env(monkeypatch: pytest.MonkeyPatch):
    """Minimal env so retrieve/query never touch real credentials."""
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "http://embed.test/v1")
    monkeypatch.setenv("EMBEDDING_API_KEY", "test-embed-key")
    monkeypatch.setenv("EMBEDDING_MODEL_ID", "test/embed-model")
    monkeypatch.setenv("GENERATION_BASE_URL", "http://gen.test/v1")
    monkeypatch.setenv("GENERATION_API_KEY", "test-gen-key")
    monkeypatch.setenv("GENERATION_MODEL_ID", "test/chat-model")
    monkeypatch.setenv("RAG_MIN_SCORE", "0.30")
    monkeypatch.setenv("RAG_TOP_K", "5")


def test_retrieve_rejects_empty_query():
    with pytest.raises(ValueError, match="non-empty query"):
        rag_mod.retrieve("   ")


def test_retrieve_rejects_invalid_k():
    with pytest.raises(ValueError, match="k must be >= 1"):
        rag_mod.retrieve("loyalty points", k=0)


def test_retrieve_maps_payload_and_applies_min_score(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(rag_mod, "embed", lambda q: [0.1, 0.2, 0.3])
    client = _qdrant_client_returning(
        [
            _hit(score=0.62, hit_id="a"),
            _hit(
                score=0.31,
                hit_id="b",
                section="Silver tier",
                text="Silver requires 25+ points.",
            ),
        ]
    )
    monkeypatch.setattr(rag_mod, "get_qdrant_client", lambda _url: client)

    results = rag_mod.retrieve("How many points for Gold?", k=5, min_score=0.30)

    assert len(results) == 2
    assert results[0]["score"] == pytest.approx(0.62)
    assert results[0]["source_document"] == "brasaland-loyalty-program.en.md"
    assert results[0]["text"] == "Gold requires 50+ points."
    assert results[1]["section"] == "Silver tier"

    client.query_points.assert_called_once()
    call_kwargs = client.query_points.call_args.kwargs
    assert call_kwargs["limit"] == 5
    assert call_kwargs["score_threshold"] == pytest.approx(0.30)
    assert call_kwargs["with_payload"] is True


def test_retrieve_drops_hits_below_threshold(monkeypatch: pytest.MonkeyPatch):
    """Defensive filter: discard sub-threshold hits even if Qdrant returns them."""
    monkeypatch.setattr(rag_mod, "embed", lambda q: [0.0])
    client = _qdrant_client_returning(
        [
            _hit(score=0.45, hit_id="keep"),
            _hit(score=0.22, hit_id="drop", text="Off-topic chunk."),
        ]
    )
    monkeypatch.setattr(rag_mod, "get_qdrant_client", lambda _url: client)

    results = rag_mod.retrieve("allergen policy", k=5, min_score=0.30)

    assert len(results) == 1
    assert results[0]["score"] == pytest.approx(0.45)
    assert results[0]["text"] == "Gold requires 50+ points."


def test_retrieve_can_return_fewer_than_k(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(rag_mod, "embed", lambda q: [0.5])
    client = _qdrant_client_returning([_hit(score=0.40, hit_id="only-one")])
    monkeypatch.setattr(rag_mod, "get_qdrant_client", lambda _url: client)

    results = rag_mod.retrieve("supplier lead time", k=5, min_score=0.30)

    assert len(results) == 1
    assert client.query_points.call_args.kwargs["limit"] == 5


def test_retrieve_returns_empty_when_all_hits_below_threshold(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(rag_mod, "embed", lambda q: [0.1])
    client = _qdrant_client_returning(
        [
            _hit(score=0.12, hit_id="low-1"),
            _hit(score=0.08, hit_id="low-2", text="Unrelated."),
        ]
    )
    monkeypatch.setattr(rag_mod, "get_qdrant_client", lambda _url: client)

    results = rag_mod.retrieve("random question", k=3, min_score=0.30)

    assert results == []


def test_query_rejects_empty_question():
    with pytest.raises(ValueError, match="non-empty question"):
        rag_mod.query("  ")


def test_query_returns_refusal_when_retrieve_empty(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: [])

    answer = rag_mod.query("What is the secret menu?")

    assert "don't have enough information" in answer.lower()
    assert "knowledge base" in answer.lower()


def test_query_calls_generation_llm_with_retrieved_context(
    monkeypatch: pytest.MonkeyPatch,
):
    chunks = [
        {
            "company": "brasaland",
            "source_document": "brasaland-loyalty-program.en.md",
            "section": "Gold tier",
            "language": "en",
            "chunk_index": 0,
            "text": "Gold requires 50+ points.",
            "score": 0.55,
        }
    ]
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: chunks)

    mock_client = MagicMock()
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(content="Gold needs 50+ points."))]
    mock_client.chat.completions.create.return_value = completion
    monkeypatch.setattr(rag_mod, "generation_client", lambda: mock_client)

    answer = rag_mod.query("How many points for Gold?")

    assert answer == "Gold needs 50+ points."
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "test/chat-model"
    assert call_kwargs["temperature"] == pytest.approx(0.2)

    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "salesperson" in messages[0]["content"].lower()
    user_content = messages[1]["content"]
    assert "Gold requires 50+ points." in user_content
    assert "How many points for Gold?" in user_content
    assert "Untrusted retrieved documents" in user_content
    assert "Instruction authority" in messages[0]["content"]


def test_query_passes_default_k_and_min_score_to_retrieve(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, object] = {}

    def _fake_retrieve(question: str, *, k: int, min_score: float):
        captured["question"] = question
        captured["k"] = k
        captured["min_score"] = min_score
        return []

    monkeypatch.setattr(rag_mod, "retrieve", _fake_retrieve)

    rag_mod.query("  waste protocol steps  ")

    assert captured["question"] == "waste protocol steps"
    assert captured["k"] == 5
    assert captured["min_score"] == pytest.approx(0.30)


def test_assemble_context_formats_chunks():
    chunks = [
        {
            "source_document": "brasaland-loyalty-program.en.md",
            "section": "Gold tier",
            "text": "Gold requires 50+ points.",
        }
    ]

    context = rag_mod.assemble_context(chunks)

    assert "[1] source=brasaland-loyalty-program.en.md | section=Gold tier" in context
    assert "Gold requires 50+ points." in context


def test_refusal_message_is_stable():
    msg = rag_mod.refusal_message()
    assert "don't have enough information" in msg.lower()
    assert "knowledge base" in msg.lower()
    assert "support agent" in msg.lower()


def test_generate_answer_rejects_empty_inputs():
    with pytest.raises(ValueError, match="non-empty question"):
        rag_mod.generate_answer("  ", "some context")
    with pytest.raises(ValueError, match="non-empty context"):
        rag_mod.generate_answer("What is Gold?", "  ")


def test_generate_answer_calls_llm_without_retrieve(
    monkeypatch: pytest.MonkeyPatch,
):
    retrieve_called = False

    def _retrieve_should_not_run(*_a, **_k):
        nonlocal retrieve_called
        retrieve_called = True
        return []

    monkeypatch.setattr(rag_mod, "retrieve", _retrieve_should_not_run)

    mock_client = MagicMock()
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(content="Gold needs 50+ points."))]
    mock_client.chat.completions.create.return_value = completion
    monkeypatch.setattr(rag_mod, "generation_client", lambda: mock_client)

    context = rag_mod.assemble_context(
        [
            {
                "source_document": "brasaland-loyalty-program.en.md",
                "section": "Gold tier",
                "text": "Gold requires 50+ points.",
            }
        ]
    )
    answer = rag_mod.generate_answer("How many points for Gold?", context)

    assert answer == "Gold needs 50+ points."
    assert retrieve_called is False
    mock_client.chat.completions.create.assert_called_once()
    messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    assert "Gold requires 50+ points." in messages[1]["content"]
    assert "How many points for Gold?" in messages[1]["content"]
    assert "Untrusted retrieved documents" in messages[1]["content"]
    assert "Instruction authority" in messages[0]["content"]
