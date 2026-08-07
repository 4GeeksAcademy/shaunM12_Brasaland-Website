import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { listManagedIncidents } from "@/lib/incidents-api";
import { listManagerIncidents } from "@/lib/incidents-manager-api";
import { fetchTaskStatus, taskPath } from "@/lib/tasks-api";
import { fetchSuppliers } from "@/lib/suppliers-api";
import { resolveAgentQueryPath } from "@/lib/agent";
import { getRfpTicket, listRfpTickets, resolveRfpTicketsPath } from "@/lib/rfp";
import { resolveRfpEventsStreamPath } from "@/lib/rfp-sse";
import { resolveTelemetryEndpoint } from "@/lib/telemetry";

const { authorizedFetchMock } = vi.hoisted(() => ({
  authorizedFetchMock: vi.fn(),
}));

vi.mock("@/lib/http", () => ({
  authorizedFetch: authorizedFetchMock,
}));

function emptyListResponse(): Response {
  return new Response("[]", {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  delete process.env.NEXT_PUBLIC_SUPPLIERS_API_BASE_URL;
  delete process.env.NEXT_PUBLIC_INCIDENTS_API_BASE_URL;
  delete process.env.NEXT_PUBLIC_TASKS_API_BASE_URL;
  delete process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT;
  delete process.env.NEXT_PUBLIC_TELEMETRY_API_BASE_URL;
  delete process.env.NEXT_PUBLIC_AGENT_API_BASE_URL;
  delete process.env.NEXT_PUBLIC_RFP_API_BASE_URL;
  authorizedFetchMock.mockReset();
  authorizedFetchMock.mockImplementation(async () => emptyListResponse());
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("domain API route paths", () => {
  it("uses browser-facing /api paths for same-origin requests", async () => {
    await fetchSuppliers();
    await listManagedIncidents();
    await listManagerIncidents();

    expect(authorizedFetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/suppliers",
      undefined,
    );
    expect(authorizedFetchMock).toHaveBeenNthCalledWith(2, "/api/incidents");
    expect(authorizedFetchMock).toHaveBeenNthCalledWith(3, "/api/incidents");
  });

  it("uses bare FastAPI mounts for direct API requests", async () => {
    vi.stubEnv(
      "NEXT_PUBLIC_SUPPLIERS_API_BASE_URL",
      "https://api.example.test/",
    );
    vi.stubEnv(
      "NEXT_PUBLIC_INCIDENTS_API_BASE_URL",
      "https://api.example.test/",
    );

    await fetchSuppliers();
    await listManagedIncidents();
    await listManagerIncidents();

    expect(authorizedFetchMock).toHaveBeenNthCalledWith(
      1,
      "https://api.example.test/suppliers",
      undefined,
    );
    expect(authorizedFetchMock).toHaveBeenNthCalledWith(
      2,
      "https://api.example.test/incidents",
    );
    expect(authorizedFetchMock).toHaveBeenNthCalledWith(
      3,
      "https://api.example.test/incidents",
    );
  });

  it("uses browser-facing /api paths for telemetry and tasks", () => {
    expect(resolveTelemetryEndpoint()).toBe("/api/telemetry/events");
    expect(taskPath("abc-123")).toBe("/api/tasks/abc-123");
  });

  it("uses bare FastAPI mounts for direct telemetry and tasks requests", async () => {
    vi.stubEnv("NEXT_PUBLIC_TELEMETRY_API_BASE_URL", "https://api.example.test/");
    vi.stubEnv("NEXT_PUBLIC_TASKS_API_BASE_URL", "https://api.example.test/");

    expect(resolveTelemetryEndpoint()).toBe(
      "https://api.example.test/telemetry/events",
    );
    expect(taskPath("abc-123")).toBe("/tasks/abc-123");

    await fetchTaskStatus("abc-123");
    expect(authorizedFetchMock).toHaveBeenCalledWith(
      "https://api.example.test/tasks/abc-123",
    );
  });

  it("honors explicit NEXT_PUBLIC_TELEMETRY_ENDPOINT overrides", () => {
    vi.stubEnv(
      "NEXT_PUBLIC_TELEMETRY_ENDPOINT",
      "https://api.example.test/telemetry/events",
    );
    expect(resolveTelemetryEndpoint()).toBe(
      "https://api.example.test/telemetry/events",
    );
  });

  it("uses browser-facing /api paths for the support agent", () => {
    expect(resolveAgentQueryPath()).toBe("/api/agent/query");
  });

  it("uses bare FastAPI mounts for direct support agent requests", () => {
    vi.stubEnv("NEXT_PUBLIC_AGENT_API_BASE_URL", "https://api.example.test/");
    expect(resolveAgentQueryPath()).toBe("/agent/query");
  });

  it("uses browser-facing /api paths for RFP tickets", () => {
    expect(resolveRfpTicketsPath()).toBe("/api/rfp/tickets");
    expect(resolveRfpEventsStreamPath()).toBe("/api/rfp/events/stream");
  });

  it("uses bare FastAPI mounts for direct RFP requests", () => {
    vi.stubEnv("NEXT_PUBLIC_RFP_API_BASE_URL", "https://api.example.test/");
    expect(resolveRfpTicketsPath()).toBe("/rfp/tickets");
    expect(resolveRfpEventsStreamPath()).toBe("/rfp/events/stream");
  });

  it("uses browser-facing /api paths for RFP list and detail clients", async () => {
    authorizedFetchMock.mockImplementation(async (url: string) => {
      if (url.endsWith("/tickets/ticket-abc")) {
        return new Response(
          JSON.stringify({
            ticket_id: "ticket-abc",
            status: "discarded",
            metadata: {},
            departments_needed: [],
            requires_ceo_approval: false,
            created_at: "2026-08-06T00:00:00Z",
            updated_at: "2026-08-06T00:00:00Z",
            unmapped_topics: [],
            conflicts: [],
            markdown_length: 0,
            has_markdown: false,
            sections: [],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return emptyListResponse();
    });

    await listRfpTickets();
    await getRfpTicket("ticket-abc");

    expect(authorizedFetchMock).toHaveBeenNthCalledWith(1, "/api/rfp/tickets", undefined);
    expect(authorizedFetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/rfp/tickets/ticket-abc",
      undefined,
    );
  });

  it("uses bare FastAPI mounts for direct RFP detail requests", async () => {
    vi.stubEnv("NEXT_PUBLIC_RFP_API_BASE_URL", "https://api.example.test/");
    authorizedFetchMock.mockImplementation(async () =>
      new Response("{}", {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await getRfpTicket("ticket-abc");

    expect(authorizedFetchMock).toHaveBeenCalledWith(
      "https://api.example.test/rfp/tickets/ticket-abc",
      undefined,
    );
  });
});
