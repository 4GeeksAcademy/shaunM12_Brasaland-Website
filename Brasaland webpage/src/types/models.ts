export type Country = "Colombia" | "United States";

export type City = "Medellín" | "Bogotá" | "Cali" | "Miami" | "Orlando";

export type DietaryPreference =
  | "No restrictions"
  | "Vegetarian"
  | "Gluten-free"
  | "Other";

export type DiscoveryChannel =
  | "Social media"
  | "Recommendation"
  | "Walked by"
  | "Internet search"
  | "Other";

export interface BrasaLocation {
  id: string;
  name: string;
  country: Country;
  city: City;
}

export interface BrasaPointsRegistration {
  fullName: string;
  email: string;
  phone: string;
  country: Country;
  city: City;
  favoriteBrasalandLocation?: string;
  dietaryPreferences: DietaryPreference[];
  howDidYouFindUs: DiscoveryChannel;
  dateOfBirth: string;
  acceptsProgramTerms: boolean;
  wantsEmailOffers: boolean;
  createdAt: string;
}

export interface RegistrationValidationErrors {
  fullName?: string;
  email?: string;
  phone?: string;
  country?: string;
  city?: string;
  favoriteBrasalandLocation?: string;
  dietaryPreferences?: string;
  howDidYouFindUs?: string;
  dateOfBirth?: string;
  acceptsProgramTerms?: string;
}

export interface RegistrationValidationResult {
  valid: boolean;
  errors: RegistrationValidationErrors;
}

export const COUNTRY_TO_CITIES: Record<Country, City[]> = {
  Colombia: ["Medellín", "Bogotá", "Cali"],
  "United States": ["Miami", "Orlando"],
};

export const LOCATIONS_BY_COUNTRY_AND_CITY: Record<Country, Record<City, string[]>> = {
  Colombia: {
    "Medellín": [
      "Brasaland El Poblado",
      "Brasaland Laureles",
      "Brasaland Envigado",
      "Brasaland Sabaneta",
    ],
    "Bogotá": [
      "Brasaland Usaquén",
      "Brasaland Chapinero",
      "Brasaland Zona Rosa",
    ],
    Cali: [
      "Brasaland Granada",
      "Brasaland Ciudad Jardín",
      "Brasaland Unicentro",
    ],
    Miami: [],
    Orlando: [],
  },
  "United States": {
    "Medellín": [],
    "Bogotá": [],
    Cali: [],
    Miami: ["Brasaland Brickell", "Brasaland Coral Gables"],
    Orlando: ["Brasaland Downtown", "Brasaland International Drive"],
  },
};
