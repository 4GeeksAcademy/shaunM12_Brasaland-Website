import {
  CountryMetrics,
  LocationStatus,
  MenuCategory,
  MenuItem,
  OperationsLocation,
  PaymentMethod,
  Price,
  SaleTransaction,
  WasteReason,
  WasteRecord,
} from "./types";

type Currency = keyof Price;

const USD_TO_COP_RATE = 4000;

function round2(value: number): number {
  return Number(value.toFixed(2));
}

type SortOrder = "asc" | "desc";

export function filterSalesByLocation(sales: SaleTransaction[], locationId: string): SaleTransaction[] {
  return sales.filter((sale) => sale.locationId === locationId);
}

export function filterSalesByDateRange(
  sales: SaleTransaction[],
  startDate: Date,
  endDate: Date,
): SaleTransaction[] {
  return sales.filter((sale) => sale.timestamp >= startDate && sale.timestamp <= endDate);
}

export function filterMenuItemsByCategory(items: MenuItem[], category: MenuCategory): MenuItem[] {
  return items.filter((item) => item.category === category);
}

export function filterActiveLocations(locations: OperationsLocation[]): OperationsLocation[] {
  return locations.filter((location) => location.status === ("Active" satisfies LocationStatus));
}

export function sortLocationsByCapacity(
  locations: OperationsLocation[],
  order: SortOrder,
): OperationsLocation[] {
  return [...locations].sort((a, b) =>
    order === "asc" ? a.seatingCapacity - b.seatingCapacity : b.seatingCapacity - a.seatingCapacity,
  );
}

export function sortMenuItemsByPrice(
  items: MenuItem[],
  currency: Currency,
  order: SortOrder,
): MenuItem[] {
  return [...items].sort((a, b) =>
    order === "asc" ? a.basePrice[currency] - b.basePrice[currency] : b.basePrice[currency] - a.basePrice[currency],
  );
}

export function findLocationById(locations: OperationsLocation[], id: string): OperationsLocation | null {
  return locations.find((location) => location.id === id) ?? null;
}

export function findMenuItemByName(items: MenuItem[], name: string): MenuItem | null {
  const normalizedName = name.trim().toLowerCase();
  return items.find((item) => item.name.trim().toLowerCase() === normalizedName) ?? null;
}

export function binarySearchLocationByCapacity(
  sortedLocations: OperationsLocation[],
  targetCapacity: number,
): number {
  let left = 0;
  let right = sortedLocations.length - 1;

  while (left <= right) {
    const middle = Math.floor((left + right) / 2);
    const value = sortedLocations[middle].seatingCapacity;

    if (value === targetCapacity) {
      return middle;
    }

    if (value < targetCapacity) {
      left = middle + 1;
    } else {
      right = middle - 1;
    }
  }

  return -1;
}

