import { authorizedFetch } from "@/lib/http";
import {
  IncidentManagerCreateInput,
  IncidentManagerRecord,
  IncidentManagerStatus,
  IncidentManagerSummary,
} from "@/types/incidents-manager";

interface ValidationDetail {
  field?: string;
  message?: string;
}

function getBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_INCIDENTS_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "";
}

/** Same-origin `/api/incidents/*` proxies to FastAPI `/incidents/*`. */
function incidentPath(suffix = ""): string {
  const prefix = getBaseUrl() ? "/incidents" : "/api/incidents";
  return `${prefix}${suffix}`;
}

function toErrorMessage(statusText: string, bodyText: string): string {
  if (!bodyText) {
    return statusText || "Request failed.";
  }

  try {
    const parsed = JSON.parse(bodyText) as {
      detail?: string | ValidationDetail;
      message?: string;
    };
    if (typeof parsed.detail === "string") {
      return parsed.detail;
    }
    if (parsed.detail && typeof parsed.detail === "object") {
      const field = parsed.detail.field ? `${parsed.detail.field}: ` : "";
      const message = parsed.detail.message ?? "Invalid request.";
      return `${field}${message}`;
    }
    if (parsed.message) {
      return parsed.message;
    }
  } catch {
    // Keep raw text if parsing fails.
  }

  return bodyText;
}

function toFriendlyManagerMessage(message: string): string {
  const normalized = message.toLowerCase();
  if (normalized.includes("unexpected end of json input")) {
    return "The incident manager returned an invalid response. Please try again.";
  }
  if (normalized.includes("failed to fetch")) {
    return "Cannot reach the incident manager API. Please verify the API is running.";
  }
  return message;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(toFriendlyManagerMessage(toErrorMessage(response.statusText, text)));
  }
  try {
    return (await response.json()) as T;
  } catch {
    throw new Error("The incident manager returned an unreadable response. Please try again.");
  }
}

export async function listManagerIncidents(params?: {
  status?: IncidentManagerStatus | "";
  origin?: string;
  branch?: string;
  category?: string;
}): Promise<IncidentManagerRecord[]> {
  const query = new URLSearchParams();
  if (params?.status) {
    query.set("status", params.status);
  }
  if (params?.origin) {
    query.set("origin", params.origin);
  }
  if (params?.branch) {
    query.set("branch", params.branch);
  }
  if (params?.category) {
    query.set("category", params.category);
  }

  const suffix = query.toString() ? `?${query.toString()}` : "";
  const response = await authorizedFetch(
    `${getBaseUrl()}${incidentPath(suffix)}`,
  );
  return parseResponse<IncidentManagerRecord[]>(response);
}

export async function createManagerIncident(
  payload: IncidentManagerCreateInput,
): Promise<IncidentManagerRecord> {
  const response = await authorizedFetch(`${getBaseUrl()}${incidentPath()}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse<IncidentManagerRecord>(response);
}

export async function updateManagerIncidentStatus(
  incidentId: number,
  status: IncidentManagerStatus,
): Promise<IncidentManagerRecord> {
  const response = await authorizedFetch(
    `${getBaseUrl()}${incidentPath(`/${incidentId}/status`)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    },
  );
  return parseResponse<IncidentManagerRecord>(response);
}

export async function getManagerIncidentSummary(): Promise<IncidentManagerSummary> {
  const response = await authorizedFetch(
    `${getBaseUrl()}${incidentPath("/summary")}`,
  );
  return parseResponse<IncidentManagerSummary>(response);
}

export async function getManagerIncidentById(incidentId: number): Promise<IncidentManagerRecord> {
  const response = await authorizedFetch(
    `${getBaseUrl()}${incidentPath(`/${incidentId}`)}`,
  );
  return parseResponse<IncidentManagerRecord>(response);
}
