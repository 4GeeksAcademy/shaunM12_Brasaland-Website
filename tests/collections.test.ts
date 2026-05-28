import { describe, expect, test } from "vitest";
import {
  filterLocationsByCriteria,
  filterRegistrationsByCriteria,
  sortLocationsByFields,
  sortRegistrationsByField,
} from "../Brasaland webpage/src/utils/collections.js";
import { BrasaLocation, BrasaPointsRegistration } from "../Brasaland webpage/src/types/models.js";

const sampleLocations: BrasaLocation[] = [
  {
    id: "COL-MED-POBLADO",
    name: "Brasaland El Poblado",
    city: "Medellín",
    country: "Colombia",
  },
  {
    id: "USA-MIA-BRICKELL",
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

describe("collections utilities", () => {
  test("filters registrations by multiple criteria", () => {
    const filteredRegistrations = filterRegistrationsByCriteria(
      sampleRegistrations,
      {
        country: "Colombia",
        dietaryPreference: "Vegetarian",
        minAge: 18,
      },
      new Date("2026-04-23T00:00:00.000Z"),
    );

    expect(filteredRegistrations).toHaveLength(1);
    expect(filteredRegistrations[0].email).toBe("luis@example.com");
  });

  test("filters locations by country and city", () => {
    const filteredLocations = filterLocationsByCriteria(sampleLocations, {
      country: "United States",
      city: "Miami",
    });

    expect(filteredLocations).toHaveLength(1);
    expect(filteredLocations[0].name).toBe("Brasaland Brickell");
  });

  test("sorts registrations ascending and descending", () => {
    const ascending = sortRegistrationsByField(sampleRegistrations, "email", "asc");
    const descending = sortRegistrationsByField(sampleRegistrations, "email", "desc");

    expect(ascending[0].email).toBe("ana@example.com");
    expect(descending[0].email).toBe("luis@example.com");
  });

  test("sorts locations by multiple fields", () => {
    const locations: BrasaLocation[] = [
      { id: "B", name: "Brasaland Chapinero", country: "Colombia", city: "Bogotá" },
      { id: "A", name: "Brasaland Brickell", country: "United States", city: "Miami" },
      { id: "C", name: "Brasaland Usaquén", country: "Colombia", city: "Bogotá" },
    ];

    const sortedLocations = sortLocationsByFields(locations, [
      { field: "country", order: "asc" },
      { field: "city", order: "asc" },
      { field: "name", order: "asc" },
    ]);

    expect(sortedLocations.map((location) => location.id)).toEqual(["B", "C", "A"]);
  });
});
