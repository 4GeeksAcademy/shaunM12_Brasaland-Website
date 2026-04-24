import {
  BrasaLocation,
  BrasaPointsRegistration,
} from "./types/models.js";
import {
  buildLocationDistributionReport,
  buildRegistrationReport,
} from "./utils/transformations.js";
import {
  filterLocationsByCriteria,
  filterRegistrationsByCriteria,
  sortLocationsByFields,
} from "./utils/collections.js";
import {
  binarySearchLocationByName,
  binarySearchRegistrationByEmail,
  findLocationByName,
  findRegistrationByEmail,
} from "./utils/search.js";
import { validateBrasaPointsRegistration } from "./utils/validations.js";

const sampleLocations: BrasaLocation[] = [
  {
    id: "COL-MED-POBLADO",
    name: "Brasaland El Poblado",
    country: "Colombia",
    city: "Medellín",
  },
  {
    id: "COL-BOG-CHAPINERO",
    name: "Brasaland Chapinero",
    country: "Colombia",
    city: "Bogotá",
  },
  {
    id: "USA-MIA-BRICKELL",
    name: "Brasaland Brickell",
    country: "United States",
    city: "Miami",
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
    createdAt: "2026-04-11T12:00:00.000Z",
  },
];

function runDemo(): void {
  console.log("Validation:", validateBrasaPointsRegistration(sampleRegistrations[0]));

  console.log(
    "Filter registrations (Colombia + email opt-in):",
    filterRegistrationsByCriteria(sampleRegistrations, {
      country: "Colombia",
      wantsEmailOffers: true,
    }),
  );

  console.log(
    "Filter locations (US):",
    filterLocationsByCriteria(sampleLocations, { country: "United States" }),
  );

  console.log("Linear search by email:", findRegistrationByEmail(sampleRegistrations, "beth@example.com"));
  console.log("Linear search location:", findLocationByName(sampleLocations, "Brasaland Chapinero"));

  const sortedByEmail = [...sampleRegistrations].sort((first, second) =>
    first.email.localeCompare(second.email, "en", { sensitivity: "base" }),
  );
  const sortedByLocationName = sortLocationsByFields(sampleLocations, [
    { field: "name", order: "asc" },
  ]);

  console.log(
    "Binary search registration index:",
    binarySearchRegistrationByEmail(sortedByEmail, "beth@example.com"),
  );
  console.log(
    "Binary search location index:",
    binarySearchLocationByName(sortedByLocationName, "Brasaland El Poblado"),
  );

  console.log(
    "Registration report:",
    buildRegistrationReport(sampleRegistrations, new Date("2026-04-23T00:00:00.000Z")),
  );
  console.log("Location report:", buildLocationDistributionReport(sampleLocations));
}

runDemo();
