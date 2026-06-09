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

export interface Price {
  USD: number;
  COP: number;
}

export type MenuCategory = "Meat" | "Side" | "Beverage" | "Dessert" | "Combo";
export type MenuItemStatus = "Active" | "Seasonal" | "Discontinued";

export interface MenuItem {
  id: string;
  name: string;
  category: MenuCategory;
  basePrice: Price;
  ingredientCost: Price;
  prepTimeMinutes: number;
  isAvailableInColombia: boolean;
  isAvailableInUSA: boolean;
  allergens: string[];
  status: MenuItemStatus;
}

export type PaymentMethod = "Cash" | "Credit card" | "Debit card" | "Digital wallet";

export interface SaleTransaction {
  id: string;
  locationId: string;
  itemId: string;
  quantity: number;
  totalPrice: Price;
  paymentMethod: PaymentMethod;
  timestamp: Date;
  waiterName: string;
}

export type LocationStatus = "Active" | "Temporarily closed" | "Under renovation";

export interface OperationsLocation {
  id: string;
  name: string;
  city: string;
  country: "Colombia" | "USA";
  openingYear: number;
  seatingCapacity: number;
  staffCount: number;
  monthlyRentCost: Price;
  averageMonthlyUtilities: Price;
  manager: string;
  status: LocationStatus;
}

export type WasteReason = "Expired" | "Cooking error" | "Customer return" | "Damage" | "Other";

export interface WasteRecord {
  id: string;
  locationId: string;
  itemId: string;
  quantity: number;
  reason: WasteReason;
  cost: Price;
  timestamp: Date;
  reportedBy: string;
}

export interface CountryMetrics {
  totalLocations: number;
  totalRevenue: Price;
  averageRevenuePerLocation: Price;
  totalSales: number;
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
    "Bogotá": ["Brasaland Usaquén", "Brasaland Chapinero", "Brasaland Zona Rosa"],
    Cali: ["Brasaland Granada", "Brasaland Ciudad Jardín", "Brasaland Unicentro"],
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
