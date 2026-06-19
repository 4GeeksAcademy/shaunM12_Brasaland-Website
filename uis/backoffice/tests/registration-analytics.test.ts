import { describe, expect, it } from "vitest";
import {
  buildRegistrationDashboard,
  REGISTRATION_COUNTRY_OPTIONS,
} from "../lib/registration-analytics";

describe("registration analytics dashboard", () => {
  it("builds deterministic registration totals for all countries", async () => {
    const report = await buildRegistrationDashboard({
      country: "",
      referenceDate: "2026-04-23",
    });

    expect(report.totalRegistrations).toBe(6);
    expect(report.emailOptInCount).toBe(4);
    expect(report.emailOptInRate).toBe(66.67);
    expect(report.registrationsByCountry).toEqual([
      { label: "Colombia", value: 4 },
      { label: "United States", value: 2 },
    ]);
  });

  it("supports country filtering and keeps empty rows out of city charts", async () => {
    const report = await buildRegistrationDashboard({
      country: "United States",
      referenceDate: "2026-04-23",
    });

    expect(report.countryFilter).toBe("United States");
    expect(report.totalRegistrations).toBe(2);
    expect(report.registrationsByCity).toEqual([
      { label: "Miami", value: 1 },
      { label: "Orlando", value: 1 },
    ]);
  });

  it("summarizes ages and city registration counts", async () => {
    const report = await buildRegistrationDashboard({
      country: "",
      referenceDate: "2026-04-23",
    });

    expect(report.ageAverage).toBeGreaterThan(0);
    expect(report.ageMinimum).toBeLessThanOrEqual(report.ageMaximum);
    expect(report.cityRegistrationSummary).toHaveLength(4);
  });

  it("falls back to defaults for unknown filters and invalid dates", async () => {
    const report = await buildRegistrationDashboard({
      country: "Unknown",
      referenceDate: "invalid-date",
    });

    expect(report.countryFilter).toBe("All");
    expect(report.referenceDate).toBe("2026-04-23");
  });

  it("exports the expected country options", () => {
    expect(REGISTRATION_COUNTRY_OPTIONS).toEqual(["All", "Colombia", "United States"]);
  });
});
