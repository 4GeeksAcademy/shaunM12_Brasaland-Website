import { describe, expect, test } from "vitest";
import {
  buildLocationDistributionReport,
  buildRegistrationReport,
  summarizeNumbers,
} from "../Brasaland webpage/src/utils/transformations.js";
import { BrasaLocation, BrasaPointsRegistration } from "../Brasaland webpage/src/types/models.js";

const registrations: BrasaPointsRegistration[] = [
  {
    fullName: "Ana Diaz",
    email: "ana@example.com",
    phone: "+57 300 123 4567",
    country: "Colombia",
    city: "Medellín",
    favoriteBrasalandLocation: "Brasaland El Poblado",
    dietaryPreferences: ["No restrictions"],
    howDidYouFindUs: "Social media",
    dateOfBirth: "1995-05-10",
    acceptsProgramTerms: true,
    wantsEmailOffers: true,
    createdAt: "2026-04-10T12:00:00.000Z",
  },
  {
    fullName: "Luis Moreno",
    email: "luis@example.com",
    phone: "+57 301 000 0000",
    country: "Colombia",
    city: "Bogotá",
    favoriteBrasalandLocation: "Brasaland Usaquén",
    dietaryPreferences: ["Vegetarian"],
    howDidYouFindUs: "Recommendation",
    dateOfBirth: "2005-02-20",
    acceptsProgramTerms: true,
    wantsEmailOffers: false,
    createdAt: "2026-04-11T12:00:00.000Z",
  },
  {
    fullName: "Beth Carter",
    email: "beth@example.com",
    phone: "+1 305 123 4567",
    country: "United States",
    city: "Miami",
    favoriteBrasalandLocation: "Brasaland Brickell",
    dietaryPreferences: ["Gluten-free", "Other"],
    howDidYouFindUs: "Internet search",
    dateOfBirth: "1990-08-03",
    acceptsProgramTerms: true,
    wantsEmailOffers: true,
    createdAt: "2026-04-09T12:00:00.000Z",
  },
];

const locations: BrasaLocation[] = [
  {
    id: "COL-POBLADO",
    name: "Brasaland El Poblado",
    country: "Colombia",
    city: "Medellín",
  },
  {
    id: "COL-USAQUEN",
    name: "Brasaland Usaquén",
    country: "Colombia",
    city: "Bogotá",
  },
  {
    id: "USA-BRICKELL",
    name: "Brasaland Brickell",
    country: "United States",
    city: "Miami",
  },
];

describe("transformations utilities", () => {
  test("summarizes totals, average, minimum and maximum", () => {
    expect(summarizeNumbers([10, 20, 30])).toEqual({
      total: 60,
      average: 20,
      minimum: 10,
      maximum: 30,
    });
  });

  test("builds registration report with category counts and age stats", () => {
    const report = buildRegistrationReport(registrations, new Date("2026-04-23T00:00:00.000Z"));

    expect(report.totalRegistrations).toBe(3);
    expect(report.registrationsByCountry).toEqual({ Colombia: 2, "United States": 1 });
    expect(report.registrationsByCity["Bogotá"]).toBe(1);
    expect(report.registrationsByDiscoveryChannel["Internet search"]).toBe(1);
    expect(report.dietaryPreferenceSelections["Gluten-free"]).toBe(1);
    expect(report.emailOptInCount).toBe(2);
    expect(report.ageSummary.total).toBe(95);
    expect(report.ageSummary.average).toBe(31.67);
    expect(report.ageSummary.minimum).toBe(21);
    expect(report.ageSummary.maximum).toBe(35);
  });

  test("builds location distribution report", () => {
    const locationReport = buildLocationDistributionReport(locations);

    expect(locationReport.totalLocations).toBe(3);
    expect(locationReport.locationsByCountry).toEqual({ Colombia: 2, "United States": 1 });
    expect(locationReport.locationsByCity).toEqual({
      "Medellín": 1,
      "Bogotá": 1,
      Cali: 0,
      Miami: 1,
      Orlando: 0,
    });
  });
});
