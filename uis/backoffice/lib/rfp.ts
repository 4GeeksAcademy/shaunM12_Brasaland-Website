/** RFP intake API client (context-27 Part 1 — Phase 4). */

import { formatApiError } from "@/lib/api-error";
import { authorizedFetch } from "@/lib/http";

export const RFP_STATUS_ANALYZING = "analyzing";
export const RFP_STATUS_INTAKE_COMPLETE = "intake_complete";
export const RFP_STATUS_DISCARDED = "discarded";
export const RFP_STATUS_FAILED = "failed";
export const RFP_STATUS_DRAFTING = "drafting";
export const RFP_STATUS_UNDER_EVALUATION = "under_evaluation";
export const RFP_STATUS_WAITING_FOR_APPROVAL = "waiting_for_approval";
export const RFP_STATUS_AWAITING_DEPARTMENT_APPROVAL = "awaiting_department_approval";
export const RFP_STATUS_ARBITRATING = "arbitrating";
export const RFP_STATUS_AWAITING_CEO_APPROVAL = "awaiting_ceo_approval";
export const RFP_STATUS_COMPLETED = "completed";

export const RFP_P1_TERMINAL_STATUSES = new Set<string>([
  RFP_STATUS_INTAKE_COMPLETE,
  RFP_STATUS_DISCARDED,
  RFP_STATUS_FAILED,
]);

/** Ticket statuses that should trigger detail-page polling (P1 intake + P2 generation + P3 approval). */
export const RFP_POLLING_STATUSES = new Set<string>([
  RFP_STATUS_ANALYZING,
  RFP_STATUS_DRAFTING,
  RFP_STATUS_UNDER_EVALUATION,
  RFP_STATUS_WAITING_FOR_APPROVAL,
  RFP_STATUS_AWAITING_DEPARTMENT_APPROVAL,
  RFP_STATUS_ARBITRATING,
  RFP_STATUS_AWAITING_CEO_APPROVAL,
]);

export const RFP_DRAFT_STATUS_NEEDS_HUMAN_REVIEW = "needs_human_review";
export const RFP_DRAFT_STATUS_PASSED = "passed";
export const RFP_DRAFT_STATUS_PENDING = "pending";

/** Section draft_status values that mean generation finished for that department. */
export const RFP_TERMINAL_DRAFT_STATUSES = new Set<string>([
  RFP_DRAFT_STATUS_PASSED,
  RFP_DRAFT_STATUS_NEEDS_HUMAN_REVIEW,
]);

export const RFP_APPROVAL_STATUS_AWAITING_HUMAN = "awaiting_human";
export const RFP_APPROVAL_STATUS_APPROVED = "approved";
export const RFP_APPROVAL_STATUS_REJECTED = "rejected";
export const RFP_APPROVAL_STATUS_CHANGES_REQUESTED = "changes_requested";

export const RFP_APPROVAL_DECISION_APPROVE = "approve";
export const RFP_APPROVAL_DECISION_REJECT = "reject";
export const RFP_APPROVAL_DECISION_REQUEST_CHANGES = "request_changes";

export const RFP_CEO_DECISION_APPROVE = "approve";
export const RFP_CEO_DECISION_REJECT = "reject";

export const RFP_MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

export interface RfpSection {
  department_id: string;
  department_label: string;
  department_owner: string;
  key_aspects: string[];
  draft_status: string;
  draft_status_label: string;
  draft_content?: string | null;
  evaluation_results?: Record<string, unknown> | null;
  approval_status?: string | null;
  approval_status_label?: string | null;
  approver?: string | null;
  approved_at?: string | null;
  approval_comment?: string | null;
}

export interface RfpCeoApprovalPacket {
  client_name?: string | null;
  estimated_contract_value_usd?: number | null;
  threshold_reason?: string | null;
  requires_ceo_approval: boolean;
  approved_excerpts: Record<string, string>;
  arbitration_resolutions: Array<Record<string, unknown>>;
  conflicts: Array<Record<string, unknown>>;
}

export interface RfpTraceEvent {
  id: number;
  node: string;
  payload: Record<string, unknown>;
  created_at: string;
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
  has_final_document: boolean;
  final_document_length: number;
  arbitration_exhausted: boolean;
  arbitration_resolutions: Array<Record<string, unknown>>;
  ceo_approval_comment?: string | null;
  ceo_approval_packet?: RfpCeoApprovalPacket | null;
  sections: RfpSection[];
}

