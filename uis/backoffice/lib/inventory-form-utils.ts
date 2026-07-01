import { Product, ProductCountry } from "@/types/inventory";

export interface RestaurantLocation {
  id: number;
  name: string;
  city: string;
  country: ProductCountry;
}

/** Brasaland restaurants — IDs 1–7 Colombia, 8–14 Florida (matches API location_id). */
export const RESTAURANT_LOCATIONS: RestaurantLocation[] = [
  { id: 1, name: "Brasaland Medellín Centro", city: "Medellín", country: "CO" },
  { id: 2, name: "Brasaland Medellín Laureles", city: "Medellín", country: "CO" },
  { id: 3, name: "Brasaland Medellín Envigado", city: "Envigado", country: "CO" },
  { id: 4, name: "Brasaland Bogotá Chapinero", city: "Bogotá", country: "CO" },
  { id: 5, name: "Brasaland Bogotá Usaquén", city: "Bogotá", country: "CO" },
  { id: 6, name: "Brasaland Cali Granada", city: "Cali", country: "CO" },
  { id: 7, name: "Brasaland Barranquilla Norte", city: "Barranquilla", country: "CO" },
  { id: 8, name: "Brasaland Miami Beach", city: "Miami Beach", country: "US" },
  { id: 9, name: "Brasaland Miami Brickell", city: "Miami", country: "US" },
  { id: 10, name: "Brasaland Fort Lauderdale", city: "Fort Lauderdale", country: "US" },
  { id: 11, name: "Brasaland Orlando I-Drive", city: "Orlando", country: "US" },
  { id: 12, name: "Brasaland Tampa Bay", city: "Tampa", country: "US" },
  { id: 13, name: "Brasaland West Palm Beach", city: "West Palm Beach", country: "US" },
  { id: 14, name: "Brasaland Jacksonville", city: "Jacksonville", country: "US" },
];

export function getLocationsForCountry(country: ProductCountry): RestaurantLocation[] {
  return RESTAURANT_LOCATIONS.filter((location) => location.country === country);
}

export function getLocationById(locationId: number): RestaurantLocation | undefined {
  return RESTAURANT_LOCATIONS.find((location) => location.id === locationId);
}

export function formatLocationLabel(locationId: number): string {
  const location = getLocationById(locationId);
  if (!location) {
    return `Location ${locationId}`;
  }
  return `${location.name} — ${location.city}`;
}

/** Default procurement supplier for a category at a restaurant (mirrors API seed). */
export function getSupplierForLocation(
  category: string,
  locationId: number,
): string {
  const location = getLocationById(locationId);
  const country = location?.country ?? "CO";
  if (category === "meat") {
    return country === "CO" ? "Carnes del Valle S.A." : "MiamiMeat Co.";
  }
  if (category === "seafood") {
    return country === "CO" ? "Pacífico Seafood S.A." : "Florida Gulf Seafood Co.";
  }
  if (category === "produce") {
    return country === "CO" ? "Frutas del Campo Ltda." : "Sunrise Produce Co.";
  }
  if (category === "sauce") {
    return country === "CO" ? "Salsas Artesanales Ltda." : "Gulf Coast Flavors Inc.";
  }
  if (category === "beverage") {
    return country === "CO" ? "Bebidas Andinas S.A." : "Florida Beverage Supply";
  }
  if (category === "packaging") {
    return country === "CO" ? "Empaques Andinos Ltda." : "PackRight USA";
  }
  return "Brasaland Facilities Supply";
}

/** @deprecated Use getSupplierForLocation with the receiving restaurant id. */
export function getSupplierForProduct(product: Product): string {
  return getSupplierForLocation(product.category, 1);
}

export interface QuantityInputConstraints {
  min: number;
  step: number;
  placeholder: string;
}

/** Step/min for quantity fields based on how the product is measured. */
export function getQuantityConstraints(unit: string | undefined): QuantityInputConstraints {
  if (unit === "unit") {
    return { min: 1, step: 1, placeholder: "Whole units (e.g. 50 boxes)" };
  }
  if (unit === "litre") {
    return { min: 0.5, step: 0.5, placeholder: "Litres in 0.5 steps" };
  }
  return { min: 0.5, step: 0.5, placeholder: "Kilograms in 0.5 steps" };
}

export function isValidQuantity(value: number, unit: string | undefined): boolean {
  if (!Number.isFinite(value) || value <= 0) {
    return false;
  }
  const { min, step } = getQuantityConstraints(unit);
  if (value < min) {
    return false;
  }
  const steps = Math.round((value - min) / step);
  const reconstructed = min + steps * step;
  return Math.abs(reconstructed - value) < 0.0001;
}
