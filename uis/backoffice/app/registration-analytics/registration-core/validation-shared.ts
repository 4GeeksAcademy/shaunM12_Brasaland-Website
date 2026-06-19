import { DietaryPreference, DiscoveryChannel } from "./types";

export const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const PHONE_REGEX = /^\+\d{1,3}[\s\d-]+$/;

export const ALLOWED_DIETARY_PREFERENCES: DietaryPreference[] = [
  "No restrictions",
  "Vegetarian",
  "Gluten-free",
  "Other",
];

export const ALLOWED_DISCOVERY_CHANNELS: DiscoveryChannel[] = [
  "Social media",
  "Recommendation",
  "Walked by",
  "Internet search",
  "Other",
];
