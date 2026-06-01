export const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const PHONE_REGEX = /^\+\d{1,3}[\s\d-]+$/;

export const ALLOWED_DIETARY_PREFERENCES_DATA = [
  "No restrictions",
  "Vegetarian",
  "Gluten-free",
  "Other",
];

export const ALLOWED_DISCOVERY_CHANNELS_DATA = [
  "Social media",
  "Recommendation",
  "Walked by",
  "Internet search",
  "Other",
];

export const COUNTRY_TO_CITIES_DATA = {
  Colombia: ["Medellín", "Bogotá", "Cali"],
  "United States": ["Miami", "Orlando"],
};

export const LOCATIONS_BY_COUNTRY_AND_CITY_DATA = {
  Colombia: {
    "Medellín": [
      "Brasaland El Poblado",
      "Brasaland Laureles",
      "Brasaland Envigado",
      "Brasaland Sabaneta",
    ],
    "Bogotá": [
      "Brasaland Usaquén",
      "Brasaland Chapinero",
      "Brasaland Zona Rosa",
    ],
    Cali: [
      "Brasaland Granada",
      "Brasaland Ciudad Jardín",
      "Brasaland Unicentro",
    ],
    Miami: [],
    Orlando: [],
  },
  "United States": {
    "Medellín": [],
    "Bogotá": [],
    Cali: [],
    Miami: ["Brasaland Brickell", "Brasaland Coral Gables"],
    Orlando: ["Brasaland Downtown", "Brasaland International Drive"],
  },
};

export const UI_COUNTRIES = [
  { value: "colombia", label: { en: "Colombia", es: "Colombia" } },
  { value: "united-states", label: { en: "United States", es: "Estados Unidos" } },
];

export const UI_CITIES_BY_COUNTRY = {
  colombia: [
    { value: "medellin", label: { en: "Medellin", es: "Medellín" } },
    { value: "bogota", label: { en: "Bogota", es: "Bogotá" } },
    { value: "cali", label: { en: "Cali", es: "Cali" } },
  ],
  "united-states": [
    { value: "miami", label: { en: "Miami", es: "Miami" } },
    { value: "orlando", label: { en: "Orlando", es: "Orlando" } },
  ],
};

export const UI_LOCATIONS_BY_COUNTRY_CITY = {
  "colombia|medellin": ["Brasaland El Poblado", "Brasaland Laureles", "Brasaland Envigado", "Brasaland Sabaneta"],
  "colombia|bogota": ["Brasaland Usaquén", "Brasaland Chapinero", "Brasaland Zona Rosa"],
  "colombia|cali": ["Brasaland Granada", "Brasaland Ciudad Jardín", "Brasaland Unicentro"],
  "united-states|miami": ["Brasaland Brickell", "Brasaland Coral Gables"],
  "united-states|orlando": ["Brasaland Downtown", "Brasaland International Drive"],
};

export function hasAtLeastTwoWords(fullName) {
  return fullName.trim().split(/\s+/).filter((part) => part.length > 0).length >= 2;
}

export function isValidEmail(email) {
  return EMAIL_REGEX.test(email.trim());
}

export function isPhoneFormatValid(phone) {
  return PHONE_REGEX.test(phone.trim());
}

export function calculateAge(dateOfBirth, referenceDate = new Date()) {
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
