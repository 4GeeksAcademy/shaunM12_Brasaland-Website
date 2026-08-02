"""Fixed guardrail refusal and redirect templates (context-25 P25-L12c, L14b, L16, L16b).

Copy is locked in memory-bank/historical-reference/context-25-securing-agents-harness-guardrails.md
— change templates there first, then here.
"""

from __future__ import annotations

from typing import Any

CASUAL_REPLY_MESSAGE = (
    "I don't have live weather or general trivia data in Brasaland's systems.\n\n"
    "I'm Brasaland's Support Agent — I can help with incidents, inventory, and "
    "knowledge-base policies (loyalty, allergens, waste, supplier ordering). "
    "What would you like to know?"
)

REDIRECT_SUFFIX = (
    "\n\nI'm Brasaland's Support Agent — I can help with incidents, inventory, and "
    "knowledge-base policies (loyalty, allergens, waste, supplier ordering). "
    "What would you like to know?"
)

INSTRUCTION_OVERRIDE_REFUSAL = (
    "I can't change or ignore my operating rules. "
    "I'm Brasaland's Support Agent — ask me about incidents, inventory, or "
    "knowledge-base policies (loyalty, allergens, waste, supplier ordering)."
)

OUTPUT_VALIDATION_FALLBACK = (
    "I couldn't return that response safely.\n\n"
    "I'm Brasaland's Support Agent — ask me about incidents, inventory, or "
    "knowledge-base policies (loyalty, allergens, waste, supplier ordering)."
)

REFUSAL_SUPPORT_REDIRECT_SUFFIX = (
    "\n\nI'm Brasaland's Support Agent — what can I help you with for operations support?"
)

PERSONAL_USE_REFUSALS: dict[str, str] = {
    "creative": (
        "I can't produce personal creative writing or general content. "
        "I'm here for Brasaland operations support — incidents, stock, and official manuals."
    ),
    "academic": (
        "I can't help with homework or academic assignments. "
        "I'm Brasaland's Support Agent for operations and knowledge-base questions."
    ),
    "wellness": (
        "I'm not able to provide therapy or personal counseling. "
        "For Brasaland support, ask about incidents, inventory, or company policies."
    ),
    "personal_code": (
        "I can't help with personal coding projects. "
        "I support Brasaland backoffice ops — incidents, inventory, and internal manuals."
    ),
    "personal_career": (
        "I can't help with personal job applications or resumes. "
        "Ask me about Brasaland operations or knowledge-base content instead."
    ),
    "general_knowledge": (
        "I can't act as a general encyclopedia. "
        "I'm Brasaland's Support Agent — ask about incidents, inventory, or our official manuals."
    ),
    "entertainment": (
        "I can't provide entertainment or roleplay unrelated to Brasaland support. "
        "Ask me about incidents, inventory, or knowledge-base policies."
    ),
    "concierge": (
        "I can't help with personal travel or life concierge requests. "
        "I'm here for Brasaland operations support."
    ),
    "personal_media": (
        "I can't translate or edit personal messages. "
        "I'm Brasaland's Support Agent for operations and knowledge-base questions."
    ),
    "task_delegation": (
        "I can't take on personal tasks unrelated to Brasaland. "
        "Ask me about incidents, inventory, or official manuals."
    ),
    "roleplay": (
        "I can't roleplay or pretend to be another assistant. "
        "I'm Brasaland's Support Agent for backoffice operations support."
    ),
    "default": (
        "I can't help with personal or unrelated tasks. "
        "I'm here for Brasaland operations support: incidents, stock levels, and official manuals "
        "(loyalty, allergens, waste, supplier ordering). What would you like to know?"
    ),
}


def answer_has_redirect_marker(text: str) -> bool:
    """True when answer already steers back to Brasaland (P25-L14c)."""
    lower = (text or "").lower()
    return "brasaland" in lower or "support agent" in lower


def enforce_redirect_suffix(answer: str) -> tuple[str, str | None]:
    """Append redirect suffix when missing; return (final_answer, redirect_reason)."""
    if answer_has_redirect_marker(answer):
        return answer, "domain_redirect:already_present"
    return answer.rstrip() + REDIRECT_SUFFIX, "domain_redirect:suffix_appended"


def resolve_guard_block_message(state: dict[str, Any]) -> str:
    """Pick user-facing copy for guard_block node (P25-L16, P25-L16b)."""
    if state.get("failure_type") == "security":
        return INSTRUCTION_OVERRIDE_REFUSAL

    reason = str(state.get("guardrail_reason") or "")
    if reason.startswith("personal_use:"):
        family = reason.split(":", 1)[1].split(":")[0]
        return PERSONAL_USE_REFUSALS.get(family, PERSONAL_USE_REFUSALS["default"])
    return PERSONAL_USE_REFUSALS["default"]
