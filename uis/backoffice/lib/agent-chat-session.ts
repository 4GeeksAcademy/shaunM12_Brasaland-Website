/** Support chat session id — localStorage for cross-tab continuity (MEM-092). */

export const SUPPORT_SESSION_STORAGE_KEY = "brasaland_support_session_id";

function readStoredSessionId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return (
    localStorage.getItem(SUPPORT_SESSION_STORAGE_KEY) ??
    sessionStorage.getItem(SUPPORT_SESSION_STORAGE_KEY)
  );
}

function writeStoredSessionId(sessionId: string): void {
  localStorage.setItem(SUPPORT_SESSION_STORAGE_KEY, sessionId);
  sessionStorage.setItem(SUPPORT_SESSION_STORAGE_KEY, sessionId);
}

export function getSupportSessionId(): string {
  if (typeof window === "undefined") {
    return "";
  }
  let sessionId = readStoredSessionId();
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    writeStoredSessionId(sessionId);
  } else if (!localStorage.getItem(SUPPORT_SESSION_STORAGE_KEY)) {
    writeStoredSessionId(sessionId);
  }
  return sessionId;
}

export function resetSupportSessionId(): string {
  const sessionId = crypto.randomUUID();
  if (typeof window !== "undefined") {
    writeStoredSessionId(sessionId);
  }
  return sessionId;
}
