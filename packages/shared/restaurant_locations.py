"""Shared Brasaland restaurant location map (ids 1–14, P24-OPT-L4)."""

from __future__ import annotations

from dataclasses import dataclass


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
    "chapinero": 4,
    "usaquen": 5,
    "usaquén": 5,
    "laureles": 2,
    "envigado": 3,
    "medellin": 1,
    "medellín": 1,
    "orlando": 11,
    "fort lauderdale": 10,
    "miami beach": 8,
    "brickell": 9,
    "i-drive": 11,
    "i drive": 11,
}

MIN_LOCATION_ID = 1
MAX_LOCATION_ID = 14


def get_location(location_id: int) -> RestaurantLocation | None:
    return LOCATION_BY_ID.get(location_id)


def format_location_label(location_id: int) -> str:
    location = get_location(location_id)
    if location is None:
        return f"Location {location_id}"
    return f"{location.name} — {location.city}"


def resolve_location_hint(text: str) -> int | None:
    """Match a city/neighborhood/location name fragment to a location_id."""
    lower = text.lower()
    for alias, location_id in LOCATION_ALIASES.items():
        if alias in lower:
            return location_id
    for location in RESTAURANT_LOCATIONS:
        if location.city.lower() in lower:
            return location.id
        name_tail = location.name.split()[-1].lower()
        if len(name_tail) >= 5 and name_tail in lower:
            return location.id
    return None
