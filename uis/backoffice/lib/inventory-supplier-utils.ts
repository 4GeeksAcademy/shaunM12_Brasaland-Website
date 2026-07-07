import { ProductCountry } from "@/types/inventory";
import { Supplier, SupplierCategory, SupplierCountry } from "@/types/suppliers";

const INVENTORY_TO_SUPPLIER_CATEGORY: Record<string, SupplierCategory> = {
  meat: "meat",
  seafood: "meat",
  produce: "vegetables_and_greens",
  sauce: "sauces_and_seasonings",
  beverage: "beverages",
  packaging: "packaging",
  cleaning: "cleaning_products",
};

export function locationToSupplierCountry(locationId: number): SupplierCountry {
  return locationId <= 9 ? "Colombia" : "USA";
}

export function inventoryCategoryToSupplierCategory(
  category: string,
): SupplierCategory | undefined {
  return INVENTORY_TO_SUPPLIER_CATEGORY[category];
}

export function filterSuppliersForInbound(
  suppliers: Supplier[],
  category: string,
  locationId: number,
): Supplier[] {
  const country = locationToSupplierCountry(locationId);
  const supplierCategory = inventoryCategoryToSupplierCategory(category);
  return suppliers.filter((supplier) => {
    if (supplier.country !== country || supplier.status !== "active") {
      return false;
    }
    if (supplierCategory === undefined) {
      return true;
    }
    return supplier.categories.includes(supplierCategory);
  });
}

export function pickDefaultSupplier(
  suppliers: Supplier[],
  category: string,
  locationId: number,
): Supplier | undefined {
  const matches = filterSuppliersForInbound(suppliers, category, locationId);
  return matches[0];
}

export function productCountryToSupplierCountry(
  country: ProductCountry | string,
): SupplierCountry {
  return country === "US" ? "USA" : "Colombia";
}
