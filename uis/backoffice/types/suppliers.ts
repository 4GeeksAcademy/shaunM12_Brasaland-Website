export type SupplierCategory =
  | "meat"
  | "vegetables_and_greens"
  | "sauces_and_seasonings"
  | "beverages"
  | "packaging"
  | "cleaning_products"
  | "dairy"
  | "carbon_and_fuel";

export type SupplierStatus = "active" | "suspended";
export type SupplierCountry = "Colombia" | "USA";
export type SupplierCurrency = "COP" | "USD";

export interface Supplier {
  id: number;
  name: string;
  country: SupplierCountry;
  categories: SupplierCategory[];
  rate_per_unit: number;
  currency: SupplierCurrency;
  rate_updated_at: string;
  status: SupplierStatus;
  contact_email?: string | null;
  notes?: string | null;
}

export interface SupplierCreateInput {
  name: string;
  country: SupplierCountry;
  categories: SupplierCategory[];
  rate_per_unit: number;
  currency: SupplierCurrency;
  status: SupplierStatus;
  contact_email?: string;
  notes?: string;
}

export interface ApiValidationError {
  detail?: string | Array<{ msg?: string; loc?: (string | number)[] }>;
}
