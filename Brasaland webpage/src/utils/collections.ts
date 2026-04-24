import {
  BrasaLocation,
  BrasaPointsRegistration,
  City,
  Country,
  DietaryPreference,
  DiscoveryChannel,
} from "../types/models.js";
import { calculateAge } from "./validations.js";

export interface RegistrationFilterCriteria {
  country?: Country;
  city?: City;
  favoriteBrasalandLocation?: string;
  dietaryPreference?: DietaryPreference;
  howDidYouFindUs?: DiscoveryChannel;
  wantsEmailOffers?: boolean;
  minAge?: number;
  maxAge?: number;
}

export interface LocationFilterCriteria {
  country?: Country;
  city?: City;
}

export type RegistrationSortField =
  | "fullName"
  | "email"
  | "country"
  | "city"
  | "dateOfBirth"
  | "createdAt";

export type LocationSortField = "country" | "city" | "name";

export interface SortCriteria {
  field: LocationSortField;
  order: "asc" | "desc";
}

export function filterRegistrationsByCriteria(
  registrations: BrasaPointsRegistration[],
  criteria: RegistrationFilterCriteria,
  referenceDate: Date = new Date(),
): BrasaPointsRegistration[] {
  return registrations.filter((registration) => {
    const registrationAge = calculateAge(registration.dateOfBirth, referenceDate);

    if (criteria.country && registration.country !== criteria.country) {
      return false;
    }

    if (criteria.city && registration.city !== criteria.city) {
      return false;
    }

    if (
      criteria.favoriteBrasalandLocation &&
      registration.favoriteBrasalandLocation !== criteria.favoriteBrasalandLocation
    ) {
      return false;
    }

    if (
      criteria.dietaryPreference &&
      !registration.dietaryPreferences.includes(criteria.dietaryPreference)
    ) {
      return false;
    }

    if (criteria.howDidYouFindUs && registration.howDidYouFindUs !== criteria.howDidYouFindUs) {
      return false;
    }

    if (
      typeof criteria.wantsEmailOffers === "boolean" &&
      registration.wantsEmailOffers !== criteria.wantsEmailOffers
    ) {
      return false;
    }

    if (typeof criteria.minAge === "number" && registrationAge < criteria.minAge) {
      return false;
    }

    if (typeof criteria.maxAge === "number" && registrationAge > criteria.maxAge) {
      return false;
    }

    return true;
  });
}

export function filterLocationsByCriteria(
  locations: BrasaLocation[],
  criteria: LocationFilterCriteria,
): BrasaLocation[] {
  return locations.filter((location) => {
    if (criteria.country && location.country !== criteria.country) {
      return false;
    }

    if (criteria.city && location.city !== criteria.city) {
      return false;
    }

    return true;
  });
}

function compareText(
  firstValue: string,
  secondValue: string,
  order: "asc" | "desc",
): number {
  const comparison = firstValue.localeCompare(secondValue, "en", { sensitivity: "base" });
  return order === "asc" ? comparison : -comparison;
}

export function sortRegistrationsByField(
  registrations: BrasaPointsRegistration[],
  field: RegistrationSortField,
  order: "asc" | "desc",
): BrasaPointsRegistration[] {
  return [...registrations].sort((firstRegistration, secondRegistration) =>
    compareText(
      String(firstRegistration[field]).toLowerCase(),
      String(secondRegistration[field]).toLowerCase(),
      order,
    ),
  );
}

export function sortLocationsByFields(
  locations: BrasaLocation[],
  sortCriteria: SortCriteria[],
): BrasaLocation[] {
  const criteria: SortCriteria[] =
    sortCriteria.length === 0 ? [{ field: "name", order: "asc" }] : sortCriteria;

  return [...locations].sort((firstLocation, secondLocation) => {
    for (const criterion of criteria) {
      const firstValue = firstLocation[criterion.field];
      const secondValue = secondLocation[criterion.field];
      const comparison = compareText(firstValue, secondValue, criterion.order);

      if (comparison !== 0) {
        return comparison;
      }
    }

    return 0;
  });
}
