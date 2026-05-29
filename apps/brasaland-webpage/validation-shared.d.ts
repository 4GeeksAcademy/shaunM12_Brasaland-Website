export const EMAIL_REGEX: RegExp;
export const PHONE_REGEX: RegExp;

export const ALLOWED_DIETARY_PREFERENCES_DATA: string[];
export const ALLOWED_DISCOVERY_CHANNELS_DATA: string[];

export const COUNTRY_TO_CITIES_DATA: Record<string, string[]>;
export const LOCATIONS_BY_COUNTRY_AND_CITY_DATA: Record<string, Record<string, string[]>>;

export const UI_COUNTRIES: { value: string; label: { en: string; es: string } }[];
export const UI_CITIES_BY_COUNTRY: Record<string, { value: string; label: { en: string; es: string } }[]>;
export const UI_LOCATIONS_BY_COUNTRY_CITY: Record<string, string[]>;

export function hasAtLeastTwoWords(fullName: string): boolean;
export function isValidEmail(email: string): boolean;
export function isPhoneFormatValid(phone: string): boolean;
export function calculateAge(dateOfBirth: string, referenceDate?: Date): number;