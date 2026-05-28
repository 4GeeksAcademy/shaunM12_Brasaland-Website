import {
  BrasaLocation,
  BrasaPointsRegistration,
  City,
  Country,
  DietaryPreference,
  DiscoveryChannel,
} from "../types/models.js";
import { calculateAge } from "./validations.js";

export interface NumericSummary {
  total: number;
  average: number;
  minimum: number;
  maximum: number;
}

export interface RegistrationReport {
  totalRegistrations: number;
  registrationsByCountry: Record<Country, number>;
  registrationsByCity: Record<City, number>;
  registrationsByDiscoveryChannel: Record<DiscoveryChannel, number>;
  dietaryPreferenceSelections: Record<DietaryPreference, number>;
  emailOptInCount: number;
  ageSummary: NumericSummary;
}

export interface LocationDistributionReport {
  totalLocations: number;
  locationsByCountry: Record<Country, number>;
  locationsByCity: Record<City, number>;
}

function roundToTwoDecimals(value: number): number {
  return Number(value.toFixed(2));
}

export function summarizeNumbers(values: number[]): NumericSummary {
  if (values.length === 0) {
    return {
      total: 0,
      average: 0,
      minimum: 0,
      maximum: 0,
    };
  }

  const total = values.reduce((accumulator, currentValue) => accumulator + currentValue, 0);

  return {
    total: roundToTwoDecimals(total),
    average: roundToTwoDecimals(total / values.length),
    minimum: Math.min(...values),
    maximum: Math.max(...values),
  };
}

export function buildRegistrationReport(
  registrations: BrasaPointsRegistration[],
  referenceDate: Date = new Date(),
): RegistrationReport {
  const registrationsByCountry: Record<Country, number> = {
    Colombia: 0,
    "United States": 0,
  };

  const registrationsByCity: Record<City, number> = {
    "Medellín": 0,
    "Bogotá": 0,
    Cali: 0,
    Miami: 0,
    Orlando: 0,
  };

  const registrationsByDiscoveryChannel: Record<DiscoveryChannel, number> = {
    "Social media": 0,
    Recommendation: 0,
    "Walked by": 0,
    "Internet search": 0,
    Other: 0,
  };

  const dietaryPreferenceSelections: Record<DietaryPreference, number> = {
    "No restrictions": 0,
    Vegetarian: 0,
    "Gluten-free": 0,
    Other: 0,
  };

  let emailOptInCount = 0;
  const ages: number[] = [];

  registrations.forEach((registration) => {
    registrationsByCountry[registration.country] += 1;
    registrationsByCity[registration.city] += 1;
    registrationsByDiscoveryChannel[registration.howDidYouFindUs] += 1;

    registration.dietaryPreferences.forEach((preference) => {
      dietaryPreferenceSelections[preference] += 1;
    });

    if (registration.wantsEmailOffers) {
      emailOptInCount += 1;
    }

    ages.push(calculateAge(registration.dateOfBirth, referenceDate));
  });

  return {
    totalRegistrations: registrations.length,
    registrationsByCountry,
    registrationsByCity,
    registrationsByDiscoveryChannel,
    dietaryPreferenceSelections,
    emailOptInCount,
    ageSummary: summarizeNumbers(ages),
  };
}

export function buildLocationDistributionReport(
  locations: BrasaLocation[],
): LocationDistributionReport {
  const locationsByCountry: Record<Country, number> = {
    Colombia: 0,
    "United States": 0,
  };

  const locationsByCity: Record<City, number> = {
    "Medellín": 0,
    "Bogotá": 0,
    Cali: 0,
    Miami: 0,
    Orlando: 0,
  };

  locations.forEach((location) => {
    locationsByCountry[location.country] += 1;
    locationsByCity[location.city] += 1;
  });

  return {
    totalLocations: locations.length,
    locationsByCountry,
    locationsByCity,
  };
}
