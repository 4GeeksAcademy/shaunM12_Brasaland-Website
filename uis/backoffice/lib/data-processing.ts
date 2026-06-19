import {
  buildLocationDistributionReport,
  calculateAverageTicket,
  calculateCountryComparison,
  calculateDailyRevenue,
  calculateLocationMargin,
  calculateWasteCost,
  countSalesByPaymentMethod,
  filterActiveLocations,
  filterMenuItemsByCategory,
  filterSalesByDateRange,
  filterSalesByLocation,
  findLocationById,
  findMenuItemByName,
  findTopSellingItems,
  groupWasteByReason,
  rankLocationsByPerformance,
  sortLocationsByCapacity,
  validateLocation,
  validateMenuItem,
  validateSaleTransaction,
  convertCurrency,
  binarySearchLocationByCapacity,
  SAMPLE_LOCATIONS,
  SAMPLE_MENU_ITEMS,
  SAMPLE_OPERATIONS_LOCATIONS,
  SAMPLE_SALES,
  SAMPLE_WASTE,
} from "../app/data-processing/data-processing-core";
import type { Country } from "../app/data-processing/data-processing-core";

const ALL_COUNTRIES_FILTER = "All" as const;

type CountryFilter = Country | typeof ALL_COUNTRIES_FILTER;

export interface ChartDatum {
  label: string;
  value: number;
}

export interface DataProcessingDashboard {
  countryFilter: CountryFilter;
  referenceDate: string;
  totalLocations: number;
  locationsByCountry: ChartDatum[];
  locationsByCity: ChartDatum[];
  dailyRevenueUSD: number;
  dailyRevenueCOP: number;
  averageTicketUSD: number;
  wasteCostUSD: number;
  miamiMarginPercent: number;
  paymentMethodMix: ChartDatum[];
  topSellingItems: ChartDatum[];
  wasteByReason: ChartDatum[];
  locationPerformance: ChartDatum[];
  countryRevenueUSD: ChartDatum[];
  revenueUsdAsCop: number;
  salesByLocationCount: number;
  salesOnDateCount: number;
  meatItemsCount: number;
  activeLocationsCount: number;
  locationByIdFound: boolean;
  menuItemByNameFound: boolean;
  capacityBinarySearchIndex: number;
  menuValidationPassed: boolean;
  saleValidationPassed: boolean;
  locationValidationPassed: boolean;
}

function toChartData<T extends string>(
  source: Record<T, number>,
  includeZeroValues = false,
): ChartDatum[] {
  return (Object.entries(source) as Array<[T, number]>)
    .filter(([, value]) => includeZeroValues || value > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([label, value]) => ({ label, value }));
}

function normalizeCountryFilter(value?: string): CountryFilter {
  if (value === "Colombia" || value === "United States") {
    return value;
  }

  return ALL_COUNTRIES_FILTER;
}

function normalizeReferenceDate(value?: string): Date {
  if (!value) {
    return new Date("2026-04-23T00:00:00.000Z");
  }

  const parsed = new Date(`${value}T00:00:00.000Z`);
  if (Number.isNaN(parsed.getTime())) {
    return new Date("2026-04-23T00:00:00.000Z");
  }

  return parsed;
}

function filterByCountry<T extends { country: Country }>(
  rows: T[],
  countryFilter: CountryFilter,
): T[] {
  if (countryFilter === ALL_COUNTRIES_FILTER) {
    return rows;
  }

  return rows.filter((row) => row.country === countryFilter);
}

