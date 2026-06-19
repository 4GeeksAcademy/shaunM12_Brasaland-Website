/**
 * Shared auth configuration used by the client, middleware, and providers.
 *
 * The access token lives in localStorage; the refresh token is an HttpOnly
 * cookie set by the API (read only by middleware on the server, never by JS).
 */

export const ACCESS_TOKEN_STORAGE_KEY = "brasaland_access_token";

export const REFRESH_COOKIE_NAME =
  process.env.NEXT_PUBLIC_REFRESH_COOKIE_NAME ?? "brasaland_refresh";

export const LOGIN_PATH = "/login";
export const HOME_PATH = "/";

/** Routes reachable without a session. Everything else is gated. */
export const PUBLIC_PATHS = ["/login", "/register", "/verify-email"] as const;

export function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some(
    (base) => pathname === base || pathname.startsWith(`${base}/`),
  );
}
