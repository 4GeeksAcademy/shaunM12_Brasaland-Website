import { BrasaPointsRegistration } from "./types";
import { SAMPLE_REGISTRATIONS } from "./sample-data";

/**
 * Single source of truth for registration data.
 *
 * Today this returns in-memory sample data. The function is intentionally
 * `async` so a later refactor can swap the body for an API call
 * (e.g. `await authorizedFetch("/registrations")`) without touching the report
 * builder, the dashboard, or the page.
 */
export async function getRegistrations(): Promise<BrasaPointsRegistration[]> {
  return SAMPLE_REGISTRATIONS;
}
