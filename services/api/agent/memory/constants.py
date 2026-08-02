"""Support Agent memory graph constants (context-26)."""

from __future__ import annotations

MEMORY_ACK_MESSAGE = "Got it — I'll remember that for next time."

MEMORY_REJECT_BARE_ASSENT_MESSAGE = (
    "I didn't save that. To confirm memory, say something like "
    '"Yes, please remember that."'
)

MEMORY_REJECT_TOPIC_CHANGE_MESSAGE = (
    "I didn't save the pending memory because you asked a different question. "
    "You can propose it again if you still want me to remember it."
)

MEMORY_REJECT_DENYLIST_MESSAGE = (
    "I can't save that in operational memory — it matches blocked content "
    "(such as payroll, personal data, or official policy). "
    "The correction was not stored."
)

MEMORY_REJECT_USER_DECLINED_MESSAGE = "Understood — I won't save that."

MEMORY_REJECT_EMPTY_REPLY_MESSAGE = (
    "I didn't save that. Please confirm with something like "
    '"Yes, please remember that" or say no if you do not want me to remember it.'
)

MEMORY_REJECT_GENERIC_MESSAGE = (
    "I didn't save that. Please confirm with something like "
    '"Yes, please remember that."'
)

MEMORY_NO_PENDING_BARE_ASSENT_MESSAGE = (
    "I don't have a pending memory request to confirm. "
    "Send the location correction again in one message, wait until I ask "
    'whether to remember it, then reply with "Yes, please remember that." '
    "Use the same conversation — don't click New conversation between turns."
)

MEMORY_NO_PENDING_APPROVE_MESSAGE = (
    "I don't have a pending memory request to approve. "
    "If you previously replied with bare \"yes\", that cleared the proposal — "
    "send the location correction again, wait until I ask whether to remember it, "
    'then reply with "Yes, please remember that."'
)

MEMORY_PROPOSAL_RATE_LIMIT_MESSAGE = (
    "I couldn't stage a memory proposal because you've reached the proposal "
    "limit for now. Try again later, or ask an admin to raise "
    "AGENT_MEMORY_PROPOSAL_RATE_LIMIT."
)

MEMORY_PROPOSE_CONFIRMATION_FALLBACK = (
    "Thanks for the correction. Would you like me to remember that for next time?"
)


def memory_reject_message(*, outcome: str, reason: str | None = None) -> str:
    """User-facing reply when a pending proposal is not stored."""
    if (
        outcome == "rejected_denylist"
        or reason
        in {
            "denylist",
            "payroll",
            "allergen_zero_risk",
            "email_pii",
            "phone_pii",
            "instruction_override",
            "brasa_points_pii",
            "live_operational_snapshot",
        }
    ):
        return MEMORY_REJECT_DENYLIST_MESSAGE
    if outcome == "reject":
        return MEMORY_REJECT_USER_DECLINED_MESSAGE
    if reason == "bare_assent":
        return MEMORY_REJECT_BARE_ASSENT_MESSAGE
    if reason == "topic_change":
        return MEMORY_REJECT_TOPIC_CHANGE_MESSAGE
    if reason == "empty_reply":
        return MEMORY_REJECT_EMPTY_REPLY_MESSAGE
    return MEMORY_REJECT_GENERIC_MESSAGE


MEMORY_PROPOSAL_DISABLED_ROUTES: frozenset[str] = frozenset(
    {
        "guard_block",
        "casual_reply",
        "error",
        "refuse",
        "fallback",
        "confirm_write",
        "inventory_write_block",
        "memory_ack",
        "memory_reject",
    }
)
