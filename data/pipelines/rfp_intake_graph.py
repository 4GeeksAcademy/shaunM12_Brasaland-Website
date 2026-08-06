"""RFP intake LangGraph — convert, classify, orchestrate, workers, synthesize (context-27 P1).

Pipeline graph lives under ``data/pipelines/`` (monorepo layout M9-M2). HTTP routes
call ``invoke_rfp_intake`` via ``services/api/rfp/intake_service.py``.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command, Send

from data.pipelines.rfp_generation_graph import add_generation_nodes, set_entry_router
from data.pipelines.rfp_approval_graph import add_approval_nodes
from data.pipelines.rfp_intake import _ensure_repo_root_on_path, repo_root
from data.pipelines.rfp_trace import trace_node

_ensure_repo_root_on_path()

from rfp.constants import (  # noqa: E402
    ERROR_PDF_CONVERSION_FAILED,
    ERROR_PIPELINE_ERROR,
    STATUS_DISCARDED,
    STATUS_FAILED,
    STATUS_INTAKE_COMPLETE,
)
from rfp.state import RfpGraphState, initial_state  # noqa: E402

logger = logging.getLogger(__name__)


def _load_pipeline():
    from data.pipelines import rfp_intake as pipeline

    return pipeline


def checkpoint_db_path() -> Path:
    raw = os.getenv("RFP_CHECKPOINT_DB_PATH", "data/rfp/checkpoints.db").strip()
    path = Path(raw)
    if path.is_absolute():
        return path
    return (repo_root() / path).resolve()


def _convert_pdf_node(state: RfpGraphState) -> dict[str, Any]:
    pipeline = _load_pipeline()
    pdf_path = Path(state["pdf_path"])
    try:
        markdown_text = pipeline.convert_pdf_to_markdown(pdf_path)
        return {
            "markdown_text": markdown_text,
            "trace_events": trace_node(
                "convert_pdf",
                input_data={"pdf_path": str(pdf_path)},
                output_data={"markdown_length": len(markdown_text)},
            ),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("convert_pdf failed for %s", pdf_path)
        return {
            "status": STATUS_FAILED,
            "error_code": ERROR_PDF_CONVERSION_FAILED,
            "error_message": "Could not convert PDF to Markdown.",
            "trace_events": trace_node(
                "convert_pdf",
                input_data={"pdf_path": str(pdf_path)},
                output_data={"ok": False, "error": str(exc)},
            ),
        }


def _readability_node(state: RfpGraphState) -> dict[str, Any]:
    if state.get("status") == STATUS_FAILED:
        return {}
    pipeline = _load_pipeline()
    scores = pipeline.compute_readability_scores(state.get("markdown_text") or "")
    metadata = dict(state.get("metadata") or {})
    metadata["readability_scores"] = scores
    return {
        "readability_scores": scores,
        "metadata": metadata,
        "trace_events": trace_node(
            "readability",
            input_data={"markdown_length": len(state.get("markdown_text") or "")},
            output_data={"scores": scores},
        ),
    }


def _classify_node(state: RfpGraphState) -> dict[str, Any]:
    if state.get("status") == STATUS_FAILED:
        return {}
    pipeline = _load_pipeline()
    result = pipeline.classify_document(state.get("markdown_text") or "")
    metadata = dict(result.metadata)
    if "readability_scores" in state:
        metadata["readability_scores"] = state["readability_scores"]
    trace_fields: dict[str, Any] = {
        "status": result.status,
        "departments_needed": result.departments_needed,
        "requires_ceo_approval": result.requires_ceo_approval,
    }
    if result.status == STATUS_DISCARDED:
        return {
            "status": STATUS_DISCARDED,
            "metadata": metadata,
            "departments_needed": [],
            "unmapped_topics": result.unmapped_topics,
            "discard_reason": result.discard_reason,
            "trace_events": trace_node(
                "classify",
                input_data={"markdown_length": len(state.get("markdown_text") or "")},
                output_data={**trace_fields, "discarded": True},
            ),
        }
    return {
        "status": STATUS_INTAKE_COMPLETE,
        "metadata": metadata,
        "departments_needed": result.departments_needed,
        "unmapped_topics": result.unmapped_topics,
        "requires_ceo_approval": result.requires_ceo_approval,
        "trace_events": trace_node(
            "classify",
            input_data={"markdown_length": len(state.get("markdown_text") or "")},
            output_data=trace_fields,
        ),
    }


def _orchestrate_node(state: RfpGraphState) -> dict[str, Any]:
    if state.get("status") != STATUS_INTAKE_COMPLETE:
        return {}
    pipeline = _load_pipeline()
    markdown = state.get("markdown_text") or ""
    excerpts = {
        dept: pipeline.build_department_excerpt(markdown, dept)
        for dept in state.get("departments_needed") or []
    }
    return {
        "department_excerpts": excerpts,
        "trace_events": trace_node(
            "orchestrate",
            input_data={"departments_needed": list(state.get("departments_needed") or [])},
            output_data={"department_ids": list(excerpts.keys())},
        ),
    }


def _workers_node(state: RfpGraphState) -> dict[str, Any]:
    if state.get("status") != STATUS_INTAKE_COMPLETE:
        return {}
    pipeline = _load_pipeline()
    metadata = state.get("metadata") or {}
    excerpts = state.get("department_excerpts") or {}
    key_aspects: dict[str, list[str]] = {}
    traces: list[dict[str, Any]] = []
    for dept in state.get("departments_needed") or []:
        excerpt = excerpts.get(dept, "")
        aspects = pipeline.generate_key_aspects(dept, metadata, excerpt)
        key_aspects[dept] = aspects
        traces.extend(
            trace_node(
                "worker",
                input_data={"department_id": dept},
                output_data={"key_aspect_count": len(aspects)},
            )
        )
    return {"department_key_aspects": key_aspects, "trace_events": traces}


def _synthesize_node(state: RfpGraphState) -> dict[str, Any]:
    if state.get("status") != STATUS_INTAKE_COMPLETE:
        return {}
    pipeline = _load_pipeline()
    summary, conflicts = pipeline.synthesize_intake(
        state.get("metadata") or {},
        state.get("departments_needed") or [],
        state.get("department_key_aspects") or {},
    )
    return {
        "intake_summary": summary,
        "conflicts": conflicts,
        "status": STATUS_INTAKE_COMPLETE,
        "trace_events": trace_node(
            "synthesize",
            input_data={"department_count": len(state.get("departments_needed") or [])},
            output_data={"conflict_count": len(conflicts)},
        ),
    }


def _route_after_convert(state: RfpGraphState) -> Literal["readability", "failed"]:
    if state.get("status") == STATUS_FAILED:
        return "failed"
    return "readability"


def _route_after_classify(state: RfpGraphState) -> Literal["orchestrate", "discarded", "failed"]:
    status = state.get("status")
    if status == STATUS_FAILED:
        return "failed"
    if status == STATUS_DISCARDED:
        return "discarded"
    return "orchestrate"


def build_graph() -> StateGraph:
    builder = StateGraph(RfpGraphState)
    builder.add_node("convert_pdf", _convert_pdf_node)
    builder.add_node("readability", _readability_node)
    builder.add_node("classify", _classify_node)
    builder.add_node("orchestrate", _orchestrate_node)
    builder.add_node("workers", _workers_node)
    builder.add_node("synthesize", _synthesize_node)
    add_generation_nodes(builder)
    add_approval_nodes(builder)
    set_entry_router(builder)
    builder.add_conditional_edges(
        "convert_pdf",
        _route_after_convert,
        {"readability": "readability", "failed": END},
    )
    builder.add_edge("readability", "classify")
    builder.add_conditional_edges(
        "classify",
        _route_after_classify,
        {"orchestrate": "orchestrate", "discarded": END, "failed": END},
    )
    builder.add_edge("orchestrate", "workers")
    builder.add_edge("workers", "synthesize")
    builder.add_edge("synthesize", END)
    return builder


@lru_cache(maxsize=1)
def _sqlite_checkpointer() -> SqliteSaver:
    db_path = checkpoint_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    logger.info("RFP checkpointer using %s", db_path)
    return SqliteSaver(conn)


@lru_cache(maxsize=1)
def get_compiled_graph():
    return build_graph().compile(checkpointer=_sqlite_checkpointer())


def intake_thread_id(ticket_id: str) -> str:
    """Checkpoint thread for P1 intake (M9-P3-10)."""
    return f"rfp:{ticket_id}:intake"


def invoke_rfp_intake(*, ticket_id: str, pdf_path: str | Path) -> RfpGraphState:
    """Run the intake graph synchronously and return final state."""
    graph = get_compiled_graph()
    config: dict[str, Any] = {"configurable": {"thread_id": intake_thread_id(ticket_id)}}
    input_state = initial_state(ticket_id=ticket_id, pdf_path=str(pdf_path))
    input_state["invoke_mode"] = "intake"
    try:
        return graph.invoke(input_state, config)
    except Exception as exc:  # noqa: BLE001
        logger.exception("RFP intake graph failed for ticket %s", ticket_id)
        failed = initial_state(ticket_id=ticket_id, pdf_path=str(pdf_path))
        failed["status"] = STATUS_FAILED
        failed["error_code"] = ERROR_PIPELINE_ERROR
        failed["error_message"] = "RFP intake pipeline failed."
        failed["trace_events"] = trace_node(
            "pipeline_error",
            input_data={"ticket_id": ticket_id},
            output_data={"error": str(exc)},
        )
        return failed


def invoke_rfp_generation(
    state: RfpGraphState,
    *,
    on_node_update: Callable[[str, dict[str, Any]], None] | None = None,
) -> RfpGraphState:
    """Run P2 generation nodes only (hydrated state — M9-P2-14).

    Uses a generation-specific checkpoint thread so intake state is not merged.
    When ``on_node_update`` is set, streams node outputs (for incremental Postgres
    persistence while parallel department branches complete).
    """
    graph = get_compiled_graph()
    ticket_id = state.get("ticket_id") or ""
    thread_id = f"rfp:{ticket_id}:generation"
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    input_state = dict(state)
    input_state["invoke_mode"] = "generation"
    try:
        if on_node_update is None:
            return graph.invoke(input_state, config)

        for chunk in graph.stream(input_state, config, stream_mode="updates"):
            if not isinstance(chunk, dict):
                continue
            for node_name, update in chunk.items():
                if update:
                    on_node_update(node_name, update)

        snapshot = graph.get_state(config)
        if snapshot and snapshot.values:
            return dict(snapshot.values)
        return input_state
    except Exception as exc:  # noqa: BLE001
        logger.exception("RFP generation graph failed for ticket %s", ticket_id)
        failed = dict(input_state)
        failed["status"] = STATUS_FAILED
        failed["error_code"] = ERROR_PIPELINE_ERROR
        failed["error_message"] = "RFP generation pipeline failed."
        failed["trace_events"] = trace_node(
            "pipeline_error",
            input_data={"ticket_id": ticket_id},
            output_data={"error": str(exc)},
        )
        return failed


def approval_thread_id(ticket_id: str) -> str:
    return f"rfp:{ticket_id}:approval"


def list_pending_interrupts(config: dict[str, Any]) -> list[Any]:
    """Return pending LangGraph interrupts for an approval checkpoint thread."""
    graph = get_compiled_graph()
    snapshot = graph.get_state(config)
    pending: list[Any] = []
    for task in snapshot.tasks or ():
        pending.extend(list(task.interrupts or ()))
    return pending


def invoke_rfp_approval(
    state: RfpGraphState,
    *,
    on_node_update: Callable[[str, dict[str, Any]], None] | None = None,
) -> RfpGraphState:
    """Run P3 approval nodes (hydrated state — M9-P3-3).

    Uses an approval-specific checkpoint thread. Returns graph state when interrupted
    or when the approval flow reaches a terminal node.
    """
    graph = get_compiled_graph()
    ticket_id = state.get("ticket_id") or ""
    config: dict[str, Any] = {"configurable": {"thread_id": approval_thread_id(ticket_id)}}
    input_state = dict(state)
    input_state["invoke_mode"] = "approval"
    try:
        if on_node_update is None:
            result = graph.invoke(input_state, config)
        else:
            for chunk in graph.stream(input_state, config, stream_mode="updates"):
                if not isinstance(chunk, dict):
                    continue
                for node_name, update in chunk.items():
                    if update:
                        on_node_update(node_name, update)
            snapshot = graph.get_state(config)
            result = dict(snapshot.values) if snapshot and snapshot.values else input_state

        if result.get("__interrupt__"):
            return result
        snapshot = graph.get_state(config)
        if snapshot and snapshot.values:
            merged = dict(snapshot.values)
            if result.get("__interrupt__"):
                merged["__interrupt__"] = result["__interrupt__"]
            return merged
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception("RFP approval graph failed for ticket %s", ticket_id)
        failed = dict(input_state)
        failed["status"] = STATUS_FAILED
        failed["error_code"] = ERROR_PIPELINE_ERROR
        failed["error_message"] = "RFP approval pipeline failed."
        failed["trace_events"] = trace_node(
            "pipeline_error",
            input_data={"ticket_id": ticket_id},
            output_data={"error": str(exc)},
        )
        return failed


def resume_rfp_approval(
    ticket_id: str,
    payload: dict[str, Any],
    *,
    interrupt_id: str | None = None,
) -> RfpGraphState:
    """Resume P3 from a human or CEO interrupt (M9-P3-9)."""
    graph = get_compiled_graph()
    config: dict[str, Any] = {"configurable": {"thread_id": approval_thread_id(ticket_id)}}
    pending = list_pending_interrupts(config)
    if not pending:
        raise RuntimeError(f"No pending approval interrupts for ticket {ticket_id}.")

    if interrupt_id:
        resume_arg: Any = {interrupt_id: payload}
    elif len(pending) == 1:
        resume_arg = payload
    else:
        dept = payload.get("department_id")
        kind = payload.get("kind")
        matched: str | None = None
        for intr in pending:
            value = intr.value or {}
            if kind == "ceo_approval" and value.get("kind") == "ceo_approval":
                matched = intr.id
                break
            if (
                value.get("kind") == "dept_approval"
                and value.get("department_id") == dept
            ):
                matched = intr.id
                break
        if matched is None:
            raise RuntimeError(
                f"No matching interrupt for department '{dept}' on ticket {ticket_id}."
            )
        resume_arg = {matched: payload}

    try:
        return graph.invoke(Command(resume=resume_arg), config)
    except Exception as exc:  # noqa: BLE001
        logger.exception("RFP approval resume failed for ticket %s", ticket_id)
        failed: RfpGraphState = RfpGraphState(
            ticket_id=ticket_id,
            invoke_mode="approval",
            status=STATUS_FAILED,
            error_code=ERROR_PIPELINE_ERROR,
            error_message="RFP approval resume failed.",
            trace_events=trace_node(
                "pipeline_error",
                input_data={"ticket_id": ticket_id, "phase": "approval_resume"},
                output_data={"error": str(exc)},
            ),
        )
        return failed


def reopen_department_approval(
    ticket_id: str,
    branch_payload: dict[str, Any],
) -> RfpGraphState:
    """Re-enter one department approval branch after reject recovery (M9-P3-7)."""
    graph = get_compiled_graph()
    config: dict[str, Any] = {"configurable": {"thread_id": approval_thread_id(ticket_id)}}
    send = Send("dept_approval_branch", branch_payload)
    try:
        return graph.invoke(Command(goto=[send]), config)
    except Exception as exc:  # noqa: BLE001
        logger.exception("RFP approval reopen failed for ticket %s", ticket_id)
        return RfpGraphState(
            ticket_id=ticket_id,
            invoke_mode="approval",
            status=STATUS_FAILED,
            error_code=ERROR_PIPELINE_ERROR,
            error_message="RFP approval reopen failed.",
            trace_events=trace_node(
                "pipeline_error",
                input_data={"ticket_id": ticket_id, "phase": "approval_resume"},
                output_data={"error": str(exc)},
            ),
        )


def reset_graph_cache() -> None:
    get_compiled_graph.cache_clear()
    _sqlite_checkpointer.cache_clear()


__all__ = [
    "approval_thread_id",
    "build_graph",
    "checkpoint_db_path",
    "get_compiled_graph",
    "intake_thread_id",
    "invoke_rfp_approval",
    "invoke_rfp_generation",
    "invoke_rfp_intake",
    "list_pending_interrupts",
    "reopen_department_approval",
    "reset_graph_cache",
    "resume_rfp_approval",
]
