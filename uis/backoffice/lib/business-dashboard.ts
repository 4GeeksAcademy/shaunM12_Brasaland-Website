import {
  calculateAge,
  buildLocationDistributionReport,
  buildRegistrationReport,
  filterLocationsByCriteria,
  filterRegistrationsByCriteria,
  findRegistrationByEmail,
  sortRegistrationsByField,
  sortLocationsByFields,
} from "../../../src/index";
import type { BrasaLocation, BrasaPointsRegistration } from "../../../src/types/models";
import type { Candidate, CandidateInput, CandidateStage, CandidateStatus } from "@/types/api";

export interface TrackerInsights {
  totalLocations: number;
  totalRegistrations: number;
  colombiaOptInCount: number;
  latestRegistration: BrasaPointsRegistration | null;
  locationReport: ReturnType<typeof buildLocationDistributionReport>;
  registrationReport: ReturnType<typeof buildRegistrationReport>;
  topLocationsAlphabetical: BrasaLocation[];
}

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
  {
    id: "USA-ORL-LAKE-EOLA",
    name: "Brasaland Lake Eola",
    country: "United States",
    city: "Orlando",
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
  {
    fullName: "Santiago Ruiz",
    email: "santiago@example.com",
    phone: "+57 315 987 1234",
    country: "Colombia",
    city: "Bogotá",
    favoriteBrasalandLocation: "Brasaland Chapinero",
    dietaryPreferences: ["Other"],
    howDidYouFindUs: "Recommendation",
    dateOfBirth: "1997-02-14",
    acceptsProgramTerms: true,
    wantsEmailOffers: true,
    createdAt: "2026-04-12T12:00:00.000Z",
  },
];

function normalizeId(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

function mapDiscoveryChannelToStage(channel: BrasaPointsRegistration["howDidYouFindUs"]): CandidateStage {
  if (channel === "Recommendation") {
    return "technical_interview";
  }

  if (channel === "Internet search") {
    return "personal_interview";
  }

  if (channel === "Social media") {
    return "review";
  }

  if (channel === "Other") {
    return "offer_presented";
  }

  return "pending";
}

function mapRegistrationToStatus(registration: BrasaPointsRegistration): CandidateStatus {
  if (registration.country === "United States") {
    return "selected";
  }

  if (registration.wantsEmailOffers) {
    return "in_progress";
  }

  return "received";
}

function toCandidate(registration: BrasaPointsRegistration): Candidate {
  const age = calculateAge(registration.dateOfBirth, new Date("2026-04-23T00:00:00.000Z"));
  const baseId = `${registration.fullName}-${registration.city}`;

  return {
    id: normalizeId(baseId),
    full_name: registration.fullName,
    email: registration.email,
    phone: registration.phone,
    position: "Executive Assistant",
    linkedin_url: `https://linkedin.com/in/${normalizeId(registration.fullName)}`,
    cv_url: `https://example.com/cv/${normalizeId(registration.fullName)}.pdf`,
    status: mapRegistrationToStatus(registration),
    stage: mapDiscoveryChannelToStage(registration.howDidYouFindUs),
    experience_years: Math.max(0, age - 18),
    notes_count: registration.dietaryPreferences.length,
    applied_at: registration.createdAt,
    updated_at: registration.createdAt,
  };
}

export function getInitialTrackerCandidates(): Candidate[] {
  const sorted = sortRegistrationsByField(sampleRegistrations, "fullName", "asc");
  return sorted.map(toCandidate);
}

export function createLocalCandidate(input: CandidateInput): Candidate {
  const normalizedName = input.full_name.trim();

  return {
    id: normalizeId(`${normalizedName}-${Date.now()}`),
    ...input,
    full_name: normalizedName,
    notes_count: 0,
    applied_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

export function getTrackerInsights(): TrackerInsights {
  const locationReport = buildLocationDistributionReport(sampleLocations);
  const registrationReport = buildRegistrationReport(
    sampleRegistrations,
    new Date("2026-04-23T00:00:00.000Z"),
  );

  const colombiaOptInCount = filterRegistrationsByCriteria(sampleRegistrations, {
    country: "Colombia",
    wantsEmailOffers: true,
  }).length;

  const topLocationsAlphabetical = sortLocationsByFields(
    filterLocationsByCriteria(sampleLocations, { country: "United States" }),
    [{ field: "name", order: "asc" }],
  );

  const latestRegistration = findRegistrationByEmail(sampleRegistrations, "beth@example.com");

  return {
    totalLocations: sampleLocations.length,
    totalRegistrations: sampleRegistrations.length,
    colombiaOptInCount,
    latestRegistration,
    locationReport,
    registrationReport,
    topLocationsAlphabetical,
  };
}
