import { ExitReason } from "@/types/inventory";

export const MIN_LOCATION_ID = 1;
export const MAX_LOCATION_ID = 14;
/** Filter sentinel for order history — show every restaurant. */
export const ALL_RESTAURANTS_LOCATION_ID = 0;

export {
  RESTAURANT_LOCATIONS,
  formatLocationLabel,
  getLocationById,
  getLocationsForCountry,
  getQuantityConstraints,
  getSupplierForLocation,
  getSupplierForProduct,
  isValidQuantity,
} from "@/lib/inventory-form-utils";

export const EXIT_REASON_OPTIONS: { value: ExitReason; label: string }[] = [
  { value: "consumption", label: "Consumption" },
  { value: "waste", label: "Waste" },
];

export const COUNTRY_LABELS: Record<string, string> = {
  CO: "Colombia",
  US: "United States",
};

export const CATEGORY_LABELS: Record<string, string> = {
  meat: "Meat",
  seafood: "Seafood",
  produce: "Produce",
  sauce: "Sauce",
  beverage: "Beverage",
  packaging: "Packaging",
  cleaning: "Cleaning",
};

/** Display order for product catalogue grouping. */
export const CATEGORY_ORDER: string[] = [
  "meat",
  "seafood",
  "produce",
  "sauce",
  "beverage",
  "packaging",
  "cleaning",
];

export const INPUT_CLASS =
  "mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)] outline-none transition focus:border-[color:var(--bo-focus-border)] focus:ring-4 focus:ring-[color:var(--bo-focus-ring)]";

export const LABEL_CLASS = "text-xs font-semibold uppercase tracking-[0.08em] bo-muted";