export function buildDataProcessingDashboard(options?: {
  country?: string;
  referenceDate?: string;
}): DataProcessingDashboard {
  const countryFilter = normalizeCountryFilter(options?.country);
  const referenceDate = normalizeReferenceDate(options?.referenceDate);
  const locations = filterByCountry(SAMPLE_LOCATIONS, countryFilter);

  const locationReport = buildLocationDistributionReport(locations);

  const reportDate = new Date(`${referenceDate.toISOString().slice(0, 10)}T00:00:00.000Z`);
  const rankedLocations = rankLocationsByPerformance(
    SAMPLE_OPERATIONS_LOCATIONS,
    SAMPLE_SALES,
    SAMPLE_WASTE,
    SAMPLE_MENU_ITEMS,
  );
  const countryComparison = calculateCountryComparison(SAMPLE_SALES, SAMPLE_OPERATIONS_LOCATIONS);
  const paymentMethodMix = countSalesByPaymentMethod(SAMPLE_SALES);
  const wasteByReason = groupWasteByReason(SAMPLE_WASTE);

  const miamiLocationId = "LOC-MIAMI-01";
  const dailyStart = new Date(`${referenceDate.toISOString().slice(0, 10)}T00:00:00.000Z`);
  const dailyEnd = new Date(`${referenceDate.toISOString().slice(0, 10)}T23:59:59.999Z`);
  const sortedLocationsByCapacity = sortLocationsByCapacity(SAMPLE_OPERATIONS_LOCATIONS, "asc");
  const capacityTarget = sortedLocationsByCapacity[0]?.seatingCapacity ?? 0;

  return {
    countryFilter,
    referenceDate: referenceDate.toISOString().slice(0, 10),
    totalLocations: locationReport.totalLocations,
    locationsByCountry: toChartData(locationReport.locationsByCountry, true),
    locationsByCity: toChartData(locationReport.locationsByCity),
    dailyRevenueUSD: calculateDailyRevenue(SAMPLE_SALES, reportDate, "USD"),
    dailyRevenueCOP: calculateDailyRevenue(SAMPLE_SALES, reportDate, "COP"),
    averageTicketUSD: calculateAverageTicket(SAMPLE_SALES, "USD"),
    wasteCostUSD: calculateWasteCost(SAMPLE_WASTE, miamiLocationId, "USD"),
    miamiMarginPercent: calculateLocationMargin(
      SAMPLE_SALES,
      SAMPLE_MENU_ITEMS,
      miamiLocationId,
      "USD",
    ),
    paymentMethodMix: toChartData(paymentMethodMix),
    topSellingItems: findTopSellingItems(SAMPLE_SALES, SAMPLE_MENU_ITEMS, 3).map((row) => ({
      label: row.item.name,
      value: row.totalSold,
    })),
    wasteByReason: (Object.entries(wasteByReason) as Array<[string, Array<unknown>]>).map(
      ([label, rows]) => ({ label, value: rows.length }),
    ),
    locationPerformance: rankedLocations.map((row) => ({
      label: row.location.name,
      value: row.score,
    })),
    countryRevenueUSD: [
      { label: "Colombia", value: countryComparison.Colombia.totalRevenue.USD },
      { label: "USA", value: countryComparison.USA.totalRevenue.USD },
    ],
    revenueUsdAsCop: convertCurrency(calculateDailyRevenue(SAMPLE_SALES, reportDate, "USD"), "USD", "COP"),
    salesByLocationCount: filterSalesByLocation(SAMPLE_SALES, miamiLocationId).length,
    salesOnDateCount: filterSalesByDateRange(SAMPLE_SALES, dailyStart, dailyEnd).length,
    meatItemsCount: filterMenuItemsByCategory(SAMPLE_MENU_ITEMS, "Meat").length,
    activeLocationsCount: filterActiveLocations(SAMPLE_OPERATIONS_LOCATIONS).length,
    locationByIdFound: findLocationById(SAMPLE_OPERATIONS_LOCATIONS, miamiLocationId) !== null,
    menuItemByNameFound: findMenuItemByName(SAMPLE_MENU_ITEMS, "French Fries") !== null,
    capacityBinarySearchIndex: binarySearchLocationByCapacity(sortedLocationsByCapacity, capacityTarget),
    menuValidationPassed: validateMenuItem(SAMPLE_MENU_ITEMS[0]).valid,
    saleValidationPassed: validateSaleTransaction(SAMPLE_SALES[0]).valid,
    locationValidationPassed: validateLocation(SAMPLE_OPERATIONS_LOCATIONS[0]).valid,
  };
}

export const DATA_PROCESSING_COUNTRY_OPTIONS: Array<CountryFilter> = [
  ALL_COUNTRIES_FILTER,
  "Colombia",
  "United States",
];
