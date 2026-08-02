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
from langgraph.config import get_config
from langgraph.graph import END, START, StateGraph

from knowledge.bootstrap import ensure_repo_root_on_path

from .classify import classify_question
from .fallbacks import resolve_fallback_message, resolve_ops_misroute_hint, resolve_procedure_hint
from .guardrails.input import evaluate_input_guard
from .guardrails.messages import CASUAL_REPLY_MESSAGE, resolve_guard_block_message
from .guardrails.observability import record_guardrail_event
from .guardrails.output import validate_agent_output
from .guardrails.sanitize import has_usable_sanitized_text, sanitize_rag_context
from .state import AgentState, initial_state
from .mcp_client import lookup_incidents_via_mcp, mutate_incident_via_mcp
from .tools.inventory import lookup_inventory_stock
from .write_confirmations import format_write_confirmation

logger = logging.getLogger(__name__)

RouteAfterIntake = Literal["error", "guard_input"]
RouteAfterGuardInput = Literal["guard_block", "classify"]
RouteAfterClassify = Literal[
    "retrieve",
    "lookup_incident",
    "lookup_inventory_stock",
    "mutate_incident",
    "inventory_write_block",
]
RouteAfterLookupIncident = Literal["retrieve", "generate", "fallback"]
RouteAfterMutateIncident = Literal["confirm_write", "fallback"]
RouteAfterLookupInventory = Literal["generate", "fallback"]
RouteAfterRetrieve = Literal["refuse", "generate", "fallback", "casual_reply"]

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


def _latest_tool(state: AgentState) -> dict[str, Any] | None:
    results = state.get("tool_results") or []
    return results[-1] if results else None


def _tool_has_rows(tool: dict[str, Any] | None) -> bool:
    if tool is None or not tool.get("ok"):
        return False
    if tool.get("summary"):
        return True
    rows = tool.get("rows")
    return isinstance(rows, list) and len(rows) > 0


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
        "trace_events": _trace("intake", valid=True),
    }


def guard_input_node(state: AgentState) -> dict[str, Any]:
    result = evaluate_input_guard(state["question"])
    trace: dict[str, Any] = {
        "node": "guard_input",
        "action": "block" if result.action == "block" else "continue",
    }
    if result.failure_type:
        trace["failure_type"] = result.failure_type
    if result.reason:
        trace["reason"] = result.reason
    if result.personal_use_score is not None:
        trace["personal_use_score"] = result.personal_use_score
    if result.matched:
        trace["matched"] = result.matched

    updates: dict[str, Any] = {
        "redirect_required": result.redirect_required,
        "trace_events": [trace],
    }
    if result.action == "block":
        updates["route"] = "guard_block"
        updates["failure_type"] = result.failure_type
        updates["guardrail_reason"] = result.reason
        updates["personal_use_score"] = result.personal_use_score
    return updates


def guard_block_node(state: AgentState) -> dict[str, Any]:
    answer = resolve_guard_block_message(state)
    record_guardrail_event(
        action="block",
        failure_type=state.get("failure_type"),
        reason=state.get("guardrail_reason"),
        question=state.get("question"),
    )
    trace: dict[str, Any] = {
        "node": "guard_block",
        "action": "block",
        "failure_type": state.get("failure_type"),
        "reason": state.get("guardrail_reason"),
    }
    if state.get("personal_use_score") is not None:
        trace["personal_use_score"] = state.get("personal_use_score")
    return {
        "answer": answer,
        "route": "guard_block",
        "trace_events": [trace],
    }


def casual_reply_node(state: AgentState) -> dict[str, Any]:
    record_guardrail_event(
        action="redirect",
        failure_type="content",
        reason="domain_redirect:casual_reply",
        question=state.get("question"),
    )
    return {
        "answer": CASUAL_REPLY_MESSAGE,
        "route": "casual_reply",
        "trace_events": [
            {
                "node": "casual_reply",
                "action": "redirect",
                "failure_type": "content",
                "reason": "domain_redirect:casual_reply",
            }
        ],
    }


