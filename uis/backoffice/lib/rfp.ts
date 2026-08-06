/** RFP intake API client (context-27 Part 1 — Phase 4). */

import { formatApiError } from "@/lib/api-error";
import { authorizedFetch } from "@/lib/http";

export const RFP_STATUS_ANALYZING = "analyzing";
export const RFP_STATUS_INTAKE_COMPLETE = "intake_complete";
export const RFP_STATUS_DISCARDED = "discarded";
export const RFP_STATUS_FAILED = "failed";

export const RFP_P1_TERMINAL_STATUSES = new Set<string>([
  RFP_STATUS_INTAKE_COMPLETE,
  RFP_STATUS_DISCARDED,
  RFP_STATUS_FAILED,
]);

export const RFP_MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

export interface RfpSection {
  department_id: string;
  department_label: string;
  department_owner: string;
  key_aspects: string[];
  draft_content?: string | null;
  evaluation_results?: Record<string, unknown> | null;
  approval_status?: string | null;
}

export interface RfpTicketSummary {
  ticket_id: string;
  status: string;
  status_label: string;
  metadata: Record<string, unknown>;
  departments_needed: string[];
  requires_ceo_approval: boolean;
  created_at: string;
  updated_at: string;
}

export interface RfpTicketDetail extends RfpTicketSummary {
  unmapped_topics: string[];
  conflicts: Array<Record<string, unknown>>;
  intake_summary?: string | null;
  discard_reason?: string | null;
  error_message?: string | null;
  error_code?: string | null;
  markdown_length: number;
  has_markdown: boolean;
  sections: RfpSection[];
}

export interface RfpTicketCreateResponse {
  ticket_id: string;
  status: string;
  created_at: string;
}

function getBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_RFP_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "";
}

/** Same-origin `/api/rfp/*` proxies to FastAPI `/rfp/*`. */
export function rfpPath(suffix: string): string {
  const prefix = getBaseUrl() ? "/rfp" : "/api/rfp";
  return `${prefix}${suffix}`;
}

export function resolveRfpTicketsPath(): string {
  return rfpPath("/tickets");
}

export function isRfpTerminalStatus(status: string): boolean {
  return RFP_P1_TERMINAL_STATUSES.has(status);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await authorizedFetch(`${getBaseUrl()}${path}`, init);
  } catch (caught) {
    if (caught instanceof Error && caught.message.toLowerCase().includes("session")) {
      throw caught;
    }
    throw new Error(
      "Cannot reach the RFP API. Start it with: npm run api:dev",
    );
  }

  const body = await response.text();
  if (!response.ok) {
    throw new Error(formatApiError(response.status, body));
  }
  if (!body) {
    return undefined as T;
  }
  return JSON.parse(body) as T;
}

export async function uploadRfpTicket(file: File): Promise<RfpTicketCreateResponse> {
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    throw new Error("Upload must be a PDF file.");
  }
  if (file.size > RFP_MAX_UPLOAD_BYTES) {
    throw new Error("PDF exceeds the 10 MB upload limit.");
  }

  const formData = new FormData();
  formData.append("file", file);

  return request<RfpTicketCreateResponse>(rfpPath("/tickets"), {
    method: "POST",
    body: formData,
  });
}

export async function listRfpTickets(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<RfpTicketSummary[]> {
  const query = new URLSearchParams();
  if (params?.status) {
    query.set("status", params.status);
  }
  if (params?.limit !== undefined) {
    query.set("limit", String(params.limit));
  }
  if (params?.offset !== undefined) {
    query.set("offset", String(params.offset));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<RfpTicketSummary[]>(rfpPath(`/tickets${suffix}`));
}

export async function getRfpTicket(ticketId: string): Promise<RfpTicketDetail> {
  return request<RfpTicketDetail>(
    rfpPath(`/tickets/${encodeURIComponent(ticketId)}`),
  );
}
