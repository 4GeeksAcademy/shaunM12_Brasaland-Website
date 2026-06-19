/** Shared helpers for turning FastAPI error responses into UI-friendly messages. */

interface FastApiErrorDetailItem {
  msg?: string;
  loc?: (string | number)[];
}

interface FastApiError {
  detail?: string | FastApiErrorDetailItem[];
}

/** A single human-readable message for a failed response body. */
export function formatApiError(status: number, body: string): string {
  try {
    const parsed = JSON.parse(body) as FastApiError;
    if (Array.isArray(parsed.detail)) {
      const joined = parsed.detail
        .map((item) => item.msg ?? "Validation error")
        .join("; ");
      if (joined) {
        return joined;
      }
    } else if (typeof parsed.detail === "string" && parsed.detail) {
      return parsed.detail;
    }
  } catch {
    // fall through to raw body
  }
  return body || `Request failed (${status})`;
}

/**
 * Map a 422 validation body to per-field messages, keyed by the last segment
 * of each error's `loc` (e.g. `email`, `password`). Useful for form views.
 */
export function parseFieldErrors(body: string): Record<string, string> {
  const fields: Record<string, string> = {};
  try {
    const parsed = JSON.parse(body) as FastApiError;
    if (Array.isArray(parsed.detail)) {
      for (const item of parsed.detail) {
        const loc = item.loc ?? [];
        const field = loc.length ? String(loc[loc.length - 1]) : "_";
        if (!fields[field]) {
          fields[field] = item.msg ?? "Invalid value";
        }
      }
    }
  } catch {
    // ignore — caller falls back to formatApiError
  }
  return fields;
}
