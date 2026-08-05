/** Support Agent API client (context-23 Part 1 Phase 3 + MEM-092 thread continuity). */

import { formatApiError } from "@/lib/api-error";
import { authorizedFetch } from "@/lib/http";

export interface AgentQueryResponse {
  answer: string;
}

export interface AgentQueryRequest {
  question: string;
  thread_id?: string;
}

const SUPPORT_THREAD_STORAGE_KEY = "brasaland_support_thread_id";

function getBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_AGENT_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "";
}

/** Same-origin `/api/agent/*` proxies to FastAPI `/agent/*`. */
function agentPath(suffix: string): string {
  const prefix = getBaseUrl() ? "/agent" : "/api/agent";
  return `${prefix}${suffix}`;
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
      "Cannot reach the Support Agent API. Start it with: npm run api:dev (and Qdrant).",
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

export function getSupportThreadId(): string {
  if (typeof window === "undefined") {
    return "";
  }
  let threadId = sessionStorage.getItem(SUPPORT_THREAD_STORAGE_KEY);
  if (!threadId) {
    threadId = crypto.randomUUID();
    sessionStorage.setItem(SUPPORT_THREAD_STORAGE_KEY, threadId);
  }
  return threadId;
}

export function resetSupportThreadId(): string {
  const threadId = crypto.randomUUID();
  if (typeof window !== "undefined") {
    sessionStorage.setItem(SUPPORT_THREAD_STORAGE_KEY, threadId);
  }
  return threadId;
}

export async function askSupportAgent(
  question: string,
  threadId?: string,
): Promise<AgentQueryResponse> {
  const payload: AgentQueryRequest = { question };
  const resolvedThreadId = threadId ?? getSupportThreadId();
  if (resolvedThreadId) {
    payload.thread_id = resolvedThreadId;
  }
  return request<AgentQueryResponse>(agentPath("/query"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/** Exported for route-path tests (context-22 alignment). */
export function resolveAgentQueryPath(): string {
  return agentPath("/query");
}
