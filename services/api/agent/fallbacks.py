"""Template fallback messages for Support Agent tool failures (P2-L30–P2-L34)."""

from __future__ import annotations

from typing import Any

from agent.classify import has_procedure_phrasing, looks_like_live_ops_question

TIMEOUT_INCIDENT = (
    "I couldn't reach live incident data in time. Please try again in a moment, "
    "or check the Incidents tab in the backoffice directly."
)

TIMEOUT_INVENTORY = (
    "I couldn't reach live inventory data in time. Please try again in a moment, "
    "or check the Inventory tab in the backoffice directly."
)

HTTP_ERROR_INCIDENT = (
    "Live incident lookup failed. Please try again shortly, or use the "
    "Incidents manager in the backoffice."
)

HTTP_ERROR_INCIDENT_WRITE = (
    "The incident change could not be completed. Please try again shortly, "
    "or use the Incidents manager in the backoffice."
)

INVALID_STATUS_TRANSITION = (
    "That status change is not allowed for incident {incident_id}. "
    "Open incidents must move to in_progress before resolved. "
    "Allowed paths: open → in_progress → resolved, or open → discarded."
)

INCIDENT_PROCEDURE_HINT = (
    "To create an incident in Brasaland, use the Incidents manager in the backoffice, "
    "or ask the Support Agent with a direct command such as: "
    "\"Create incident for broken POS at Miami Doral: terminal frozen during lunch rush\". "
    "Include the branch and a short description. "
    "Status updates follow: open → in_progress → resolved (or open → discarded)."
)

HTTP_ERROR_INVENTORY = (
    "Live inventory lookup failed. Please try again shortly, or use the "
    "Inventory tab in the backoffice."
)

EMPTY_INCIDENT = (
    "No incidents matched that query. Try an incident ID (e.g. incident 42) or "
    "narrow by status, branch, or origin."
)

NOT_FOUND_INCIDENT = (
    "I couldn't find incident {incident_id}. Check the ID or browse open "
    "incidents in the Incidents manager."
)

EMPTY_INVENTORY = (
    "No products matched that stock query. Check the SKU, product ID, or "
    "location in Inventory."
)

INVENTORY_WRITE_FORBIDDEN = (
    "The Support Agent can only read inventory stock levels. "
    "To restock, submit inbound/outbound orders, or adjust stock, use the Inventory tab "
    "in the backoffice."
)

VAGUE_INVENTORY_QUERY = (
    "Please include a SKU, product ID, or product name in your stock question — "
    "for example: \"Current stock for SKU BEEF-001\", \"Stock for beef at Chapinero\", "
    "or \"How much beef do we have\"."
)

BOTH_TOOL_AND_RAG_EMPTY = (
    "I couldn't fetch live incidents, and I don't have matching knowledge-base "
    "content for that question. Try again shortly, or check Incidents and "
    "Knowledge separately in the backoffice."
)

STUB_NOT_IMPLEMENTED = (
    "Live incident lookup is not wired yet on this build. Retry after the "
    "tool integration phase, or use the Incidents manager in the backoffice."
)

OPS_MISROUTE_HINT = (
    "That sounds like a live incidents or inventory question, not a knowledge-base policy. "
    "Try one of these examples:\n"
    '• "List open incidents" or "Show me all incidents at Miami Doral"\n'
    '• "Stock for beef at Chapinero" or "How much beef do we have"'
)


def resolve_procedure_hint(question: str) -> str | None:
    """Return a static ops hint when a how-to question has no KB match."""
    lower = (question or "").lower()
    if not has_procedure_phrasing(question):
        return None
    if any(word in lower for word in ("incident", "ticket", "case")):
        return INCIDENT_PROCEDURE_HINT
    return None


def resolve_ops_misroute_hint(question: str) -> str | None:
    """Return guidance when a live-data question was mis-routed to empty KB retrieval."""
    if looks_like_live_ops_question(question):
        return OPS_MISROUTE_HINT
    return None


def resolve_fallback_message(state: dict[str, Any]) -> tuple[str, str]:
    """Pick user-facing fallback copy from graph state. Returns (message, reason)."""
    intent = state.get("intent", "rag")
    tool_results = state.get("tool_results") or []
    tool = tool_results[-1] if tool_results else {}
    reason = str(tool.get("reason") or "unknown")

    if reason == "both_tool_and_rag_empty":
        return BOTH_TOOL_AND_RAG_EMPTY, reason

    if reason == "inventory_write_forbidden":
        return INVENTORY_WRITE_FORBIDDEN, reason

    if reason == "needs_clarification":
        if intent in ("inventory", "inventory_write"):
            return VAGUE_INVENTORY_QUERY, reason
        return EMPTY_INCIDENT, reason

    if reason == "not_found":
        incident_id = state.get("incident_id") or tool.get("incident_id")
        product_id = tool.get("product_id")
        if incident_id is not None:
            return NOT_FOUND_INCIDENT.format(incident_id=incident_id), reason
        if product_id is not None:
            return (
                f"I couldn't find product {product_id}. Check the product ID or browse "
                "stock in the Inventory tab."
            ), reason
        return EMPTY_INCIDENT, "empty"

    if reason == "empty":
        if intent == "inventory":
            return EMPTY_INVENTORY, reason
        return EMPTY_INCIDENT, reason

    if reason == "invalid_status_transition":
        incident_id = state.get("incident_id") or tool.get("incident_id") or "?"
        return INVALID_STATUS_TRANSITION.format(incident_id=incident_id), reason

    if reason == "timeout":
        if intent == "inventory":
            return TIMEOUT_INVENTORY, reason
        return TIMEOUT_INCIDENT, reason

    if reason.startswith("http_"):
        if intent == "inventory":
            return HTTP_ERROR_INVENTORY, reason
        if intent == "incident_write":
            return HTTP_ERROR_INCIDENT_WRITE, reason
        return HTTP_ERROR_INCIDENT, reason

    if reason == "stub":
        if intent == "inventory":
            return (
                "Live inventory lookup is not wired yet on this build. "
                "Use the Inventory tab in the backoffice."
            ), reason
        return STUB_NOT_IMPLEMENTED, reason

    if intent == "incident_write":
        return HTTP_ERROR_INCIDENT_WRITE, reason
    if intent in ("inventory", "inventory_write"):
        return HTTP_ERROR_INVENTORY, reason
    return HTTP_ERROR_INCIDENT, reason
