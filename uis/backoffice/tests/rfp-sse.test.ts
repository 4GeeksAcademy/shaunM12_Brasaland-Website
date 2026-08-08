import { describe, expect, it } from "vitest";

import {
  parseRfpTicketCreatedEvent,
  parseSseMessageBlock,
  resolveRfpEventsStreamPath,
  rfpTicketSummaryFromCreatedEvent,
  RFP_SSE_EVENT_TICKET_CREATED,
  sseReconnectDelayMs,
} from "@/lib/rfp-sse";

describe("rfp sse client helpers", () => {
  it("resolves same-origin events stream path", () => {
    expect(resolveRfpEventsStreamPath()).toBe("/api/rfp/events/stream");
  });

  it("parses SSE message blocks", () => {
    const block = [
      "event: rfp_ticket_created",
      'data: {"ticket_id":"abc","status":"analyzing","created_at":"2026-08-07T00:00:00Z"}',
    ].join("\n");

    expect(parseSseMessageBlock(block)).toEqual({
      event: RFP_SSE_EVENT_TICKET_CREATED,
      data: '{"ticket_id":"abc","status":"analyzing","created_at":"2026-08-07T00:00:00Z"}',
    });
  });

  it("ignores comment lines in SSE blocks", () => {
    const block = ": keep-alive\nevent: ping";
    expect(parseSseMessageBlock(block)).toEqual({ event: "ping", data: undefined });
  });

  it("parses ticket created payloads", () => {
    const event = parseRfpTicketCreatedEvent(
      JSON.stringify({
        ticket_id: "ticket-1",
        status: "analyzing",
        created_at: "2026-08-07T12:00:00Z",
        client_name: "Sunset Bay",
      }),
    );

    expect(event.ticket_id).toBe("ticket-1");
    expect(event.client_name).toBe("Sunset Bay");
  });

  it("builds a list row from sparse SSE metadata", () => {
    const summary = rfpTicketSummaryFromCreatedEvent({
      ticket_id: "ticket-1",
      status: "analyzing",
      created_at: "2026-08-07T12:00:00Z",
      client_name: "Sunset Bay",
    });

    expect(summary.ticket_id).toBe("ticket-1");
    expect(summary.status_label).toBe("analyzing");
    expect(summary.metadata.client_name).toBe("Sunset Bay");
    expect(summary.departments_needed).toEqual([]);
  });

  it("caps reconnect backoff at 30 seconds", () => {
    expect(sseReconnectDelayMs(1)).toBe(1000);
    expect(sseReconnectDelayMs(2)).toBe(2000);
    expect(sseReconnectDelayMs(6)).toBe(30_000);
    expect(sseReconnectDelayMs(10)).toBe(30_000);
  });
});