def classify_node(state: AgentState) -> dict[str, Any]:
    result = classify_question(state["question"])
    trace: dict[str, Any] = {
        "node": "classify",
        "intent": result.intent,
        "matched": result.matched,
    }
    if result.incident_id is not None:
        trace["incident_id"] = result.incident_id
    if result.incident_filters:
        trace["filters"] = result.incident_filters
    if result.incident_action != "list":
        trace["incident_action"] = result.incident_action
    if result.write_action:
        trace["write_action"] = result.write_action
    return {
        "intent": result.intent,
        "incident_id": result.incident_id,
        "incident_filters": result.incident_filters,
        "incident_action": result.incident_action,
        "write_action": result.write_action,
        "write_payload": result.write_payload,
        "write_status": result.write_status,
        "trace_events": [trace],
    }


def lookup_incident_node(state: AgentState) -> dict[str, Any]:
    config = get_config() or {}
    configurable = config.get("configurable") or {}
    auth_header = configurable.get("auth_header")

    envelope = lookup_incidents_via_mcp(
        incident_id=state.get("incident_id"),
        filters=state.get("incident_filters") or {},
        auth_header=auth_header,
        incident_action=state.get("incident_action") or "list",
    )
    trace_fields: dict[str, Any] = {
        "ok": envelope.get("ok"),
        "row_count": len(envelope.get("rows") or []),
        "http_status": envelope.get("http_status"),
    }
    if envelope.get("reason"):
        trace_fields["reason"] = envelope.get("reason")

    updates: dict[str, Any] = {
        "tool_results": [envelope],
        "trace_events": _trace("lookup_incident", **trace_fields),
    }
    if envelope.get("ok") and (envelope.get("rows") or envelope.get("summary")):
        updates["sources_used"] = ["incidents_api"]
    return updates


def mutate_incident_node(state: AgentState) -> dict[str, Any]:
    config = get_config() or {}
    configurable = config.get("configurable") or {}
    auth_header = configurable.get("auth_header")

    envelope = mutate_incident_via_mcp(
        write_action=state.get("write_action") or "",
        auth_header=auth_header,
        incident_id=state.get("incident_id"),
        write_status=state.get("write_status"),
        write_payload=state.get("write_payload"),
    )
    trace_fields: dict[str, Any] = {
        "ok": envelope.get("ok"),
        "http_status": envelope.get("http_status"),
        "write_action": state.get("write_action"),
    }
    if envelope.get("reason"):
        trace_fields["reason"] = envelope.get("reason")

    updates: dict[str, Any] = {
        "tool_results": [envelope],
        "trace_events": _trace("mutate_incident", **trace_fields),
    }
    if envelope.get("ok") and envelope.get("rows"):
        updates["sources_used"] = ["incidents_api"]
    return updates


def confirm_write_node(state: AgentState) -> dict[str, Any]:
    tool = _latest_tool(state)
    if tool is None or not tool.get("ok"):
        message, reason = resolve_fallback_message(state)
        return {
            "answer": message,
            "route": "fallback",
            "trace_events": _trace("confirm_write", ok=False, reason=reason),
        }
    answer = format_write_confirmation(tool)
    return {
        "answer": answer,
        "route": "confirm_write",
        "trace_events": _trace("confirm_write", ok=True, write_action=tool.get("action")),
    }


def lookup_inventory_stock_node(state: AgentState) -> dict[str, Any]:
    config = get_config() or {}
    configurable = config.get("configurable") or {}
    auth_header = configurable.get("auth_header")

    envelope = lookup_inventory_stock(
        question=state["question"],
        auth_header=auth_header,
    )
    trace_fields: dict[str, Any] = {
        "ok": envelope.get("ok"),
        "row_count": len(envelope.get("rows") or []),
        "http_status": envelope.get("http_status"),
    }
    if envelope.get("reason"):
        trace_fields["reason"] = envelope.get("reason")
    if envelope.get("filters"):
        trace_fields["filters"] = envelope.get("filters")

    updates: dict[str, Any] = {
        "tool_results": [envelope],
        "trace_events": _trace("lookup_inventory_stock", **trace_fields),
    }
    if envelope.get("ok") and envelope.get("rows"):
        updates["sources_used"] = ["inventory_api"]
    return updates


