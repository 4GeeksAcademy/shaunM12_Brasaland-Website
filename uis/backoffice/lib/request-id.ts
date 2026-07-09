function uuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`;
}

let activeCorrelatedRequestId: string | null = null;

/** Create a fresh request correlation id. */
export function nextRequestId(): string {
  return `req_${uuid()}`;
}

/** Begin a correlated client action (e.g. order submit) shared by fetch + telemetry. */
export function beginCorrelatedRequest(): string {
  activeCorrelatedRequestId = nextRequestId();
  return activeCorrelatedRequestId;
}

/** Reuse the active correlated id when present; otherwise allocate a new one. */
export function getCorrelatedRequestId(): string {
  return activeCorrelatedRequestId ?? nextRequestId();
}

export function endCorrelatedRequest(): void {
  activeCorrelatedRequestId = null;
}

export async function withCorrelatedRequest<T>(fn: () => Promise<T>): Promise<T> {
  beginCorrelatedRequest();
  try {
    return await fn();
  } finally {
    endCorrelatedRequest();
  }
}
