/**
 * Authorized fetch wrapper for the Brasaland API.
 *
 * - Attaches `Authorization: Bearer <access token>` from localStorage.
 * - Sends cookies (`credentials: "include"`) so the HttpOnly refresh cookie
 *   rides along to same-origin `/auth/*` calls via the Next proxy.
 * - On `401`, performs a single-flight refresh and retries once. If refresh
 *   fails, clears the session and redirects to `/login`.
 */

import { LOGIN_PATH } from "./auth-config";
import { clearAccessToken, getAccessToken, setAccessToken } from "./auth-storage";

let refreshPromise: Promise<string | null> | null = null;

/**
 * Exchange the refresh cookie for a new access token. Concurrent callers share
 * one in-flight request so rotating refresh tokens don't invalidate each other.
 * Returns the new access token, or `null` if refresh failed. Never redirects.
 */
export function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const response = await fetch("/auth/refresh", {
          method: "POST",
          credentials: "include",
          cache: "no-store",
        });
        if (!response.ok) {
          return null;
        }
        const data = (await response.json()) as { access_token?: string };
        if (!data.access_token) {
          return null;
        }
        setAccessToken(data.access_token);
        return data.access_token;
      } catch {
        return null;
      }
    })();
    void refreshPromise.finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

function withAuthHeaders(init: RequestInit, token: string | null): Headers {
  const headers = new Headers(init.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return headers;
}

function redirectToLogin(): void {
  if (typeof window === "undefined") {
    return;
  }
  const { pathname, search } = window.location;
  if (pathname === LOGIN_PATH) {
    return;
  }
  const next = encodeURIComponent(`${pathname}${search}`);
  window.location.assign(`${LOGIN_PATH}?next=${next}`);
}

function endSessionAndRedirect(): void {
  clearAccessToken();
  redirectToLogin();
}

/**
 * Fetch a protected resource. Adds the bearer token, retries once after a
 * silent refresh on `401`, and bounces to `/login` if the session is gone.
 */
export async function authorizedFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const run = (token: string | null): Promise<Response> =>
    fetch(path, {
      ...init,
      credentials: "include",
      cache: "no-store",
      headers: withAuthHeaders(init, token),
    });

  let response = await run(getAccessToken());
  if (response.status !== 401) {
    return response;
  }

  const newToken = await refreshAccessToken();
  if (!newToken) {
    endSessionAndRedirect();
    throw new Error("Your session has expired. Please sign in again.");
  }

  response = await run(newToken);
  if (response.status === 401) {
    endSessionAndRedirect();
    throw new Error("Your session has expired. Please sign in again.");
  }
  return response;
}