/** Status filter options for the ticket list (matches API ``STATUS_VALUES``). */
export const RFP_STATUS_FILTER_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "", label: "All statuses" },
  { value: RFP_STATUS_ANALYZING, label: "Analyzing" },
  { value: RFP_STATUS_INTAKE_COMPLETE, label: "Intake complete" },
  { value: RFP_STATUS_DISCARDED, label: "Discarded" },
  { value: RFP_STATUS_FAILED, label: "Failed" },
  { value: RFP_STATUS_DRAFTING, label: "Drafting" },
  { value: RFP_STATUS_UNDER_EVALUATION, label: "Under evaluation" },
  { value: RFP_STATUS_WAITING_FOR_APPROVAL, label: "Waiting for approval" },
  { value: RFP_STATUS_AWAITING_DEPARTMENT_APPROVAL, label: "Awaiting department approval" },
  { value: RFP_STATUS_ARBITRATING, label: "Arbitrating" },
  { value: RFP_STATUS_AWAITING_CEO_APPROVAL, label: "Awaiting CEO approval" },
  { value: RFP_STATUS_COMPLETED, label: "Done" },
];

export interface RfpTicketCreateResponse {
  ticket_id: string;
  status: string;
  created_at: string;
}

export interface RfpDraftStartResponse {
  ticket_id: string;
  status: string;
  status_label: string;
}

export interface RfpDepartmentDecisionRequest {
  decision: string;
  comment?: string | null;
}

export interface RfpDepartmentDecisionResponse {
  ticket_id: string;
  department_id: string;
  decision: string;
  status: string;
  status_label: string;
  approval_status?: string | null;
  approval_status_label?: string | null;
}

export interface RfpRegenerateResponse {
  ticket_id: string;
  department_id: string;
  status: string;
  status_label: string;
  draft_status: string;
  draft_status_label: string;
  approval_status?: string | null;
  approval_status_label?: string | null;
}

export interface RfpCeoDecisionRequest {
  decision: string;
  comment?: string | null;
}

export interface RfpCeoDecisionResponse {
  ticket_id: string;
  decision: string;
  status: string;
  status_label: string;
}

export interface RfpApprovalStartResponse {
  ticket_id: string;
  status: string;
  status_label: string;
}

export interface RfpFinalDocumentResponse {
  ticket_id: string;
  final_document_markdown: string;
  generated_at: string;
}

export interface EvaluationSummaryView {
  iteration?: number;
  overall_passed?: boolean;
  needs_human_review?: boolean;
  readability_passed?: boolean;
  relevance_passed?: boolean;
  compliance_passed?: boolean;
  missing_topics: string[];
  compliance_failures: Array<{ rule_id?: string; message?: string }>;
}

