import {
  BrasaPointsRegistration,
  City,
  COUNTRY_TO_CITIES,
  Country,
  DietaryPreference,
  DiscoveryChannel,
  LOCATIONS_BY_COUNTRY_AND_CITY,
  RegistrationValidationErrors,
  RegistrationValidationResult,
} from "../types/models.js";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const ALLOWED_DIETARY_PREFERENCES: DietaryPreference[] = [
  "No restrictions",
  "Vegetarian",
  "Gluten-free",
  "Other",
];

const ALLOWED_DISCOVERY_CHANNELS: DiscoveryChannel[] = [
  "Social media",
  "Recommendation",
  "Walked by",
  "Internet search",
  "Other",
];

function hasAtLeastTwoWords(fullName: string): boolean {
  return fullName.trim().split(/\s+/).filter((part) => part.length > 0).length >= 2;
}

function isValidDate(dateOfBirth: string): boolean {
  return !Number.isNaN(new Date(dateOfBirth).getTime());
}

function isValidEmail(email: string): boolean {
  return EMAIL_REGEX.test(email.trim());
}

function isPhoneFormatValid(phone: string): boolean {
  return /^\+\d{1,3}[\s\d-]+$/.test(phone.trim());
}

export function calculateAge(dateOfBirth: string, referenceDate: Date = new Date()): number {
  const birthDate = new Date(dateOfBirth);

  if (Number.isNaN(birthDate.getTime())) {
    return -1;
  }

  let age = referenceDate.getUTCFullYear() - birthDate.getUTCFullYear();
  const monthDelta = referenceDate.getUTCMonth() - birthDate.getUTCMonth();
  const dayDelta = referenceDate.getUTCDate() - birthDate.getUTCDate();

  if (monthDelta < 0 || (monthDelta === 0 && dayDelta < 0)) {
    age -= 1;
  }

  return age;
}

export function getCitiesForCountry(country: Country): string[] {
  return [...COUNTRY_TO_CITIES[country]];
}

export function getFavoriteLocationsByCountryAndCity(
  country: Country,
  city: City,
): string[] {
  return [...LOCATIONS_BY_COUNTRY_AND_CITY[country][city]];
}

function hasCorrectCountryCode(phone: string, country: Country): boolean {
  const normalizedPhone = phone.trim();
  if (country === "Colombia") {
    return normalizedPhone.startsWith("+57");
  }

  return normalizedPhone.startsWith("+1");
}

export function validateBrasaPointsRegistration(
  registration: BrasaPointsRegistration,
  referenceDate: Date = new Date(),
): RegistrationValidationResult {
  const errors: RegistrationValidationErrors = {};

  if (!hasAtLeastTwoWords(registration.fullName)) {
    errors.fullName = "Enter your full name (first and last name)";
  }

  if (!isValidEmail(registration.email)) {
    errors.email = "Enter a valid email (example: <name@email.com>)";
  }

  if (!isPhoneFormatValid(registration.phone) || !hasCorrectCountryCode(registration.phone, registration.country)) {
    errors.phone = "Phone must include country code (example: +57 300 123 4567 or +1 305 123 4567)";
  }

  if (!registration.country) {
    errors.country = "Select your country";
  }

  const cityOptions = COUNTRY_TO_CITIES[registration.country];

  if (!registration.city || !cityOptions.includes(registration.city)) {
    errors.city = "Select your city";
  }

  if (!ALLOWED_DISCOVERY_CHANNELS.includes(registration.howDidYouFindUs)) {
    errors.howDidYouFindUs = "Tell us how you found Brasaland";
  }

  if (!isValidDate(registration.dateOfBirth) || calculateAge(registration.dateOfBirth, referenceDate) < 18) {
    errors.dateOfBirth = "You must be 18 or older to register for Brasa Points";
  }

  if (!registration.acceptsProgramTerms) {
    errors.acceptsProgramTerms = "You must accept the Brasa Points program terms to continue";
  }

  registration.dietaryPreferences.forEach((preference) => {
    if (!ALLOWED_DIETARY_PREFERENCES.includes(preference)) {
      errors.dietaryPreferences = "Select valid dietary preferences";
    }
  });

  if (registration.favoriteBrasalandLocation && !errors.city) {
    const validLocations = getFavoriteLocationsByCountryAndCity(registration.country, registration.city);

    if (!validLocations.includes(registration.favoriteBrasalandLocation)) {
      errors.favoriteBrasalandLocation = "Select a valid favorite location for your country and city";
    }
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors,
  };
}
