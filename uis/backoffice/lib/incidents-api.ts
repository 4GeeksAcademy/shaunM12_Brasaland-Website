import { IncidentAnalysisResult } from "@/types/incidents";

function getBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_INCIDENTS_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  // Same-origin requests are proxied to the FastAPI service via next.config.mjs rewrites.
  return "";
}

export async function analyzeIncidentFile(file: File): Promise<IncidentAnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);

  let response: Response;
  try {
    response = await fetch(`${getBaseUrl()}/api/incidents/analyze`, {
      method: "POST",
      body: formData,
      cache: "no-store",
    });
  } catch {
    throw new Error(
      "Cannot reach the incident analyzer API. Start it with: npm run api:dev",
    );
  }

  if (!response.ok) {
    const errorText = await response.text();
    let message = errorText || response.statusText;
    try {
      const parsed = JSON.parse(errorText) as { detail?: string };
      if (parsed.detail) {
        message = parsed.detail;
      }
    } catch {
      // keep raw text
    }
    throw new Error(message);
  }

  return (await response.json()) as IncidentAnalysisResult;
}

export async function downloadIncidentResults(): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(`${getBaseUrl()}/api/incidents/results/export`, {
      cache: "no-store",
    });
  } catch {
    throw new Error(
      "Cannot reach the incident analyzer API. Start it with: npm run api:dev",
    );
  }

  if (!response.ok) {
    const errorText = await response.text();
    let message = errorText || response.statusText;
    try {
      const parsed = JSON.parse(errorText) as { detail?: string };
      if (parsed.detail) {
        message = parsed.detail;
      }
    } catch {
      // keep raw text
    }
    throw new Error(message);
  }

  return response.blob();
}