export function validateMenuItem(item: MenuItem): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (!item.name.trim()) {
    errors.push("name must not be empty");
  }

  if (item.basePrice.USD <= 0 || item.basePrice.COP <= 0) {
    errors.push("both base prices must be > 0");
  }

  if (item.prepTimeMinutes <= 0 || item.prepTimeMinutes > 60) {
    errors.push("prepTimeMinutes must be > 0 and <= 60");
  }

  if (!item.isAvailableInColombia && !item.isAvailableInUSA) {
    errors.push("item must be available in at least one country");
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

export function validateSaleTransaction(sale: SaleTransaction): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (sale.quantity <= 0) {
    errors.push("quantity must be > 0");
  }

  if (sale.totalPrice.USD <= 0 || sale.totalPrice.COP <= 0) {
    errors.push("both price values must be > 0");
  }

  if (!sale.waiterName.trim()) {
    errors.push("waiterName must not be empty");
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

export function validateLocation(location: OperationsLocation): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  const currentYear = new Date().getUTCFullYear();

  if (location.openingYear < 2008 || location.openingYear > currentYear) {
    errors.push("openingYear must be between 2008 and current year");
  }

  if (location.seatingCapacity <= 0) {
    errors.push("seatingCapacity must be > 0");
  }

  if (location.staffCount <= 0) {
    errors.push("staffCount must be > 0");
  }

  if (location.monthlyRentCost.USD <= 0 || location.monthlyRentCost.COP <= 0) {
    errors.push("rent costs must be > 0");
  }

  if (location.averageMonthlyUtilities.USD <= 0 || location.averageMonthlyUtilities.COP <= 0) {
    errors.push("utility costs must be > 0");
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

function inSameUtcDate(value: Date, date: Date): boolean {
  return (
    value.getUTCFullYear() === date.getUTCFullYear() &&
    value.getUTCMonth() === date.getUTCMonth() &&
    value.getUTCDate() === date.getUTCDate()
  );
}

export function convertCurrency(amount: number, fromCurrency: Currency, toCurrency: Currency): number {
  if (fromCurrency === toCurrency) {
    return round2(amount);
  }

  if (fromCurrency === "USD" && toCurrency === "COP") {
    return round2(amount * USD_TO_COP_RATE);
  }

  return round2(amount / USD_TO_COP_RATE);
}

export function calculateDailyRevenue(
  sales: SaleTransaction[],
  date: Date,
  currency: Currency,
): number {
  const total = sales
    .filter((sale) => inSameUtcDate(sale.timestamp, date))
    .reduce((acc, sale) => acc + sale.totalPrice[currency], 0);

  return round2(total);
}

export function calculateWasteCost(
  wasteRecords: WasteRecord[],
  locationId: string,
  currency: Currency,
): number {
  const total = wasteRecords
    .filter((record) => record.locationId === locationId)
    .reduce((acc, record) => acc + record.cost[currency], 0);

  return round2(total);
}

export function calculateLocationMargin(
  sales: SaleTransaction[],
  menuItems: MenuItem[],
  locationId: string,
  currency: Currency,
): number {
  const itemMap = new Map(menuItems.map((item) => [item.id, item]));
  const locationSales = sales.filter((sale) => sale.locationId === locationId);

  const revenue = locationSales.reduce((acc, sale) => acc + sale.totalPrice[currency], 0);

  if (revenue <= 0) {
    return 0;
  }

  const ingredientCost = locationSales.reduce((acc, sale) => {
    const item = itemMap.get(sale.itemId);
    if (!item) {
      return acc;
    }

    return acc + item.ingredientCost[currency] * sale.quantity;
  }, 0);

  return round2(((revenue - ingredientCost) / revenue) * 100);
}

function summarizeLocationPerformanceInputs(
  locationId: string,
  sales: SaleTransaction[],
  wasteRecords: WasteRecord[],
  menuItems: MenuItem[],
): {
  revenueUSD: number;
  margin: number;
  wasteUSD: number;
  efficiencyRatio: number;
} {
  const locationSales = sales.filter((sale) => sale.locationId === locationId);
  const itemMap = new Map(menuItems.map((item) => [item.id, item]));

  const revenueUSD = locationSales.reduce((acc, sale) => acc + sale.totalPrice.USD, 0);
  const margin = calculateLocationMargin(sales, menuItems, locationId, "USD");
  const wasteUSD = calculateWasteCost(wasteRecords, locationId, "USD");

  const prepWeightedSum = locationSales.reduce((acc, sale) => {
    const item = itemMap.get(sale.itemId);
    if (!item) {
      return acc;
    }

    return acc + item.prepTimeMinutes * sale.quantity;
  }, 0);
  const totalQuantity = locationSales.reduce((acc, sale) => acc + sale.quantity, 0);
  const averagePrepTime = totalQuantity > 0 ? prepWeightedSum / totalQuantity : 60;
  const efficiencyRatio = Math.max(0, Math.min(1, (60 - averagePrepTime) / 60));

  return {
    revenueUSD,
    margin,
    wasteUSD,
    efficiencyRatio,
  };
}

export function scoreLocationPerformance(
  location: OperationsLocation,
  sales: SaleTransaction[],
  wasteRecords: WasteRecord[],
  menuItems: MenuItem[],
): number {
  const locationIds = new Set<string>([
    location.id,
    ...sales.map((sale) => sale.locationId),
    ...wasteRecords.map((record) => record.locationId),
  ]);

  const all = Array.from(locationIds).map((locationId) =>
    summarizeLocationPerformanceInputs(locationId, sales, wasteRecords, menuItems),
  );

  const current = summarizeLocationPerformanceInputs(location.id, sales, wasteRecords, menuItems);
  const maxRevenue = Math.max(...all.map((item) => item.revenueUSD), 1);
  const maxWaste = Math.max(...all.map((item) => item.wasteUSD), 1);

  const revenueScore = Math.min(40, (current.revenueUSD / maxRevenue) * 40);
  const efficiencyScore = current.efficiencyRatio * 30;
  const wasteScore = Math.max(0, 20 - (current.wasteUSD / maxWaste) * 20);
  const marginScore = Math.max(0, Math.min(10, (current.margin / 100) * 10));

  return round2(revenueScore + efficiencyScore + wasteScore + marginScore);
}

export function rankLocationsByPerformance(
  locations: OperationsLocation[],
  sales: SaleTransaction[],
  wasteRecords: WasteRecord[],
  menuItems: MenuItem[],
): Array<{ location: OperationsLocation; score: number }> {
  const details = locations.map((location) => ({
    location,
    inputs: summarizeLocationPerformanceInputs(location.id, sales, wasteRecords, menuItems),
  }));

  const maxRevenue = Math.max(...details.map((item) => item.inputs.revenueUSD), 1);
  const maxWaste = Math.max(...details.map((item) => item.inputs.wasteUSD), 1);

  return details
    .map(({ location, inputs }) => {
      const revenueScore = Math.min(40, (inputs.revenueUSD / maxRevenue) * 40);
      const efficiencyScore = inputs.efficiencyRatio * 30;
      const wasteScore = Math.max(0, 20 - (inputs.wasteUSD / maxWaste) * 20);
      const marginScore = Math.max(0, Math.min(10, (inputs.margin / 100) * 10));

      return {
        location,
        score: round2(revenueScore + efficiencyScore + wasteScore + marginScore),
      };
    })
    .sort((a, b) => b.score - a.score);
}

export function countSalesByPaymentMethod(sales: SaleTransaction[]): Record<PaymentMethod, number> {
  const count: Record<PaymentMethod, number> = {
    Cash: 0,
    "Credit card": 0,
    "Debit card": 0,
    "Digital wallet": 0,
  };

  sales.forEach((sale) => {
    count[sale.paymentMethod] += 1;
  });

  return count;
}

export function calculateAverageTicket(sales: SaleTransaction[], currency: Currency): number {
  if (sales.length === 0) {
    return 0;
  }

  const total = sales.reduce((acc, sale) => acc + sale.totalPrice[currency], 0);
  return round2(total / sales.length);
}

export function findTopSellingItems(
  sales: SaleTransaction[],
  menuItems: MenuItem[],
  topN: number,
): Array<{ item: MenuItem; totalSold: number }> {
  const soldByItemId = new Map<string, number>();
  sales.forEach((sale) => {
    soldByItemId.set(sale.itemId, (soldByItemId.get(sale.itemId) ?? 0) + sale.quantity);
  });

  const menuById = new Map(menuItems.map((item) => [item.id, item]));

  return Array.from(soldByItemId.entries())
    .map(([itemId, totalSold]) => {
      const item = menuById.get(itemId);
      if (!item) {
        return null;
      }

      return { item, totalSold };
    })
    .filter((row): row is { item: MenuItem; totalSold: number } => row !== null)
    .sort((a, b) => b.totalSold - a.totalSold)
    .slice(0, Math.max(0, topN));
}

export function groupWasteByReason(wasteRecords: WasteRecord[]): Record<WasteReason, WasteRecord[]> {
  const grouped: Record<WasteReason, WasteRecord[]> = {
    Expired: [],
    "Cooking error": [],
    "Customer return": [],
    Damage: [],
    Other: [],
  };

  wasteRecords.forEach((record) => {
    grouped[record.reason].push(record);
  });

  return grouped;
}

export function calculateCountryComparison(
  sales: SaleTransaction[],
  locations: OperationsLocation[],
): { Colombia: CountryMetrics; USA: CountryMetrics } {
  const countryByLocationId = new Map(locations.map((location) => [location.id, location.country]));

  const makeEmpty = (): CountryMetrics => ({
    totalLocations: 0,
    totalRevenue: { USD: 0, COP: 0 },
    averageRevenuePerLocation: { USD: 0, COP: 0 },
    totalSales: 0,
  });

  const result = {
    Colombia: makeEmpty(),
    USA: makeEmpty(),
  };

  locations.forEach((location) => {
    if (location.country === "Colombia") {
      result.Colombia.totalLocations += 1;
    } else {
      result.USA.totalLocations += 1;
    }
  });

  sales.forEach((sale) => {
    const country = countryByLocationId.get(sale.locationId);
    if (country === "Colombia") {
      result.Colombia.totalRevenue.USD = round2(result.Colombia.totalRevenue.USD + sale.totalPrice.USD);
      result.Colombia.totalRevenue.COP = round2(result.Colombia.totalRevenue.COP + sale.totalPrice.COP);
      result.Colombia.totalSales += 1;
    }

    if (country === "USA") {
      result.USA.totalRevenue.USD = round2(result.USA.totalRevenue.USD + sale.totalPrice.USD);
      result.USA.totalRevenue.COP = round2(result.USA.totalRevenue.COP + sale.totalPrice.COP);
      result.USA.totalSales += 1;
    }
  });

  if (result.Colombia.totalLocations > 0) {
    result.Colombia.averageRevenuePerLocation.USD = round2(
      result.Colombia.totalRevenue.USD / result.Colombia.totalLocations,
    );
    result.Colombia.averageRevenuePerLocation.COP = round2(
      result.Colombia.totalRevenue.COP / result.Colombia.totalLocations,
    );
  }

  if (result.USA.totalLocations > 0) {
    result.USA.averageRevenuePerLocation.USD = round2(result.USA.totalRevenue.USD / result.USA.totalLocations);
    result.USA.averageRevenuePerLocation.COP = round2(result.USA.totalRevenue.COP / result.USA.totalLocations);
  }

  return result;
}
