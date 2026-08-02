"""Support Agent persistent memory (context-26 MEM-092).

P26-1: Postgres store, denylist, key allowlist.
P26-3+: graph integration, proposal classifier, generation injection.
"""

from __future__ import annotations

from .denylist import DenylistResult, check_denylist
from .keys import ALLOWED_CATEGORIES, validate_category, validate_key
from .models import AgentMemoryAuditLog, AgentMemoryEntry, ensure_agent_memory_schema
from .schemas import (
    GenerationResult,
    MemoryProposal,
    MemoryWriteResult,
    validate_proposal_shape,
)
from .location_hint import resolve_injection_location_id
from .proposal import classify_memory_decision
from .store import (
    check_proposal_rate_limit,
    count_recent_proposed,
    log_proposal,
    proposal_rate_limit,
    proposal_rate_window_hours,
    purge_stale_entries,
    read_memory,
    write_memory,
)
from .structured_generation import build_generation_result, parse_structured_payload

__all__ = [
    "ALLOWED_CATEGORIES",
    "AgentMemoryAuditLog",
    "AgentMemoryEntry",
    "DenylistResult",
    "GenerationResult",
    "MemoryProposal",
    "MemoryWriteResult",
    "build_generation_result",
    "check_denylist",
    "check_proposal_rate_limit",
    "classify_memory_decision",
    "count_recent_proposed",
    "ensure_agent_memory_schema",
    "log_proposal",
    "parse_structured_payload",
    "proposal_rate_limit",
    "proposal_rate_window_hours",
    "purge_stale_entries",
    "read_memory",
    "resolve_injection_location_id",
    "validate_category",
    "validate_key",
    "validate_proposal_shape",
    "write_memory",
]
