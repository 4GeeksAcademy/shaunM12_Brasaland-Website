import {
  Candidate,
  CandidateInput,
  CandidateNote,
  CandidatePatchInput,
} from "@/types/api";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_TRACKER_API_BASE_URL ??
  "https://playground.4geeks.com/tracker/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

function toArray<T>(value: unknown): T[] {
  if (Array.isArray(value)) {
    return value as T[];
  }

  if (value && typeof value === "object") {
    const objectValue = value as Record<string, unknown>;

    if (Array.isArray(objectValue.results)) {
      return objectValue.results as T[];
    }

    if (Array.isArray(objectValue.items)) {
      return objectValue.items as T[];
    }

    if (Array.isArray(objectValue.data)) {
      return objectValue.data as T[];
    }
  }

  return [];
}

function getTotalCount(value: unknown): number | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const objectValue = value as Record<string, unknown>;
  if (typeof objectValue.count === "number") {
    return objectValue.count;
  }

  if (typeof objectValue.total === "number") {
    return objectValue.total;
  }

  return null;
}

function toPositiveInt(value: string | undefined, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback;
}

function normalizeNote(raw: unknown, index: number): CandidateNote {
  if (typeof raw === "string") {
    return {
      id: `${index}`,
      content: raw,
    };
  }

  if (raw && typeof raw === "object") {
    const note = raw as Record<string, unknown>;
    return {
      id: String(note.id ?? note.note_id ?? note._id ?? index),
      content: String(note.content ?? note.note ?? ""),
      created_at:
        typeof note.created_at === "string" ? note.created_at : undefined,
    };
  }

  return {
    id: `${index}`,
    content: "",
  };
}

export async function getRecords(params?: {
  status?: string;
  stage?: string;
  search?: string;
  page?: string;
  limit?: string;
}): Promise<Candidate[]> {
  const baseParams = new URLSearchParams();
  if (params?.status) baseParams.set("status", params.status);
  if (params?.stage) baseParams.set("stage", params.stage);
  if (params?.search) baseParams.set("search", params.search);

  // If caller explicitly requests a page, preserve single-page behavior.
  if (params?.page) {
    baseParams.set("page", params.page);
    if (params?.limit) baseParams.set("limit", params.limit);

    const query = baseParams.toString();
    const data = await request<unknown>(`/records${query ? `?${query}` : ""}`);
    return toArray<Candidate>(data);
  }

  const pageSize = toPositiveInt(params?.limit, 100);
  const allRecords: Candidate[] = [];
  const seenIds = new Set<string>();
  const maxPages = 200;

  for (let page = 1; page <= maxPages; page += 1) {
    const pageParams = new URLSearchParams(baseParams.toString());
    pageParams.set("page", String(page));
    pageParams.set("limit", String(pageSize));

    const query = pageParams.toString();
    const rawPage = await request<unknown>(`/records?${query}`);
    const pageItems = toArray<Candidate>(rawPage);

    if (pageItems.length === 0) {
      break;
    }

    let newlyAdded = 0;
    for (const item of pageItems) {
      const id = String((item as { id?: unknown }).id ?? "");

      if (id && seenIds.has(id)) {
        continue;
      }

      if (id) {
        seenIds.add(id);
      }

      allRecords.push(item);
      newlyAdded += 1;
    }

    // Defensive break if backend ignores page and starts repeating data.
    if (newlyAdded === 0) {
      break;
    }

    const totalCount = getTotalCount(rawPage);
    if (totalCount !== null && allRecords.length >= totalCount) {
      break;
    }

    if (pageItems.length < pageSize) {
      break;
    }
  }

  return allRecords;
}

export async function getRecordById(id: string): Promise<Candidate> {
  return request<Candidate>(`/records/${id}`);
}

export async function createRecord(payload: CandidateInput): Promise<Candidate> {
  return request<Candidate>("/records", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function replaceRecord(
  id: string,
  payload: CandidateInput,
): Promise<Candidate> {
  return request<Candidate>(`/records/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function patchRecord(
  id: string,
  payload: CandidatePatchInput,
): Promise<Candidate> {
  return request<Candidate>(`/records/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteRecord(id: string): Promise<void> {
  await request<void>(`/records/${id}`, {
    method: "DELETE",
  });
}

export async function getNotesByRecordId(id: string): Promise<CandidateNote[]> {
  const raw = await request<unknown>(`/records/${id}/notes`);
  return toArray<unknown>(raw).map(normalizeNote).filter((note) => note.content);
}

export async function addNote(id: string, content: string): Promise<unknown> {
  return request<unknown>(`/records/${id}/notes`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export async function deleteNote(id: string, noteId: string): Promise<void> {
  await request<void>(`/records/${id}/notes/${noteId}`, {
    method: "DELETE",
  });
}
