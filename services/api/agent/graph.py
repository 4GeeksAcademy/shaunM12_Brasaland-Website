"""Support Agent LangGraph — nodes, conditional edges, SQLite checkpointer."""

from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from knowledge.bootstrap import ensure_repo_root_on_path

from .state import AgentState, initial_state

logger = logging.getLogger(__name__)

RouteAfterIntake = Literal["error", "retrieve"]
RouteAfterRetrieve = Literal["refuse", "generate"]

_EMPTY_QUESTION_ANSWER = (
    "Please enter a question so the Support Agent can look it up in Brasaland's "
    "knowledge base."
)


def _default_min_score() -> float:
    raw = os.getenv("RAG_MIN_SCORE", "").strip()
    if not raw:
        return 0.30
    return float(raw)


def checkpoint_db_path() -> Path:
    """Resolve SQLite checkpoint file (``AGENT_CHECKPOINT_DB_PATH`` under repo root)."""
    raw = os.getenv("AGENT_CHECKPOINT_DB_PATH", "data/agent/checkpoints.db").strip()
    path = Path(raw)
    if path.is_absolute():
        return path
    repo_root = ensure_repo_root_on_path()
    return (repo_root / path).resolve()


def _trace(node: str, **fields: Any) -> list[dict[str, Any]]:
    return [{"node": node, **fields}]


def intake_node(state: AgentState) -> dict[str, Any]:
    question = (state.get("question") or "").strip()
    if not question:
        return {
            "route": "error",
            "error": "empty question",
            "answer": _EMPTY_QUESTION_ANSWER,
            "trace_events": _trace("intake", valid=False),
        }
    return {
        "question": question,
        "route": "retrieve",
        "trace_events": _trace("intake", valid=True),
    }


def retrieve_node(state: AgentState) -> dict[str, Any]:
    ensure_repo_root_on_path()
    from data.pipelines.rag import assemble_context, retrieve

    min_score = _default_min_score()
    chunks = retrieve(state["question"], min_score=min_score)
    context_text = assemble_context(chunks) if chunks else ""
    return {
        "chunks": chunks,
        "context_text": context_text,
        "trace_events": _trace(
            "retrieve",
            chunk_count=len(chunks),
            min_score=min_score,
        ),
    }


def generate_node(state: AgentState) -> dict[str, Any]:
    ensure_repo_root_on_path()
    from data.pipelines.rag import generate_answer

    answer = generate_answer(state["question"], state["context_text"])
    return {
        "answer": answer,
        "route": "generate",
        "trace_events": _trace("generate", grounded=True),
    }


def refuse_node(state: AgentState) -> dict[str, Any]:
    ensure_repo_root_on_path()
    from data.pipelines.rag import refusal_message

    return {
        "answer": refusal_message(),
        "route": "refuse",
        "trace_events": _trace("refuse", reason="empty_retrieval"),
    }


def error_node(state: AgentState) -> dict[str, Any]:
    return {
        "answer": state.get("answer") or _EMPTY_QUESTION_ANSWER,
        "route": "error",
        "error": state.get("error") or "empty question",
        "trace_events": _trace("error", reason=state.get("error") or "empty question"),
    }


def route_after_intake(state: AgentState) -> RouteAfterIntake:
    if state.get("route") == "error":
        return "error"
    return "retrieve"


def route_after_retrieve(state: AgentState) -> RouteAfterRetrieve:
    if not state.get("chunks"):
        return "refuse"
    return "generate"


def build_graph() -> StateGraph:
    """Construct the uncompiled Support Agent graph."""
    builder: StateGraph = StateGraph(AgentState)
    builder.add_node("intake", intake_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("generate", generate_node)
    builder.add_node("refuse", refuse_node)
    builder.add_node("error", error_node)

    builder.add_edge(START, "intake")
    builder.add_conditional_edges(
        "intake",
        route_after_intake,
        {"error": "error", "retrieve": "retrieve"},
    )
    builder.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {"refuse": "refuse", "generate": "generate"},
    )
    builder.add_edge("error", END)
    builder.add_edge("refuse", END)
    builder.add_edge("generate", END)
    return builder


@lru_cache(maxsize=1)
def _sqlite_checkpointer() -> SqliteSaver:
    db_path = checkpoint_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    logger.info("Support Agent checkpointer using %s", db_path)
    return SqliteSaver(conn)


@lru_cache(maxsize=1)
def get_compiled_graph():
    """Return the compiled graph with SQLite checkpointing (singleton)."""
    return build_graph().compile(checkpointer=_sqlite_checkpointer())


def invoke_support_agent(
    question: str,
    *,
    thread_id: str | None = None,
) -> AgentState:
    """Run the Support Agent graph synchronously and return final state."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}}
    return graph.invoke(initial_state(question), config)
