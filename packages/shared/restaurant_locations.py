"""Shared Brasaland restaurant location map (ids 1–14, P24-OPT-L4)."""

from __future__ import annotations

from dataclasses import dataclass

from typing import Iterable


@dataclass(frozen=True)
class RestaurantLocation:
    id: int
    name: str
    city: str
    country: str


RESTAURANT_LOCATIONS: tuple[RestaurantLocation, ...] = (
    RestaurantLocation(1, "Brasaland Medellín Centro", "Medellín", "CO"),
    RestaurantLocation(2, "Brasaland Medellín Laureles", "Medellín", "CO"),
    RestaurantLocation(3, "Brasaland Medellín Envigado", "Envigado", "CO"),
    RestaurantLocation(4, "Brasaland Bogotá Chapinero", "Bogotá", "CO"),
    RestaurantLocation(5, "Brasaland Bogotá Usaquén", "Bogotá", "CO"),
    RestaurantLocation(6, "Brasaland Cali Granada", "Cali", "CO"),
    RestaurantLocation(7, "Brasaland Barranquilla Norte", "Barranquilla", "CO"),
    RestaurantLocation(8, "Brasaland Miami Beach", "Miami Beach", "US"),
    RestaurantLocation(9, "Brasaland Miami Brickell", "Miami", "US"),
    RestaurantLocation(10, "Brasaland Fort Lauderdale", "Fort Lauderdale", "US"),
    RestaurantLocation(11, "Brasaland Orlando I-Drive", "Orlando", "US"),
    RestaurantLocation(12, "Brasaland Tampa Bay", "Tampa", "US"),
    RestaurantLocation(13, "Brasaland West Palm Beach", "West Palm Beach", "US"),
    RestaurantLocation(14, "Brasaland Jacksonville", "Jacksonville", "US"),
)

LOCATION_BY_ID: dict[int, RestaurantLocation] = {
    location.id: location for location in RESTAURANT_LOCATIONS
}

LOCATION_ALIASES: dict[str, int] = {
    "centro": 1,
    "medellin centro": 1,
    "medellín centro": 1,
    "laureles": 2,
    "envigado": 3,
    "medellin envigado": 3,
    "medellín envigado": 3,
    "chapinero": 4,
    "bogota chapinero": 4,
    "bogotá chapinero": 4,
    "usaquen": 5,
    "usaquén": 5,
    "bogota usaquen": 5,
    "bogotá usaquén": 5,
    "cali granada": 6,
    "granada": 6,
    "cali": 6,
    "barranquilla": 7,
    "barranquilla norte": 7,
    "miami beach": 8,
    "brickell": 9,
    "miami brickell": 9,
    "fort lauderdale": 10,
    "orlando": 11,
    "i-drive": 11,
    "i drive": 11,
    "idrive": 11,
    "tampa bay": 12,
    "tampa": 12,
    "west palm beach": 13,
    "west palm": 13,
    "jacksonville": 14,
}

# Metro names that map to multiple branches when no neighborhood alias matched.
METRO_AREA_CANDIDATES: dict[str, tuple[int, ...]] = {
    "medellín": (1, 2, 3),
    "medellin": (1, 2, 3),
    "bogotá": (4, 5),
    "bogota": (4, 5),
    "miami": (8, 9),
}

LOCATION_SHORT_NAMES: dict[int, str] = {
    1: "Centro",
    2: "Laureles",
    3: "Envigado",
    4: "Chapinero",
    5: "Usaquén",
    6: "Cali Granada",
    7: "Barranquilla Norte",
    8: "Miami Beach",
    9: "Miami Brickell",
    10: "Fort Lauderdale",
    11: "Orlando I-Drive",
    12: "Tampa Bay",
    13: "West Palm Beach",
    14: "Jacksonville",
}

MIN_LOCATION_ID = 1
MAX_LOCATION_ID = 14


def get_location(location_id: int) -> RestaurantLocation | None:
    return LOCATION_BY_ID.get(location_id)


def format_location_label(location_id: int) -> str:
    location = get_location(location_id)
    if not location:
        return f"Location {location_id}"
    return f"{location.name} — {location.city}"


def location_short_name(location_id: int) -> str:
    return LOCATION_SHORT_NAMES.get(location_id, format_location_label(location_id))


def resolve_location_hint(text: str) -> int | None:
    """Match a city/neighborhood/location name fragment to a location_id."""
    lower = text.lower()
    for alias in sorted(LOCATION_ALIASES.keys(), key=len, reverse=True):
        if alias in lower:
            return LOCATION_ALIASES[alias]

    city_matches: list[int] = []
    for location in RESTAURANT_LOCATIONS:
        if location.city.lower() in lower:
            city_matches.append(location.id)
    if len(city_matches) == 1:
        return city_matches[0]

    for location in RESTAURANT_LOCATIONS:
        name_tail = location.name.split()[-1].lower()
        if len(name_tail) >= 5 and name_tail in lower:
            return location.id
    return None


@dataclass(frozen=True)
class LocationScope:
    """Resolved or ambiguous location scope extracted from user text."""

    resolved_id: int | None
    ambiguous_ids: tuple[int, ...] | None = None

    @property
    def is_ambiguous(self) -> bool:
        return self.resolved_id is None and bool(self.ambiguous_ids)


def _specific_alias_matched(text: str, location_ids: Iterable[int]) -> bool:
    lower = text.lower()
    allowed = set(location_ids)
    for alias, location_id in LOCATION_ALIASES.items():
        if location_id in allowed and alias in lower:
            return True
    return False


def resolve_location_scope(text: str) -> LocationScope:
    """Resolve a single location id or return ambiguous metro-area candidates."""
    resolved = resolve_location_hint(text)
    if resolved is not None:
        return LocationScope(resolved_id=resolved)

    lower = (text or "").lower()
    for metro in sorted(METRO_AREA_CANDIDATES.keys(), key=len, reverse=True):
        if metro not in lower:
            continue
        candidates = METRO_AREA_CANDIDATES[metro]
        if _specific_alias_matched(text, candidates):
            hint = resolve_location_hint(text)
            if hint is not None:
                return LocationScope(resolved_id=hint)
        return LocationScope(resolved_id=None, ambiguous_ids=candidates)

    return LocationScope(resolved_id=None)
