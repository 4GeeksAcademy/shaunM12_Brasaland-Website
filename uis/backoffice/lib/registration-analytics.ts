import {
  buildRegistrationReport,
  Country,
  getRegistrations,
  summarizeNumbers,
} from "../app/registration-analytics/registration-core";

const ALL_COUNTRIES_FILTER = "All" as const;

type CountryFilter = Country | typeof ALL_COUNTRIES_FILTER;

export interface ChartDatum {
  label: string;
  value: number;
}

export interface RegistrationDashboard {
  countryFilter: CountryFilter;
  referenceDate: string;
  totalRegistrations: number;
  emailOptInCount: number;
  emailOptInRate: number;
  ageAverage: number;
  ageMinimum: number;
  ageMaximum: number;
  registrationsByCountry: ChartDatum[];
  registrationsByCity: ChartDatum[];
  registrationsByDiscoveryChannel: ChartDatum[];
  dietaryPreferenceSelections: ChartDatum[];
  cityRegistrationSummary: ChartDatum[];
}

function toChartData<T extends string>(
  source: Record<T, number>,
  includeZeroValues = false,
): ChartDatum[] {
  return (Object.entries(source) as Array<[T, number]>)
    .filter(([, value]) => includeZeroValues || value > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([label, value]) => ({ label, value }));
}

function normalizeCountryFilter(value?: string): CountryFilter {
  if (value === "Colombia" || value === "United States") {
    return value;
  }

  return ALL_COUNTRIES_FILTER;
}

function normalizeReferenceDate(value?: string): Date {
  if (!value) {
    return new Date("2026-04-23T00:00:00.000Z");
  }

  const parsed = new Date(`${value}T00:00:00.000Z`);
  if (Number.isNaN(parsed.getTime())) {
    return new Date("2026-04-23T00:00:00.000Z");
  }

  return parsed;
}

function filterByCountry<T extends { country: Country }>(
  rows: T[],
  countryFilter: CountryFilter,
): T[] {
  if (countryFilter === ALL_COUNTRIES_FILTER) {
    return rows;
  }

  return rows.filter((row) => row.country === countryFilter);
}

export async function buildRegistrationDashboard(options?: {
  country?: string;
  referenceDate?: string;
}): Promise<RegistrationDashboard> {
  const countryFilter = normalizeCountryFilter(options?.country);
  const referenceDate = normalizeReferenceDate(options?.referenceDate);

  const allRegistrations = await getRegistrations();
  const registrations = filterByCountry(allRegistrations, countryFilter);

  const registrationReport = buildRegistrationReport(registrations, referenceDate);

  const cityCounts = Object.values(registrationReport.registrationsByCity);
  const citySummary = summarizeNumbers(cityCounts);

  return {
    countryFilter,
    referenceDate: referenceDate.toISOString().slice(0, 10),
    totalRegistrations: registrationReport.totalRegistrations,
    emailOptInCount: registrationReport.emailOptInCount,
    emailOptInRate:
      registrationReport.totalRegistrations === 0
        ? 0
        : Number(
            ((registrationReport.emailOptInCount / registrationReport.totalRegistrations) * 100).toFixed(
              2,
            ),
          ),
    ageAverage: registrationReport.ageSummary.average,
    ageMinimum: registrationReport.ageSummary.minimum,
    ageMaximum: registrationReport.ageSummary.maximum,
    registrationsByCountry: toChartData(registrationReport.registrationsByCountry, true),
    registrationsByCity: toChartData(registrationReport.registrationsByCity),
    registrationsByDiscoveryChannel: toChartData(registrationReport.registrationsByDiscoveryChannel),
    dietaryPreferenceSelections: toChartData(registrationReport.dietaryPreferenceSelections),
    cityRegistrationSummary: [
      { label: "City registrations total", value: citySummary.total },
      { label: "City registrations average", value: citySummary.average },
      { label: "City registrations min", value: citySummary.minimum },
      { label: "City registrations max", value: citySummary.maximum },
    ],
  };
}

export const REGISTRATION_COUNTRY_OPTIONS: Array<CountryFilter> = [
  ALL_COUNTRIES_FILTER,
  "Colombia",
  "United States",
];
