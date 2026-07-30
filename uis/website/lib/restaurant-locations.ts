export type RestaurantCountry = "CO" | "US";

export interface RestaurantLocation {
  id: number;
  name: string;
  city: string;
  country: RestaurantCountry;
}

/** Brasaland restaurants — IDs 1–7 Colombia, 8–14 United States (matches API location_id). */
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

export function getLocationById(locationId: number): RestaurantLocation | undefined {
  return RESTAURANT_LOCATIONS.find((location) => location.id === locationId);
}

export function getLocationsForCountry(country: RestaurantCountry): RestaurantLocation[] {
  return RESTAURANT_LOCATIONS.filter((location) => location.country === country);
}

export function getCitiesForCountry(country: RestaurantCountry): string[] {
  const cities = new Set(
    getLocationsForCountry(country).map((location) => location.city),
  );
  return [...cities].sort((first, second) => first.localeCompare(second, "en"));
}

export function getAllCities(): string[] {
  const cities = new Set(RESTAURANT_LOCATIONS.map((location) => location.city));
  return [...cities].sort((first, second) => first.localeCompare(second, "en"));
}

export function getLocationsForCity(
  country: RestaurantCountry,
  city: string,
): RestaurantLocation[] {
  return getLocationsForCountry(country).filter((location) => location.city === city);
}

export function cityToSlug(city: string): string {
  return city
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .replace(/\s+/g, "-");
}

export function slugToCity(country: RestaurantCountry, slug: string): string | undefined {
  return getCitiesForCountry(country).find((city) => cityToSlug(city) === slug);
}
