/** Access-token persistence in localStorage (client-only). */

import { ACCESS_TOKEN_STORAGE_KEY } from "./auth-config";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
}

export function setAccessToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
}

export function clearAccessToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
}
