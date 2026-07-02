import { IncidentAnalysisResult } from "@/types/incidents";
import { authorizedFetch } from "@/lib/http";

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
    const errorText = await response.text();
    let message = errorText || response.statusText || "Request failed.";
    try {
      const parsed = JSON.parse(errorText || "{}") as { detail?: string };
      if (parsed.detail) {
        message = parsed.detail;
      }
    } catch {
      // keep raw text
    }
    throw new Error(toFriendlyIncidentMessage(message));
  }
  try {
    return (await response.json()) as IncidentAnalysisResult;
  } catch {
    throw new Error("The incident analyzer returned an unreadable response. Please try again.");
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
    const errorText = await response.text();
    let message = errorText || response.statusText || "Request failed.";
    try {
      const parsed = JSON.parse(errorText || "{}") as { detail?: string };
      if (parsed.detail) {
        message = parsed.detail;
      }
    } catch {
      // keep raw text
    }
    throw new Error(toFriendlyIncidentMessage(message));
  }

  return response.blob();
}
