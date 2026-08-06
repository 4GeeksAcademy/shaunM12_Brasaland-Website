import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import {
  countTerminalDraftSections,
  hasSectionDraftMismatch,
  isRfpTerminalStatus,
  isSectionDraftTerminal,
  RFP_DRAFT_STATUS_NEEDS_HUMAN_REVIEW,
  RFP_DRAFT_STATUS_PASSED,
  RFP_DRAFT_STATUS_PENDING,
  RFP_STATUS_ANALYZING,
  RFP_STATUS_DISCARDED,
  RFP_STATUS_DRAFTING,
  RFP_STATUS_FAILED,
  RFP_STATUS_INTAKE_COMPLETE,
  RFP_STATUS_UNDER_EVALUATION,
  RFP_STATUS_WAITING_FOR_APPROVAL,
  resolveRfpTicketsPath,
  rfpPath,
  shouldPollRfpTicket,
  shouldPollRfpTicketDetail,
  type RfpSection,
  type RfpTicketDetail,
} from "@/lib/rfp";

const DEPARTMENT_OWNERS: Record<string, string> = {
  marketing: "Camila Ospina",
  operations: "Felipe Guerrero",
  procurement: "Lucia Fernandez",
  training: "Jake Morrison",
};

describe("rfp client helpers", () => {
  it("resolves same-origin ticket list path", () => {
    expect(resolveRfpTicketsPath()).toBe("/api/rfp/tickets");
  });

  it("resolves same-origin ticket detail path", () => {
    expect(rfpPath("/tickets/ticket-abc")).toBe("/api/rfp/tickets/ticket-abc");
  });

  it("detects Part 1 terminal statuses", () => {
    expect(isRfpTerminalStatus(RFP_STATUS_INTAKE_COMPLETE)).toBe(true);
    expect(isRfpTerminalStatus(RFP_STATUS_DISCARDED)).toBe(true);
    expect(isRfpTerminalStatus(RFP_STATUS_FAILED)).toBe(true);
    expect(isRfpTerminalStatus(RFP_STATUS_ANALYZING)).toBe(false);
    expect(isRfpTerminalStatus(RFP_STATUS_DRAFTING)).toBe(false);
    expect(isRfpTerminalStatus(RFP_STATUS_WAITING_FOR_APPROVAL)).toBe(false);
  });

  it("polls during intake and P2 in-progress statuses", () => {
    expect(shouldPollRfpTicket(RFP_STATUS_ANALYZING)).toBe(true);
    expect(shouldPollRfpTicket(RFP_STATUS_DRAFTING)).toBe(true);
    expect(shouldPollRfpTicket(RFP_STATUS_UNDER_EVALUATION)).toBe(true);
    expect(shouldPollRfpTicket(RFP_STATUS_INTAKE_COMPLETE)).toBe(false);
    expect(shouldPollRfpTicket(RFP_STATUS_WAITING_FOR_APPROVAL)).toBe(false);
    expect(shouldPollRfpTicket(RFP_STATUS_FAILED)).toBe(false);
  });

  it("resolves draft start path", () => {
    expect(rfpPath("/tickets/ticket-abc/draft")).toBe(
      "/api/rfp/tickets/ticket-abc/draft",
    );
  });

  it("resolves ticket delete path", () => {
    expect(rfpPath("/tickets/ticket-abc")).toBe("/api/rfp/tickets/ticket-abc");
  });

  it("detects terminal section draft statuses", () => {
    expect(isSectionDraftTerminal(RFP_DRAFT_STATUS_PASSED)).toBe(true);
    expect(isSectionDraftTerminal(RFP_DRAFT_STATUS_NEEDS_HUMAN_REVIEW)).toBe(true);
    expect(isSectionDraftTerminal(RFP_DRAFT_STATUS_PENDING)).toBe(false);
  });

  it("keeps polling when ticket status and sections disagree", () => {
    const section = (draftStatus: string): RfpSection => ({
      department_id: "marketing",
      department_label: "Marketing",
      department_owner: "Camila Ospina",
      key_aspects: [],
      draft_status: draftStatus,
      draft_status_label: draftStatus,
    });
    const ticket: RfpTicketDetail = {
      ticket_id: "t1",
      status: RFP_STATUS_WAITING_FOR_APPROVAL,
      status_label: "Waiting for approval",
      metadata: {},
      departments_needed: ["marketing", "operations"],
      requires_ceo_approval: false,
      created_at: "2026-01-01",
      updated_at: "2026-01-01",
      unmapped_topics: [],
      conflicts: [],
      markdown_length: 100,
      has_markdown: true,
      sections: [section(RFP_DRAFT_STATUS_PASSED), section(RFP_DRAFT_STATUS_PENDING)],
    };
    expect(hasSectionDraftMismatch(ticket)).toBe(true);
    expect(shouldPollRfpTicketDetail(ticket)).toBe(true);
    expect(countTerminalDraftSections(ticket.sections)).toEqual({
      completed: 1,
      total: 2,
    });
  });

  it("stops polling when all sections are terminal at waiting_for_approval", () => {
    const section: RfpSection = {
      department_id: "marketing",
      department_label: "Marketing",
      department_owner: "Camila Ospina",
      key_aspects: [],
      draft_status: RFP_DRAFT_STATUS_PASSED,
      draft_status_label: "Passed",
    };
    const ticket: RfpTicketDetail = {
      ticket_id: "t1",
      status: RFP_STATUS_WAITING_FOR_APPROVAL,
      status_label: "Waiting for approval",
      metadata: {},
      departments_needed: ["marketing"],
      requires_ceo_approval: false,
      created_at: "2026-01-01",
      updated_at: "2026-01-01",
      unmapped_topics: [],
      conflicts: [],
      markdown_length: 100,
      has_markdown: true,
      sections: [section],
    };
    expect(shouldPollRfpTicketDetail(ticket)).toBe(false);
  });

  it("documents department owners for routing display", () => {
    expect(DEPARTMENT_OWNERS.marketing).toBe("Camila Ospina");
    expect(DEPARTMENT_OWNERS.operations).toBe("Felipe Guerrero");
  });
});

describe("rfp next.config proxy", () => {
  it("rewrites /api/rfp to FastAPI /rfp", () => {
    const configPath = path.resolve(__dirname, "../next.config.mjs");
    const source = readFileSync(configPath, "utf8");
    expect(source).toContain('source: "/api/rfp/:path*"');
    expect(source).toContain("destination: `${apiOrigin}/rfp/:path*`");
  });
});
