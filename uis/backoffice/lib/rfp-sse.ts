/** RFP SSE client (context-28 Milestone 10 Part 1 — Phase 2). */

import { authorizedFetch } from "@/lib/http";
import { rfpPath, type RfpTicketSummary } from "@/lib/rfp";

export const RFP_SSE_EVENT_TICKET_CREATED = "rfp_ticket_created";

export type RfpSseConnectionState =
  | "connecting"
  | "live"
  | "reconnecting"
  | "stopped";

export interface RfpTicketCreatedEvent {
  ticket_id: string;
  status: string;
  created_at: string;
  client_name?: string | null;
  location?: string | null;
  service_type?: string | null;
}

export interface RfpSseClientOptions {
  onTicketCreated: (event: RfpTicketCreatedEvent) => void;
  onStateChange?: (state: RfpSseConnectionState) => void;
  /** Refetch-then-SSE: called before each reconnect attempt after the first. */
  onRecover?: () => Promise<void>;
  signal?: AbortSignal;
}

function getBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_RFP_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "";
}

export function resolveRfpEventsStreamPath(): string {
  return rfpPath("/events/stream");
}

export function sseReconnectDelayMs(attempt: number): number {
  const base = Math.min(1000 * 2 ** Math.max(attempt - 1, 0), 30_000);
  return base;
}

export function parseSseMessageBlock(block: string): {
  event?: string;
  data?: string;
} {
  let eventName: string | undefined;
  const dataLines: string[] = [];

  for (const line of block.split("\n")) {
    if (!line || line.startsWith(":")) {
      continue;
    }
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  return {
    event: eventName,
    data: dataLines.length ? dataLines.join("\n") : undefined,
  };
}

export function parseRfpTicketCreatedEvent(raw: string): RfpTicketCreatedEvent {
  const parsed = JSON.parse(raw) as RfpTicketCreatedEvent;
  if (!parsed.ticket_id || !parsed.status || !parsed.created_at) {
    throw new Error("Invalid rfp_ticket_created payload.");
  }
  return parsed;
}

export function rfpTicketSummaryFromCreatedEvent(
  event: RfpTicketCreatedEvent,
): RfpTicketSummary {
  const metadata: Record<string, unknown> = {};
  if (event.client_name) {
    metadata.client_name = event.client_name;
  }
  if (event.location) {
    metadata.location = event.location;
  }
  if (event.service_type) {
    metadata.service_type = event.service_type;
  }

  return {
    ticket_id: event.ticket_id,
    status: event.status,
    status_label: event.status.replaceAll("_", " "),
    metadata,
    departments_needed: [],
    requires_ceo_approval: false,
    created_at: event.created_at,
    updated_at: event.created_at,
  };
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = window.setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      window.clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    };
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

async function consumeSseStream(
  body: ReadableStream<Uint8Array>,
  options: RfpSseClientOptions,
  signal: AbortSignal,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (!signal.aborted) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });

      let boundary = buffer.indexOf("\n\n");
      while (boundary >= 0) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const message = parseSseMessageBlock(block);
        if (
          message.event === RFP_SSE_EVENT_TICKET_CREATED &&
          message.data
        ) {
          options.onTicketCreated(parseRfpTicketCreatedEvent(message.data));
        }
        boundary = buffer.indexOf("\n\n");
      }
    }
  } finally {
    reader.releaseLock();
  }
}

async function runRfpSseClient(options: RfpSseClientOptions): Promise<void> {
  const signal = options.signal;
  if (!signal) {
    throw new Error("RFP SSE client requires an AbortSignal.");
  }

  let attempt = 0;

  while (!signal.aborted) {
    if (attempt === 0) {
      options.onStateChange?.("connecting");
    } else {
      options.onStateChange?.("reconnecting");
      await sleep(sseReconnectDelayMs(attempt), signal);
      if (options.onRecover) {
        await options.onRecover();
      }
    }

    let response: Response;
    try {
      response = await authorizedFetch(`${getBaseUrl()}${resolveRfpEventsStreamPath()}`, {
        headers: { Accept: "text/event-stream" },
        cache: "no-store",
        signal,
      });
    } catch (caught) {
      if (signal.aborted) {
        break;
      }
      attempt += 1;
      continue;
    }

    if (!response.ok) {
      await response.text();
      if (signal.aborted) {
        break;
      }
      options.onStateChange?.("reconnecting");
      attempt += 1;
      await sleep(sseReconnectDelayMs(attempt), signal);
      continue;
    }

    if (!response.body) {
      attempt += 1;
      await sleep(sseReconnectDelayMs(attempt), signal);
      continue;
    }

    options.onStateChange?.("live");
    attempt = 0;

    try {
      await consumeSseStream(response.body, options, signal);
    } catch {
      if (signal.aborted) {
        break;
      }
    }

    if (signal.aborted) {
      break;
    }
    attempt += 1;
  }

  options.onStateChange?.("stopped");
}

/** Start the SSE client; returns a disconnect function. */
export function connectRfpTicketStream(options: RfpSseClientOptions): () => void {
  const controller = new AbortController();
  const mergedSignal = options.signal;

  if (mergedSignal) {
    if (mergedSignal.aborted) {
      controller.abort();
    } else {
      mergedSignal.addEventListener(
        "abort",
        () => controller.abort(),
        { once: true },
      );
    }
  }

  void runRfpSseClient({ ...options, signal: controller.signal });

  return () => {
    controller.abort();
    options.onStateChange?.("stopped");
  };
}