def inventory_write_block_node(state: AgentState) -> dict[str, Any]:
    record_guardrail_event(
        action="block",
        failure_type="content",
        reason="inventory_write_forbidden",
        question=state.get("question"),
    )
    return {
        "tool_results": [
            {
                "source": "inventory_api",
                "ok": False,
                "http_status": 403,
                "rows": [],
                "reason": "inventory_write_forbidden",
                "error": "inventory_write_forbidden",
            }
        ],
        "trace_events": [
            {
                "node": "inventory_write_block",
                "action": "block",
                "failure_type": "content",
                "reason": "inventory_write_forbidden",
            }
        ],
    }


def retrieve_node(state: AgentState) -> dict[str, Any]:
    ensure_repo_root_on_path()
    from data.pipelines.rag import assemble_context, retrieve

    min_score = _default_min_score()
    chunks = retrieve(state["question"], min_score=min_score)
    raw_context = assemble_context(chunks) if chunks else ""
    context_text = sanitize_rag_context(raw_context) if raw_context else ""
    trace_fields: dict[str, Any] = {
        "chunk_count": len(chunks),
        "min_score": min_score,
    }
    if chunks and not has_usable_sanitized_text(context_text):
        trace_fields["sanitize_empty"] = True
        return {
            "chunks": chunks,
            "context_text": "",
            "fallback_reason": "empty_context_after_sanitize",
            "trace_events": _trace("retrieve", **trace_fields),
        }
    return {
        "chunks": chunks,
        "context_text": context_text,
        "trace_events": _trace("retrieve", **trace_fields),
    }


def _is_generation_provider_error(exc: BaseException) -> bool:
    """True when the generation LLM endpoint rejected or failed the request."""
    try:
        from openai import APIConnectionError, APIStatusError, PermissionDeniedError, RateLimitError
    except ImportError:
        return False
    return isinstance(
        exc,
        (PermissionDeniedError, APIStatusError, APIConnectionError, RateLimitError),
    )


def _generation_provider_fallback(state: AgentState, exc: BaseException) -> dict[str, Any]:
    logger.warning("generation LLM call failed: %s", exc)
    message, reason = resolve_fallback_message(
        {**state, "fallback_reason": "generation_provider_error"}
    )
    return {
        "answer": message,
        "route": "fallback",
        "fallback_reason": reason,
        "trace_events": _trace("generate", grounded=False, reason=reason),
    }


def generate_node(state: AgentState) -> dict[str, Any]:
    ensure_repo_root_on_path()
    from data.pipelines.rag import generate_answer

    from .generation import build_combined_context, generate_support_answer

    intent = state.get("intent", "rag")
    rag_context = state.get("context_text") or ""
    tool = _latest_tool(state)

    if intent == "rag":
        if not has_usable_sanitized_text(rag_context):
            message, reason = resolve_fallback_message(
                {**state, "fallback_reason": "empty_context_after_sanitize"}
            )
            return {
                "answer": message,
                "route": "fallback",
                "fallback_reason": reason,
                "trace_events": _trace(
                    "generate",
                    grounded=False,
                    reason="empty_context_after_sanitize",
                ),
            }
        try:
            answer = generate_answer(state["question"], rag_context)
        except Exception as exc:
            if _is_generation_provider_error(exc):
                return _generation_provider_fallback(state, exc)
            raise
    else:
        caveat: str | None = None
        if intent == "both" and tool is not None and not tool.get("ok"):
            caveat = (
                "Note: live incident lookup failed; answering from the knowledge base only."
            )
        combined = build_combined_context(
            rag_context=rag_context,
            tool_results=state.get("tool_results"),
            caveat=caveat,
        )
        if not combined.strip():
            message, reason = resolve_fallback_message(
                {**state, "fallback_reason": "empty_context_after_sanitize"}
            )
            return {
                "answer": message,
                "route": "fallback",
                "fallback_reason": reason,
                "trace_events": _trace(
                    "generate",
                    grounded=False,
                    reason="empty_context_after_sanitize",
                ),
            }
        try:
            answer = generate_support_answer(
                state["question"],
                rag_context=rag_context,
                tool_results=state.get("tool_results"),
                caveat=caveat,
            )
        except Exception as exc:
            if _is_generation_provider_error(exc):
                return _generation_provider_fallback(state, exc)
            raise

    return {
        "answer": answer,
        "route": "generate",
        "trace_events": _trace("generate", grounded=True, intent=intent),
    }