export async function startRfpDraft(ticketId: string): Promise<RfpDraftStartResponse> {
  return request<RfpDraftStartResponse>(
    rfpPath(`/tickets/${encodeURIComponent(ticketId)}/draft`),
    { method: "POST" },
  );
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

export function shouldPollRfpTicket(status: string): boolean {
  return RFP_POLLING_STATUSES.has(status);
}

export function isSectionDraftTerminal(draftStatus: string): boolean {
  return RFP_TERMINAL_DRAFT_STATUSES.has(draftStatus);
}

export function countTerminalDraftSections(
  sections: RfpSection[],
): { completed: number; total: number } {
  const total = sections.length;
  const completed = sections.filter((section) =>
    isSectionDraftTerminal(section.draft_status),
  ).length;
  return { completed, total };
}

/** True when ticket status says done but section rows are still in-flight. */
export function hasSectionDraftMismatch(ticket: RfpTicketDetail): boolean {
  if (ticket.status !== RFP_STATUS_WAITING_FOR_APPROVAL) {
    return false;
  }
  if (!ticket.sections.length) {
    return false;
  }
  return !ticket.sections.every((section) =>
    isSectionDraftTerminal(section.draft_status),
  );
}

/** Poll intake, active drafting, or until every section reaches a terminal draft_status. */
export function shouldPollRfpTicketDetail(ticket: RfpTicketDetail): boolean {
  if (shouldPollRfpTicket(ticket.status)) {
    return true;
  }
  if (ticket.status === RFP_STATUS_DRAFTING) {
    const { completed, total } = countTerminalDraftSections(ticket.sections);
    return total === 0 || completed < total;
  }
  if (hasSectionDraftMismatch(ticket)) {
    return true;
  }
  return false;
}

export function isGenerationInProgress(ticket: RfpTicketDetail): boolean {
  return (
    ticket.status === RFP_STATUS_DRAFTING || hasSectionDraftMismatch(ticket)
  );
}

export function isApprovalPhase(status: string): boolean {
  return (
    status === RFP_STATUS_WAITING_FOR_APPROVAL ||
    status === RFP_STATUS_AWAITING_DEPARTMENT_APPROVAL ||
    status === RFP_STATUS_ARBITRATING ||
    status === RFP_STATUS_AWAITING_CEO_APPROVAL
  );
}

export function isSectionAwaitingApproval(section: RfpSection): boolean {
  return section.approval_status === RFP_APPROVAL_STATUS_AWAITING_HUMAN;
}

export function isSectionRejected(section: RfpSection): boolean {
  return section.approval_status === RFP_APPROVAL_STATUS_REJECTED;
}

export function sectionNeedsHumanReviewBanner(section: RfpSection): boolean {
  if (section.draft_status === RFP_DRAFT_STATUS_NEEDS_HUMAN_REVIEW) {
    return true;
  }
  const latest = section.evaluation_results?.latest;
  if (latest && typeof latest === "object" && !Array.isArray(latest)) {
    return Boolean((latest as Record<string, unknown>).needs_human_review);
  }
  return false;
}

export function buildEvaluationSummaryView(
  evaluationResults: Record<string, unknown> | null | undefined,
): EvaluationSummaryView | null {
  if (!evaluationResults || typeof evaluationResults !== "object") {
    return null;
  }
  const latest = evaluationResults.latest;
  if (!latest || typeof latest !== "object" || Array.isArray(latest)) {
    return null;
  }
  const run = latest as Record<string, unknown>;
  const readability = run.readability as Record<string, unknown> | undefined;
  const relevance = run.relevance as Record<string, unknown> | undefined;
  const compliance = run.compliance as Record<string, unknown> | undefined;
  return {
    iteration: typeof run.iteration === "number" ? run.iteration : undefined,
    overall_passed:
      typeof run.overall_passed === "boolean" ? run.overall_passed : undefined,
    needs_human_review:
      typeof run.needs_human_review === "boolean" ? run.needs_human_review : undefined,
    readability_passed:
      typeof readability?.passed === "boolean" ? readability.passed : undefined,
    relevance_passed:
      typeof relevance?.passed === "boolean" ? relevance.passed : undefined,
    compliance_passed:
      typeof compliance?.passed === "boolean" ? compliance.passed : undefined,
    missing_topics: Array.isArray(relevance?.missing_topics)
      ? (relevance.missing_topics as string[])
      : [],
    compliance_failures: Array.isArray(compliance?.failures)
      ? (compliance.failures as Array<{ rule_id?: string; message?: string }>)
      : [],
  };
}

export async function submitDepartmentDecision(
  ticketId: string,
  departmentId: string,
  body: RfpDepartmentDecisionRequest,
): Promise<RfpDepartmentDecisionResponse> {
  return request<RfpDepartmentDecisionResponse>(
    rfpPath(
      `/tickets/${encodeURIComponent(ticketId)}/sections/${encodeURIComponent(departmentId)}/decision`,
    ),
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
}

export async function regenerateDepartmentSection(
  ticketId: string,
  departmentId: string,
): Promise<RfpRegenerateResponse> {
  return request<RfpRegenerateResponse>(
    rfpPath(
      `/tickets/${encodeURIComponent(ticketId)}/sections/${encodeURIComponent(departmentId)}/regenerate`,
    ),
    { method: "POST" },
  );
}

export async function submitCeoDecision(
  ticketId: string,
  body: RfpCeoDecisionRequest,
): Promise<RfpCeoDecisionResponse> {
  return request<RfpCeoDecisionResponse>(
    rfpPath(`/tickets/${encodeURIComponent(ticketId)}/ceo/decision`),
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
}

export async function startApprovalRecovery(
  ticketId: string,
): Promise<RfpApprovalStartResponse> {
  return request<RfpApprovalStartResponse>(
    rfpPath(`/tickets/${encodeURIComponent(ticketId)}/approval/start`),
    { method: "POST" },
  );
}

export async function getFinalDocument(
  ticketId: string,
): Promise<RfpFinalDocumentResponse> {
  return request<RfpFinalDocumentResponse>(
    rfpPath(`/tickets/${encodeURIComponent(ticketId)}/final-document`),
  );
}

/** Fetch final markdown and trigger a browser download. */
export async function downloadFinalDocument(
  ticketId: string,
  filename?: string,
): Promise<void> {
  const doc = await getFinalDocument(ticketId);
  const blob = new Blob([doc.final_document_markdown], {
    type: "text/markdown;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename ?? `brasaland-proposal-${ticketId.slice(0, 8)}.md`;
  anchor.click();
  URL.revokeObjectURL(url);
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

export function shouldPollRfpTicketList(tickets: RfpTicketSummary[]): boolean {
  return tickets.some((ticket) => shouldPollRfpTicket(ticket.status));
}

export async function getRfpTicketTrace(ticketId: string): Promise<RfpTraceEvent[]> {
  return request<RfpTraceEvent[]>(
    rfpPath(`/tickets/${encodeURIComponent(ticketId)}/trace`),
  );
}

export async function getRfpTicket(ticketId: string): Promise<RfpTicketDetail> {
  return request<RfpTicketDetail>(
    rfpPath(`/tickets/${encodeURIComponent(ticketId)}`),
  );
}

export async function deleteRfpTicket(ticketId: string): Promise<void> {
  await request<void>(
    rfpPath(`/tickets/${encodeURIComponent(ticketId)}`),
    { method: "DELETE" },
  );
}
