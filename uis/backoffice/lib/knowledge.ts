/** Knowledge RAG API client (context-21 Phase 4). */

import { formatApiError } from "@/lib/api-error";
import { authorizedFetch } from "@/lib/http";

export interface KnowledgeQueryResponse {
  answer: string;
}

export interface KnowledgeReindexResponse {
  status: string;
  chunks_indexed: number;
}

function getBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_KNOWLEDGE_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "";
}

/** Same-origin `/api/knowledge/*` proxies to FastAPI `/knowledge/*`. */
function knowledgePath(suffix: string): string {
  const prefix = getBaseUrl() ? "/knowledge" : "/api/knowledge";
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
      "Cannot reach the knowledge API. Start it with: npm run api:dev (and Qdrant).",
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

export async function askKnowledgeQuestion(
  question: string,
): Promise<KnowledgeQueryResponse> {
  return request<KnowledgeQueryResponse>(knowledgePath("/query"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}

export async function reindexKnowledge(): Promise<KnowledgeReindexResponse> {
  return request<KnowledgeReindexResponse>(knowledgePath("/reindex"), {
    method: "POST",
  });
}
