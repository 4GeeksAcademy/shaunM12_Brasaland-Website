import {
  Supplier,
  SupplierCategory,
  SupplierCountry,
  SupplierCreateInput,
  SupplierCurrency,
  SupplierStatus,
} from "@/types/suppliers";

export const SUPPLIER_CATEGORIES: SupplierCategory[] = [
  "meat",
  "vegetables_and_greens",
  "sauces_and_seasonings",
  "beverages",
  "packaging",
  "cleaning_products",
  "dairy",
  "carbon_and_fuel",
];

export const CATEGORY_LABELS: Record<SupplierCategory, string> = {
  meat: "Meat",
  vegetables_and_greens: "Vegetables & greens",
  sauces_and_seasonings: "Sauces & seasonings",
  beverages: "Beverages",
  packaging: "Packaging",
  cleaning_products: "Cleaning products",
  dairy: "Dairy",
  carbon_and_fuel: "Charcoal & fuel",
};

export const COUNTRY_OPTIONS: SupplierCountry[] = ["Colombia", "USA"];

export const STATUS_LABELS: Record<SupplierStatus, string> = {
  active: "Active",
  suspended: "Suspended",
};

export function currencyForCountry(country: SupplierCountry): SupplierCurrency {
  return country === "Colombia" ? "COP" : "USD";
}

export function formatSupplierRate(rate: number, currency: SupplierCurrency): string {
  if (currency === "USD") {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(rate);
  }

  return `${new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 }).format(rate)} COP`;
}

export function formatCategoryList(categories: SupplierCategory[]): string {
  return categories.map((category) => CATEGORY_LABELS[category]).join(", ");
}

export const EMPTY_SUPPLIER_FORM: SupplierCreateInput = {
  name: "",
  country: "Colombia",
  categories: ["meat"],
  rate_per_unit: 0,
  currency: "COP",
  status: "active",
  contact_email: "",
  notes: "",
};

export type { Supplier, SupplierCreateInput };
