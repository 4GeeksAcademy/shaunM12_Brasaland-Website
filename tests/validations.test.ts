import { describe, expect, test } from "vitest";
import {
  getCitiesForCountry,
  getFavoriteLocationsByCountryAndCity,
  validateBrasaPointsRegistration,
} from "../Brasaland webpage/src/utils/validations.js";
import { BrasaPointsRegistration } from "../Brasaland webpage/src/types/models.js";

const validRegistration: BrasaPointsRegistration = {
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
  wantsEmailOffers: false,
  createdAt: "2026-04-10T12:00:00.000Z",
};

describe("validation utilities", () => {
  test("validates a correct Brasa Points registration", () => {
    const result = validateBrasaPointsRegistration(
      validRegistration,
      new Date("2026-04-23T00:00:00.000Z"),
    );

    expect(result).toEqual({ valid: true, errors: {} });
  });

  test("returns exact required messages for invalid required fields", () => {
    const invalidRegistration = {
      ...validRegistration,
      fullName: "Ana",
      email: "anaexample.com",
      phone: "3001234567",
      city: "Miami",
      howDidYouFindUs: "" as BrasaPointsRegistration["howDidYouFindUs"],
      dateOfBirth: "2010-01-01",
      acceptsProgramTerms: false,
    };

    const result = validateBrasaPointsRegistration(
      invalidRegistration,
      new Date("2026-04-23T00:00:00.000Z"),
    );

    expect(result.valid).toBe(false);
    expect(result.errors.fullName).toBe("Enter your full name (first and last name)");
    expect(result.errors.email).toBe("Enter a valid email (example: <name@email.com>)");
    expect(result.errors.phone).toBe("Phone must include country code (example: +57 300 123 4567 or +1 305 123 4567)");
    expect(result.errors.city).toBe("Select your city");
    expect(result.errors.howDidYouFindUs).toBe("Tell us how you found Brasaland");
    expect(result.errors.dateOfBirth).toBe("You must be 18 or older to register for Brasa Points");
    expect(result.errors.acceptsProgramTerms).toBe(
      "You must accept the Brasa Points program terms to continue",
    );
  });

  test("validates dependent country-city and country+city-location logic", () => {
    expect(getCitiesForCountry("Colombia")).toEqual(["Medellín", "Bogotá", "Cali"]);
    expect(getCitiesForCountry("United States")).toEqual(["Miami", "Orlando"]);

    expect(getFavoriteLocationsByCountryAndCity("Colombia", "Bogotá")).toEqual([
      "Brasaland Usaquén",
      "Brasaland Chapinero",
      "Brasaland Zona Rosa",
    ]);

    const invalidLocationRegistration: BrasaPointsRegistration = {
      ...validRegistration,
      city: "Bogotá",
      favoriteBrasalandLocation: "Brasaland Brickell",
    };

    const result = validateBrasaPointsRegistration(invalidLocationRegistration);
    expect(result.valid).toBe(false);
    expect(result.errors.favoriteBrasalandLocation).toBe(
      "Select a valid favorite location for your country and city",
    );
  });
});
