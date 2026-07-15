import { formatApiError } from "@/lib/api-error";
import { authorizedFetch } from "@/lib/http";
import {
  IncidentAnalysisResult,
  IncidentManagerSummary,
  ManagedIncident,
  ManagedIncidentCreate,
  ManagedIncidentStatus,
} from "@/types/incidents";

function getBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_INCIDENTS_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  // Same-origin requests are proxied to the FastAPI service via next.config.mjs rewrites.
  return "";
}

function toFriendlyIncidentMessage(message: string): string {
  const normalized = message.toLowerCase();
  if (normalized.includes("unexpected end of json input")) {
    return "The incident service returned an invalid response. Please try again.";
  }
  if (normalized.includes("failed to fetch")) {
    return "Cannot reach the incident analyzer API. Please verify the API is running.";
  }
  return message;
}

async function readError(response: Response): Promise<string> {
  const errorText = await response.text();
  return toFriendlyIncidentMessage(formatApiError(response.status, errorText));
}

export async function analyzeIncidentFile(file: File): Promise<IncidentAnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);

  let response: Response;
  try {
    response = await authorizedFetch(`${getBaseUrl()}/api/incidents/analyze`, {
      method: "POST",
      body: formData,
    });
  } catch (caught) {
    if (caught instanceof Error && caught.message.toLowerCase().includes("session")) {
      throw caught;
    }
    throw new Error(
      "Cannot reach the incident analyzer API. Start it with: npm run api:dev",
    );
  }

  if (!response.ok) {
    throw new Error(await readError(response));
  }
  try {
    return (await response.json()) as IncidentAnalysisResult;
  } catch {
    throw new Error(
      "The incident analyzer returned an unreadable response. Please try again.",
    );
  }
}

export async function downloadIncidentResults(): Promise<Blob> {
  let response: Response;
  try {
    response = await authorizedFetch(`${getBaseUrl()}/api/incidents/results/export`);
  } catch (caught) {
    if (caught instanceof Error && caught.message.toLowerCase().includes("session")) {
      throw caught;
    }
    throw new Error(
      "Cannot reach the incident analyzer API. Start it with: npm run api:dev",
    );
  }

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  return response.blob();
}

export async function listManagedIncidents(): Promise<ManagedIncident[]> {
  const response = await authorizedFetch(`${getBaseUrl()}/api/incidents`);
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as ManagedIncident[];
}

export async function createManagedIncident(
  payload: ManagedIncidentCreate,
): Promise<ManagedIncident> {
  const response = await authorizedFetch(`${getBaseUrl()}/api/incidents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as ManagedIncident;
}

export async function updateManagedIncidentStatus(
  id: number,
  status: ManagedIncidentStatus,
): Promise<ManagedIncident> {
  const response = await authorizedFetch(
    `${getBaseUrl()}/api/incidents/${id}/status`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    },
  );
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as ManagedIncident;
}

export async function fetchIncidentManagerSummary(): Promise<IncidentManagerSummary> {
  const response = await authorizedFetch(`${getBaseUrl()}/api/incidents/summary`);
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as IncidentManagerSummary;
}
