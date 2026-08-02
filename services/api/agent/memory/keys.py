"""Memory key allowlist per category (context-26 P26-L17)."""

from __future__ import annotations

from packages.shared.restaurant_locations import LOCATION_ALIASES, RESTAURANT_LOCATIONS

ALLOWED_CATEGORIES: frozenset[str] = frozenset(
    {"hours", "suppliers", "known_incidents", "preferences"}
)

GLOBAL_CATEGORIES: frozenset[str] = frozenset({"hours", "suppliers", "known_incidents"})

CATEGORY_KEYS: dict[str, frozenset[str]] = {
    "hours": frozenset(
        {
            "weekday_open",
            "weekday_close",
            "weekend_open",
            "weekend_close",
            "friday_close",
            "special_hours",
        }
    ),
    "suppliers": frozenset(
        {
            "meat_delivery_day",
            "vegetable_delivery_day",
            "general_delivery_day",
        }
    ),
    "known_incidents": frozenset(
        {
            "zero_sales_pattern",
            "pos_outage_pattern",
            "power_outage_pattern",
        }
    ),
    "preferences": frozenset(
        {
            "report_format",
            "language_preference",
            "summary_style",
        }
    ),
}


class MemoryKeyError(ValueError):
    """Raised when category or key is not allowlisted."""


def _base_normalize_key(key: str) -> str:
    normalized = (key or "").strip().lower().replace("-", "_")
    return "_".join(part for part in normalized.split() if part)


def _location_prefix_tokens() -> tuple[str, ...]:
    tokens: set[str] = set(LOCATION_ALIASES.keys())
    for location in RESTAURANT_LOCATIONS:
        tokens.add(location.city.lower())
        for part in location.name.lower().replace("—", " ").split():
            cleaned = part.strip(".,;:")
            if len(cleaned) >= 4:
                tokens.add(cleaned)
    return tuple(sorted(tokens, key=len, reverse=True))


def normalize_key(category: str, key: str) -> str:
    """Map LLM keys (often location-prefixed) to the category allowlist."""
    cat = validate_category(category)
    allowed = CATEGORY_KEYS.get(cat, frozenset())
    normalized = _base_normalize_key(key)

    if normalized in allowed:
        return normalized

    for allowed_key in sorted(allowed, key=len, reverse=True):
        if normalized.endswith("_" + allowed_key):
            return allowed_key

    for prefix in _location_prefix_tokens():
        for head in (prefix.replace(" ", "_"), prefix.replace("-", "_")):
            if not head:
                continue
            marker = f"{head}_"
            if normalized.startswith(marker):
                remainder = normalized[len(marker) :]
                if remainder in allowed:
                    return remainder
                for allowed_key in sorted(allowed, key=len, reverse=True):
                    if remainder.endswith("_" + allowed_key):
                        return allowed_key

    raise MemoryKeyError(f"Key {key!r} not allowlisted for category {cat!r}")


def validate_category(category: str) -> str:
    normalized = (category or "").strip().lower()
    if normalized not in ALLOWED_CATEGORIES:
        raise MemoryKeyError(f"Category not allowlisted: {category!r}")
    return normalized


def validate_key(category: str, key: str) -> str:
    return normalize_key(category, key)


def format_allowed_keys_for_prompt() -> str:
    """Human-readable allowlist for structured generation prompts."""
    lines: list[str] = []
    for category in sorted(CATEGORY_KEYS):
        keys = ", ".join(sorted(CATEGORY_KEYS[category]))
        lines.append(f"- {category}: {keys}")
    return "\n".join(lines)
