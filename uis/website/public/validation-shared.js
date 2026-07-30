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
  Colombia: ["Barranquilla", "Bogotá", "Cali", "Envigado", "Medellín"],
  "United States": [
    "Fort Lauderdale",
    "Jacksonville",
    "Miami",
    "Miami Beach",
    "Orlando",
    "Tampa",
    "West Palm Beach",
  ],
};

export const LOCATIONS_BY_COUNTRY_AND_CITY_DATA = {
  Colombia: {
    Barranquilla: ["Brasaland Barranquilla Norte"],
    "Bogotá": ["Brasaland Bogotá Chapinero", "Brasaland Bogotá Usaquén"],
    Cali: ["Brasaland Cali Granada"],
    Envigado: ["Brasaland Medellín Envigado"],
    "Medellín": ["Brasaland Medellín Centro", "Brasaland Medellín Laureles"],
    "Fort Lauderdale": [],
    Jacksonville: [],
    Miami: [],
    "Miami Beach": [],
    Orlando: [],
    Tampa: [],
    "West Palm Beach": [],
  },
  "United States": {
    Barranquilla: [],
    "Bogotá": [],
    Cali: [],
    Envigado: [],
    "Medellín": [],
    "Fort Lauderdale": ["Brasaland Fort Lauderdale"],
    Jacksonville: ["Brasaland Jacksonville"],
    Miami: ["Brasaland Miami Brickell"],
    "Miami Beach": ["Brasaland Miami Beach"],
    Orlando: ["Brasaland Orlando I-Drive"],
    Tampa: ["Brasaland Tampa Bay"],
    "West Palm Beach": ["Brasaland West Palm Beach"],
  },
};

export const UI_COUNTRIES = [
  { value: "colombia", label: { en: "Colombia", es: "Colombia" } },
  { value: "united-states", label: { en: "United States", es: "Estados Unidos" } },
];

export const UI_CITIES_BY_COUNTRY = {
  colombia: [
    { value: "barranquilla", label: { en: "Barranquilla", es: "Barranquilla" } },
    { value: "bogota", label: { en: "Bogota", es: "Bogotá" } },
    { value: "cali", label: { en: "Cali", es: "Cali" } },
    { value: "envigado", label: { en: "Envigado", es: "Envigado" } },
    { value: "medellin", label: { en: "Medellin", es: "Medellín" } },
  ],
  "united-states": [
    { value: "fort-lauderdale", label: { en: "Fort Lauderdale", es: "Fort Lauderdale" } },
    { value: "jacksonville", label: { en: "Jacksonville", es: "Jacksonville" } },
    { value: "miami", label: { en: "Miami", es: "Miami" } },
    { value: "miami-beach", label: { en: "Miami Beach", es: "Miami Beach" } },
    { value: "orlando", label: { en: "Orlando", es: "Orlando" } },
    { value: "tampa", label: { en: "Tampa", es: "Tampa" } },
    { value: "west-palm-beach", label: { en: "West Palm Beach", es: "West Palm Beach" } },
  ],
};

export const UI_LOCATIONS_BY_COUNTRY_CITY = {
  "colombia|barranquilla": ["Brasaland Barranquilla Norte"],
  "colombia|bogota": ["Brasaland Bogotá Chapinero", "Brasaland Bogotá Usaquén"],
  "colombia|cali": ["Brasaland Cali Granada"],
  "colombia|envigado": ["Brasaland Medellín Envigado"],
  "colombia|medellin": ["Brasaland Medellín Centro", "Brasaland Medellín Laureles"],
  "united-states|fort-lauderdale": ["Brasaland Fort Lauderdale"],
  "united-states|jacksonville": ["Brasaland Jacksonville"],
  "united-states|miami": ["Brasaland Miami Brickell"],
  "united-states|miami-beach": ["Brasaland Miami Beach"],
  "united-states|orlando": ["Brasaland Orlando I-Drive"],
  "united-states|tampa": ["Brasaland Tampa Bay"],
  "united-states|west-palm-beach": ["Brasaland West Palm Beach"],
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