def validate_output_node(state: AgentState) -> dict[str, Any]:
    result = validate_agent_output(
        state.get("answer") or "",
        redirect_required=bool(state.get("redirect_required")),
    )
    trace: dict[str, Any] = {
        "node": "validate_output",
        "ok": result.ok,
    }
    if not result.ok:
        trace["failure_type"] = "structural"
        trace["reason"] = result.reason
        trace["action"] = "validation_failure"
        record_guardrail_event(
            action="validation_failure",
            failure_type="structural",
            reason=result.reason,
            question=state.get("question"),
        )
    elif result.redirect_reason:
        trace["failure_type"] = "content"
        trace["reason"] = result.redirect_reason
        trace["action"] = "redirect"
        record_guardrail_event(
            action="redirect",
            failure_type="content",
            reason=result.redirect_reason,
            question=state.get("question"),
        )

    return {
        "answer": result.answer,
        "trace_events": [trace],
    }


def refuse_node(state: AgentState) -> dict[str, Any]:
    ensure_repo_root_on_path()
    from data.pipelines.rag import refusal_message

    procedure_hint = resolve_procedure_hint(state.get("question") or "")
    if procedure_hint:
        return {
            "answer": procedure_hint,
            "route": "refuse",
            "trace_events": _trace("refuse", reason="procedure_hint"),
        }

    ops_hint = resolve_ops_misroute_hint(state.get("question") or "")
    if ops_hint:
        return {
            "answer": ops_hint,
            "route": "refuse",
            "trace_events": _trace("refuse", reason="ops_misroute_hint"),
        }

    return {
        "answer": refusal_message(),
        "route": "refuse",
        "trace_events": _trace("refuse", reason="empty_retrieval"),
    }


