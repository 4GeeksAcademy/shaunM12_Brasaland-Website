import { describe, expect, it } from "vitest";
import {
  buildDataProcessingDashboard,
  DATA_PROCESSING_COUNTRY_OPTIONS,
} from "../lib/data-processing";
import {
  SAMPLE_MENU_ITEMS,
  SAMPLE_OPERATIONS_LOCATIONS,
  SAMPLE_SALES,
  SAMPLE_WASTE,
  scoreLocationPerformance,
} from "../app/data-processing/data-processing-core";

describe("data processing dashboard adapter", () => {
  it("builds deterministic location totals for all countries", () => {
    const report = buildDataProcessingDashboard({
      country: "",
      referenceDate: "2026-04-23",
    });

    expect(report.totalLocations).toBe(6);
    expect(report.locationsByCountry).toEqual([
      { label: "Colombia", value: 4 },
      { label: "United States", value: 2 },
    ]);
  });

  it("supports country filtering and keeps empty rows out of city charts", () => {
    const report = buildDataProcessingDashboard({
      country: "United States",
      referenceDate: "2026-04-23",
    });

    expect(report.countryFilter).toBe("United States");
    expect(report.totalLocations).toBe(2);
    expect(report.locationsByCity).toEqual([
      { label: "Miami", value: 1 },
      { label: "Orlando", value: 1 },
    ]);
  });

  it("falls back to defaults for unknown filters and invalid dates", () => {
    const report = buildDataProcessingDashboard({
      country: "Unknown",
      referenceDate: "invalid-date",
    });

    expect(report.countryFilter).toBe("All");
    expect(report.referenceDate).toBe("2026-04-23");
  });

  it("exports the expected country options", () => {
    expect(DATA_PROCESSING_COUNTRY_OPTIONS).toEqual(["All", "Colombia", "United States"]);
  });

  it("exposes context3 collection/search/validation outputs", () => {
    const report = buildDataProcessingDashboard({
      country: "",
      referenceDate: "2026-04-15",
    });

    expect(report.salesByLocationCount).toBeGreaterThan(0);
    expect(report.salesOnDateCount).toBeGreaterThan(0);
    expect(report.meatItemsCount).toBe(1);
    expect(report.activeLocationsCount).toBe(2);
    expect(report.locationByIdFound).toBe(true);
    expect(report.menuItemByNameFound).toBe(true);
    expect(report.capacityBinarySearchIndex).toBeGreaterThanOrEqual(0);
    expect(report.menuValidationPassed).toBe(true);
    expect(report.saleValidationPassed).toBe(true);
    expect(report.locationValidationPassed).toBe(true);
  });

  it("normalizes location scoring against peer locations", () => {
    const medellin = SAMPLE_OPERATIONS_LOCATIONS.find((location) => location.id === "LOC-MEDELLIN-01");
    const miami = SAMPLE_OPERATIONS_LOCATIONS.find((location) => location.id === "LOC-MIAMI-01");

    expect(medellin).toBeDefined();
    expect(miami).toBeDefined();

    const medellinScore = scoreLocationPerformance(
      medellin!,
      SAMPLE_SALES,
      SAMPLE_WASTE,
      SAMPLE_MENU_ITEMS,
    );
    const miamiScore = scoreLocationPerformance(
      miami!,
      SAMPLE_SALES,
      SAMPLE_WASTE,
      SAMPLE_MENU_ITEMS,
    );

    expect(medellinScore).toBeGreaterThanOrEqual(0);
    expect(miamiScore).toBeGreaterThanOrEqual(0);
    expect(medellinScore).toBeLessThanOrEqual(100);
    expect(miamiScore).toBeLessThanOrEqual(100);
    expect(medellinScore).not.toBe(miamiScore);
  });
});
