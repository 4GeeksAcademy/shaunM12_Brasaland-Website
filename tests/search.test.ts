import { describe, expect, test } from "vitest";
import {
  binarySearchLocationByName,
  binarySearchRegistrationByEmail,
  findLocationByName,
  findRegistrationByEmail,
} from "../Brasaland webpage/src/utils/search.js";
import { BrasaLocation, BrasaPointsRegistration } from "../Brasaland webpage/src/types/models.js";

const sampleLocations: BrasaLocation[] = [
  {
    id: "COL-1",
    name: "Brasaland Chapinero",
    city: "Bogotá",
    country: "Colombia",
  },
  {
    id: "COL-2",
    name: "Brasaland El Poblado",
    city: "Medellín",
    country: "Colombia",
  },
  {
    id: "USA-1",
    name: "Brasaland Brickell",
    city: "Miami",
    country: "United States",
  },
];

const sampleRegistrations: BrasaPointsRegistration[] = [
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
    fullName: "Beth Carter",
    email: "beth@example.com",
    phone: "+1 305 123 4567",
    country: "United States",
    city: "Miami",
    favoriteBrasalandLocation: "Brasaland Brickell",
    dietaryPreferences: ["Gluten-free"],
    howDidYouFindUs: "Internet search",
    dateOfBirth: "1990-08-03",
    acceptsProgramTerms: true,
    wantsEmailOffers: false,
    createdAt: "2026-04-09T12:00:00.000Z",
  },
];

describe("search utilities", () => {
  test("performs linear search in unsorted arrays", () => {
    expect(findRegistrationByEmail(sampleRegistrations, "BETH@EXAMPLE.COM")?.city).toBe("Miami");
    expect(findRegistrationByEmail(sampleRegistrations, "missing@example.com")).toBeNull();

    expect(findLocationByName(sampleLocations, "brasaland el poblado")?.country).toBe("Colombia");
    expect(findLocationByName(sampleLocations, "does not exist")).toBeNull();
  });

  test("performs binary search in sorted arrays", () => {
    const registrationsSortedByEmail = [...sampleRegistrations].sort((a, b) =>
      a.email.localeCompare(b.email, "en", { sensitivity: "base" }),
    );
    const locationsSortedByName = [...sampleLocations].sort((a, b) =>
      a.name.localeCompare(b.name, "en", { sensitivity: "base" }),
    );

    expect(binarySearchRegistrationByEmail(registrationsSortedByEmail, "beth@example.com")).toBe(1);
    expect(binarySearchRegistrationByEmail(registrationsSortedByEmail, "none@example.com")).toBe(-1);

    expect(binarySearchLocationByName(locationsSortedByName, "Brasaland El Poblado")).toBe(1);
    expect(binarySearchLocationByName(locationsSortedByName, "Unknown")).toBe(-1);
  });
});
