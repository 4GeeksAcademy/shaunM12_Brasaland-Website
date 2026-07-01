"""Canonical Brasaland chain-wide inventory catalogue for demo seeding.

One unified menu across all 14 restaurants (Colombia + Florida). Stock levels
are seeded per location; catalogue membership is chain-wide.
"""

from __future__ import annotations

from typing import Any

from .constants import country_for_location

IngredientRow = dict[str, Any]

# fmt: off
INGREDIENTS: list[IngredientRow] = [
    # --- Context-11 core (evaluator demo) ------------------------------------
    {"name": "Beef brisket", "sku": "BRS-BEEF-001", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Pork ribs", "sku": "BRS-PORK-001", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Chimichurri sauce", "sku": "BRS-SAUCE-001", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "House BBQ sauce", "sku": "BRS-SAUCE-002", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Yuca (cassava)", "sku": "BRS-PROD-001", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Takeaway box (M)", "sku": "BRS-PKG-001", "unit": "unit", "category": "packaging", "country": "CO"},
    # --- Meat ----------------------------------------------------------------
    {"name": "Short rib", "sku": "BRS-BEEF-002", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Chicken thigh (boneless)", "sku": "BRS-CHKN-001", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Chorizo sausage", "sku": "BRS-CHOR-001", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Ground beef blend", "sku": "BRS-BEEF-003", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Baby back ribs", "sku": "BRS-PORK-002", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Picanha (top sirloin cap)", "sku": "BRS-BEEF-004", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Entraña (skirt steak)", "sku": "BRS-BEEF-005", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Morcilla (blood sausage)", "sku": "BRS-PORK-003", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Chicharrón pork belly", "sku": "BRS-PORK-004", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Flank steak (marinated)", "sku": "BRS-BEEF-007", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Chicken wings (whole)", "sku": "BRS-CHKN-002", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Lamb shoulder (bone-in)", "sku": "BRS-LAMB-001", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Beef tenderloin", "sku": "BRS-BEEF-008", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Turkey thigh (boneless)", "sku": "BRS-CHKN-003", "unit": "kg", "category": "meat", "country": "CO"},
    {"name": "Duck breast", "sku": "BRS-DUCK-001", "unit": "kg", "category": "meat", "country": "CO"},
    # --- Seafood -------------------------------------------------------------
    {"name": "Red snapper (pargo rojo)", "sku": "BRS-FISH-001", "unit": "kg", "category": "seafood", "country": "CO"},
    {"name": "Tilapia fillet", "sku": "BRS-FISH-002", "unit": "kg", "category": "seafood", "country": "CO"},
    {"name": "Mahi-mahi fillet", "sku": "BRS-FISH-003", "unit": "kg", "category": "seafood", "country": "CO"},
    {"name": "Shrimp (peeled, raw)", "sku": "BRS-SHR-001", "unit": "kg", "category": "seafood", "country": "CO"},
    {"name": "Squid rings (calamari)", "sku": "BRS-SQD-001", "unit": "kg", "category": "seafood", "country": "CO"},
    {"name": "Octopus tentacles (cooked)", "sku": "BRS-OCT-001", "unit": "kg", "category": "seafood", "country": "CO", "is_active": False},
    {"name": "Mixed ceviche fish blend", "sku": "BRS-FISH-004", "unit": "kg", "category": "seafood", "country": "CO"},
    {"name": "Clams (almejas)", "sku": "BRS-SHELL-001", "unit": "kg", "category": "seafood", "country": "CO"},
    {"name": "Grouper fillet", "sku": "BRS-FISH-005", "unit": "kg", "category": "seafood", "country": "CO"},
    {"name": "Salmon fillet (Atlantic)", "sku": "BRS-FISH-006", "unit": "kg", "category": "seafood", "country": "CO"},
    {"name": "Snow crab legs (cluster)", "sku": "BRS-CRAB-001", "unit": "kg", "category": "seafood", "country": "CO", "is_active": False},
    {"name": "Sea scallops (dry)", "sku": "BRS-SCALL-001", "unit": "kg", "category": "seafood", "country": "CO"},
    {"name": "Conch meat (diced)", "sku": "BRS-CONCH-001", "unit": "kg", "category": "seafood", "country": "CO"},
    {"name": "Catfish fillet", "sku": "BRS-FISH-007", "unit": "kg", "category": "seafood", "country": "CO", "is_active": False},
    {"name": "Mixed seafood paella blend", "sku": "BRS-SEA-001", "unit": "kg", "category": "seafood", "country": "CO"},
    {"name": "Tuna steak", "sku": "BRS-FISH-008", "unit": "kg", "category": "seafood", "country": "CO"},
    {"name": "Langoustines", "sku": "BRS-SHR-003", "unit": "kg", "category": "seafood", "country": "CO"},
    # --- Produce -------------------------------------------------------------
    {"name": "White onion", "sku": "BRS-PROD-002", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Cilantro", "sku": "BRS-PROD-003", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Plantain", "sku": "BRS-PROD-004", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Russet potato", "sku": "BRS-PROD-005", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Limes", "sku": "BRS-PROD-006", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Masarepa (arepa flour)", "sku": "BRS-PROD-007", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Hass avocado", "sku": "BRS-PROD-008", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Roma tomato", "sku": "BRS-PROD-009", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Ají amarillo pepper", "sku": "BRS-PROD-010", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Plátano verde (green plantain)", "sku": "BRS-PROD-011", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Sweet corn (cob)", "sku": "BRS-PROD-012", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Black beans (dry)", "sku": "BRS-PROD-013", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Jalapeño pepper", "sku": "BRS-PROD-015", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Red bell pepper", "sku": "BRS-PROD-016", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Garlic", "sku": "BRS-PROD-018", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Scallions", "sku": "BRS-PROD-019", "unit": "kg", "category": "produce", "country": "CO"},
    {"name": "Fresh ginger", "sku": "BRS-PROD-020", "unit": "kg", "category": "produce", "country": "CO"},
    # --- Sauces --------------------------------------------------------------
    {"name": "Aji sauce", "sku": "BRS-SAUCE-003", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Garlic-cilantro marinade", "sku": "BRS-SAUCE-004", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Mustard BBQ glaze", "sku": "BRS-SAUCE-005", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Hogao (tomato-onion sofrito)", "sku": "BRS-SAUCE-006", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Ají picante (house hot sauce)", "sku": "BRS-SAUCE-007", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Salsa criolla (onion-lime)", "sku": "BRS-SAUCE-008", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Mojo criollo marinade", "sku": "BRS-SAUCE-009", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Guacamole (prepared batch)", "sku": "BRS-SAUCE-010", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Salsa verde (tomatillo)", "sku": "BRS-SAUCE-011", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Mojo marinade (citrus-garlic)", "sku": "BRS-SAUCE-012", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Chipotle crema", "sku": "BRS-SAUCE-013", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Ceviche leche de tigre (batch)", "sku": "BRS-SAUCE-014", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Ajillo garlic butter (seafood)", "sku": "BRS-SAUCE-015", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Mojo verde (cilantro-lime)", "sku": "BRS-SAUCE-016", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Coconut shrimp dip", "sku": "BRS-SAUCE-017", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Garlic aioli", "sku": "BRS-SAUCE-018", "unit": "litre", "category": "sauce", "country": "CO"},
    {"name": "Tartar sauce", "sku": "BRS-SAUCE-019", "unit": "litre", "category": "sauce", "country": "CO"},
    # --- Beverages -----------------------------------------------------------
    {"name": "Passion fruit juice (concentrate)", "sku": "BRS-BEV-001", "unit": "litre", "category": "beverage", "country": "CO"},
    {"name": "Colombian coffee (brewed batch)", "sku": "BRS-BEV-002", "unit": "litre", "category": "beverage", "country": "CO"},
    {"name": "Sweet tea (batch)", "sku": "BRS-BEV-003", "unit": "litre", "category": "beverage", "country": "CO"},
    {"name": "Lemonade (batch)", "sku": "BRS-BEV-004", "unit": "litre", "category": "beverage", "country": "CO"},
    {"name": "Aguapanela (panela drink batch)", "sku": "BRS-BEV-006", "unit": "litre", "category": "beverage", "country": "CO"},
    {"name": "Limonada de coco", "sku": "BRS-BEV-007", "unit": "litre", "category": "beverage", "country": "CO"},
    {"name": "Mango jugo (batch)", "sku": "BRS-BEV-008", "unit": "litre", "category": "beverage", "country": "CO"},
    {"name": "Malta (non-alcoholic)", "sku": "BRS-BEV-009", "unit": "litre", "category": "beverage", "country": "CO"},
    {"name": "Horchata (rice-cinnamon batch)", "sku": "BRS-BEV-010", "unit": "litre", "category": "beverage", "country": "CO"},
    {"name": "Tamarind agua fresca (batch)", "sku": "BRS-BEV-011", "unit": "litre", "category": "beverage", "country": "CO"},
    {"name": "Mango agua fresca (batch)", "sku": "BRS-BEV-012", "unit": "litre", "category": "beverage", "country": "CO"},
    {"name": "Sweet tea with lime (batch)", "sku": "BRS-BEV-013", "unit": "litre", "category": "beverage", "country": "CO"},
    {"name": "Michelada mix (batch)", "sku": "BRS-BEV-014", "unit": "litre", "category": "beverage", "country": "CO"},
    {"name": "Cola syrup concentrate", "sku": "BRS-BEV-015", "unit": "litre", "category": "beverage", "country": "CO"},
    # --- Packaging -----------------------------------------------------------
    {"name": "Takeaway box (S)", "sku": "BRS-PKG-002", "unit": "unit", "category": "packaging", "country": "CO"},
    {"name": "Takeaway box (L)", "sku": "BRS-PKG-003", "unit": "unit", "category": "packaging", "country": "CO"},
    {"name": "Paper cup 12oz", "sku": "BRS-PKG-006", "unit": "unit", "category": "packaging", "country": "CO"},
    {"name": "Paper cup 16oz", "sku": "BRS-PKG-007", "unit": "unit", "category": "packaging", "country": "CO"},
    {"name": "Cup lid 12–16oz (flat)", "sku": "BRS-PKG-008", "unit": "unit", "category": "packaging", "country": "CO"},
    {"name": "Cup lid 12oz", "sku": "BRS-PKG-010", "unit": "unit", "category": "packaging", "country": "CO", "is_active": False},
    {"name": "Kraft paper bag (small)", "sku": "BRS-PKG-011", "unit": "unit", "category": "packaging", "country": "CO"},
    {"name": "Kraft paper bag (large)", "sku": "BRS-PKG-012", "unit": "unit", "category": "packaging", "country": "CO"},
    {"name": "Wooden cutlery set", "sku": "BRS-PKG-013", "unit": "unit", "category": "packaging", "country": "CO"},
    {"name": "Napkin pack (100)", "sku": "BRS-PKG-015", "unit": "unit", "category": "packaging", "country": "CO"},
    {"name": "Aluminium foil sheet (pre-cut)", "sku": "BRS-PKG-017", "unit": "unit", "category": "packaging", "country": "CO"},
    {"name": "Compostable straws (pack)", "sku": "BRS-PKG-018", "unit": "unit", "category": "packaging", "country": "CO"},
    {"name": "Salad bowl (L)", "sku": "BRS-PKG-019", "unit": "unit", "category": "packaging", "country": "CO"},
    # --- Cleaning ------------------------------------------------------------
    {"name": "Degreaser (kitchen)", "sku": "BRS-CLN-001", "unit": "litre", "category": "cleaning", "country": "CO"},
    {"name": "Sanitizer solution", "sku": "BRS-CLN-002", "unit": "litre", "category": "cleaning", "country": "CO"},
    {"name": "Grill cleaner", "sku": "BRS-CLN-003", "unit": "litre", "category": "cleaning", "country": "CO"},
    {"name": "Hand soap (refill)", "sku": "BRS-CLN-004", "unit": "litre", "category": "cleaning", "country": "CO"},
    {"name": "Glass cleaner", "sku": "BRS-CLN-005", "unit": "litre", "category": "cleaning", "country": "CO"},
    {"name": "Floor degreaser", "sku": "BRS-CLN-006", "unit": "litre", "category": "cleaning", "country": "CO"},
]
# fmt: on

DemoOrderSpec = dict[str, Any]

ALL_LOCATIONS = range(1, 15)

# Context-11 evaluator orders — do not change quantities (pytest / acceptance).
CONTEXT11_DEMO_ORDERS: list[DemoOrderSpec] = [
    {"kind": "inbound", "sku": "BRS-BEEF-001", "quantity": 50, "supplier_name": "Carnes del Valle S.A.", "location_id": 1},
    {"kind": "inbound", "sku": "BRS-BEEF-001", "quantity": 30, "supplier_name": "Carnes del Valle S.A.", "location_id": 1},
    {"kind": "inbound", "sku": "BRS-PORK-001", "quantity": 40, "supplier_name": "MiamiMeat Co.", "location_id": 7},
    {"kind": "inbound", "sku": "BRS-SAUCE-001", "quantity": 20, "supplier_name": "Salsas Artesanales Ltda.", "location_id": 2},
    {"kind": "outbound", "sku": "BRS-BEEF-001", "quantity": 25, "reason": "consumption", "location_id": 1},
    {"kind": "outbound", "sku": "BRS-BEEF-001", "quantity": 5, "reason": "waste", "location_id": 1},
    {"kind": "outbound", "sku": "BRS-PORK-001", "quantity": 10, "reason": "consumption", "location_id": 7},
]

EXPLICIT_STOCK_ORDERS: list[DemoOrderSpec] = [
    {"kind": "inbound", "sku": "BRS-SHR-001", "quantity": 25, "supplier_name": "Pacífico Seafood S.A.", "location_id": 3},
    {"kind": "inbound", "sku": "BRS-FISH-005", "quantity": 18, "supplier_name": "Florida Gulf Seafood Co.", "location_id": 8},
    {"kind": "inbound", "sku": "BRS-PKG-006", "quantity": 500, "supplier_name": "Empaques Andinos Ltda.", "location_id": 1},
    {"kind": "inbound", "sku": "BRS-PKG-013", "quantity": 1200, "supplier_name": "Empaques Andinos Ltda.", "location_id": 1},
    {"kind": "outbound", "sku": "BRS-SHR-001", "quantity": 5, "reason": "consumption", "location_id": 3},
]

_CONTEXT_SKUS = frozenset(spec["sku"] for spec in CONTEXT11_DEMO_ORDERS)


def _supplier_for(category: str, location_id: int) -> str:
    """Procurement partner for a category at a given restaurant."""
    country = country_for_location(location_id)
    if category == "meat":
        return "Carnes del Valle S.A." if country == "CO" else "MiamiMeat Co."
    if category == "seafood":
        return (
            "Pacífico Seafood S.A."
            if country == "CO"
            else "Florida Gulf Seafood Co."
        )
    if category == "produce":
        return "Frutas del Campo Ltda." if country == "CO" else "Sunrise Produce Co."
    if category == "sauce":
        return (
            "Salsas Artesanales Ltda."
            if country == "CO"
            else "Gulf Coast Flavors Inc."
        )
    if category == "beverage":
        return "Bebidas Andinas S.A." if country == "CO" else "Florida Beverage Supply"
    if category == "packaging":
        return "Empaques Andinos Ltda." if country == "CO" else "PackRight USA"
    return "Brasaland Facilities Supply"


def _explicit_location_skus() -> set[tuple[int, str]]:
    return {
        (spec["location_id"], spec["sku"])
        for spec in CONTEXT11_DEMO_ORDERS + EXPLICIT_STOCK_ORDERS
    }


def _stock_tier(location_id: int, sku: str) -> str:
    """~82% healthy, ~10% low, ~8% out at each restaurant."""
    bucket = hash((location_id, sku)) % 100
    if bucket < 8:
        return "out"
    if bucket < 18:
        return "low"
    return "healthy"


def _tier_quantity(tier: str, unit: str, sku: str) -> float | None:
    if tier == "out":
        return None
    seed = hash(sku) % 100
    if tier == "low":
        return float(2 + seed % 8)
    if unit == "unit":
        return float(150 + seed % 301)
    return float(20 + seed % 36)


def build_per_location_stock_orders() -> list[DemoOrderSpec]:
    """Inbound rows at every restaurant — each site gets its own healthy/low/out mix."""
    covered = _explicit_location_skus()
    orders: list[DemoOrderSpec] = []
    for ingredient in INGREDIENTS:
        sku = ingredient["sku"]
        if sku in _CONTEXT_SKUS:
            continue
        category = ingredient["category"]
        for location_id in ALL_LOCATIONS:
            if (location_id, sku) in covered:
                continue
            tier = _stock_tier(location_id, sku)
            quantity = _tier_quantity(tier, ingredient["unit"], sku)
            if quantity is None:
                continue
            orders.append(
                {
                    "kind": "inbound",
                    "sku": sku,
                    "quantity": quantity,
                    "supplier_name": _supplier_for(category, location_id),
                    "location_id": location_id,
                }
            )
    return orders


DEMO_ORDERS: list[DemoOrderSpec] = (
    CONTEXT11_DEMO_ORDERS + EXPLICIT_STOCK_ORDERS + build_per_location_stock_orders()
)