def fallback_node(state: AgentState) -> dict[str, Any]:
    message, reason = resolve_fallback_message(state)
    return {
        "answer": message,
        "route": "fallback",
        "trace_events": _trace("fallback", reason=reason),
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
    return "guard_input"


def route_after_guard_input(state: AgentState) -> RouteAfterGuardInput:
    if state.get("route") == "guard_block":
        return "guard_block"
    return "classify"


def route_after_classify(state: AgentState) -> RouteAfterClassify:
    intent = state.get("intent", "rag")
    if intent == "rag":
        return "retrieve"
    if intent == "inventory":
        return "lookup_inventory_stock"
    if intent == "inventory_write":
        return "inventory_write_block"
    if intent == "incident_write":
        return "mutate_incident"
    return "lookup_incident"


def route_after_lookup_incident(state: AgentState) -> RouteAfterLookupIncident:
    intent = state.get("intent", "rag")
    if intent == "both":
        return "retrieve"
    if _tool_has_rows(_latest_tool(state)):
        return "generate"
    return "fallback"


def route_after_lookup_inventory(state: AgentState) -> RouteAfterLookupInventory:
    if _tool_has_rows(_latest_tool(state)):
        return "generate"
    return "fallback"


def route_after_mutate_incident(state: AgentState) -> RouteAfterMutateIncident:
    tool = _latest_tool(state)
    if tool is not None and tool.get("ok") and tool.get("rows"):
        return "confirm_write"
    return "fallback"


def route_after_retrieve(state: AgentState) -> RouteAfterRetrieve:
    intent = state.get("intent", "rag")
    chunks = state.get("chunks") or []
    tool = _latest_tool(state)
    context_text = (state.get("context_text") or "").strip()

    if state.get("fallback_reason") == "empty_context_after_sanitize":
        return "fallback"

    if intent == "rag":
        if state.get("redirect_required") and not chunks:
            return "casual_reply"
        return "generate" if context_text else "refuse"

    if intent == "both":
        if tool is not None and not tool.get("ok") and not chunks:
            return "fallback"
        return "generate"

    return "generate" if chunks else "refuse"


def build_graph() -> StateGraph:
    """Construct the uncompiled Support Agent graph."""
    builder: StateGraph = StateGraph(AgentState)
    builder.add_node("intake", intake_node)
    builder.add_node("guard_input", guard_input_node)
    builder.add_node("guard_block", guard_block_node)
    builder.add_node("casual_reply", casual_reply_node)
    builder.add_node("classify", classify_node)
    builder.add_node("lookup_incident", lookup_incident_node)
    builder.add_node("mutate_incident", mutate_incident_node)
    builder.add_node("confirm_write", confirm_write_node)
    builder.add_node("lookup_inventory_stock", lookup_inventory_stock_node)
    builder.add_node("inventory_write_block", inventory_write_block_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("generate", generate_node)
    builder.add_node("validate_output", validate_output_node)
    builder.add_node("refuse", refuse_node)
    builder.add_node("fallback", fallback_node)
    builder.add_node("error", error_node)

    builder.add_edge(START, "intake")
    builder.add_conditional_edges(
        "intake",
        route_after_intake,
        {"error": "error", "guard_input": "guard_input"},
    )
    builder.add_conditional_edges(
        "guard_input",
        route_after_guard_input,
        {"guard_block": "guard_block", "classify": "classify"},
    )
    builder.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "retrieve": "retrieve",
            "lookup_incident": "lookup_incident",
            "lookup_inventory_stock": "lookup_inventory_stock",
            "mutate_incident": "mutate_incident",
            "inventory_write_block": "inventory_write_block",
        },
    )
    builder.add_edge("inventory_write_block", "fallback")
    builder.add_conditional_edges(
        "mutate_incident",
        route_after_mutate_incident,
        {"confirm_write": "confirm_write", "fallback": "fallback"},
    )
    builder.add_conditional_edges(
        "lookup_incident",
        route_after_lookup_incident,
        {
            "retrieve": "retrieve",
            "generate": "generate",
            "fallback": "fallback",
        },
    )
    builder.add_conditional_edges(
        "lookup_inventory_stock",
        route_after_lookup_inventory,
        {"generate": "generate", "fallback": "fallback"},
    )
    builder.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {
            "refuse": "refuse",
            "generate": "generate",
            "fallback": "fallback",
            "casual_reply": "casual_reply",
        },
    )
    builder.add_edge("error", END)
    builder.add_edge("guard_block", END)
    builder.add_edge("casual_reply", END)
    builder.add_edge("refuse", END)
    builder.add_edge("fallback", END)
    builder.add_edge("confirm_write", END)
    builder.add_edge("generate", "validate_output")
    builder.add_edge("validate_output", END)
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
    auth_header: str | None = None,
) -> AgentState:
    """Run the Support Agent graph synchronously and return final state."""
    graph = get_compiled_graph()
    config: dict[str, Any] = {
        "configurable": {
            "thread_id": thread_id or str(uuid.uuid4()),
        }
    }
    if auth_header:
        config["configurable"]["auth_header"] = auth_header
    return graph.invoke(initial_state(question), config)
