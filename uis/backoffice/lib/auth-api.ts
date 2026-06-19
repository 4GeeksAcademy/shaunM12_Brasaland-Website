/** Client for the Brasaland auth endpoints (same-origin via the Next proxy). */

import { AuthUser, TokenResponse } from "@/types/auth";
import { formatApiError } from "./api-error";
import { authorizedFetch, refreshAccessToken } from "./http";
import {
  clearAccessToken,
  getAccessToken,
  setAccessToken,
} from "./auth-storage";

/** Raised on a non-OK response; carries status + parsed message + raw body. */
export class AuthApiError extends Error {
  status: number;
  body: string;

  constructor(status: number, body: string) {
    super(formatApiError(status, body));
    this.name = "AuthApiError";
    this.status = status;
    this.body = body;
  }
}

async function readError(response: Response): Promise<AuthApiError> {
  const body = await response.text();
  return new AuthApiError(response.status, body);
}

export async function login(email: string, password: string): Promise<void> {
  // OAuth2 password flow expects form-encoded `username`/`password`.
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);

  const response = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    throw await readError(response);
  }
  const data = (await response.json()) as TokenResponse;
  setAccessToken(data.access_token);
}

export async function register(
  email: string,
  password: string,
  name: string,
): Promise<void> {
  const response = await fetch("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name: name || null }),
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    throw await readError(response);
  }
  const data = (await response.json()) as TokenResponse;
  setAccessToken(data.access_token);
}

/**
 * Resolve the current user without redirecting on failure. Used to hydrate the
 * session on mount (so visiting `/login` doesn't bounce). Returns `null` when
 * there is no valid session.
 */
export async function fetchCurrentUser(): Promise<AuthUser | null> {
  let token = getAccessToken();
  if (!token) {
    token = await refreshAccessToken();
    if (!token) {
      return null;
    }
  }

  const requestMe = (bearer: string): Promise<Response> =>
    fetch("/auth/me", {
      headers: { Authorization: `Bearer ${bearer}` },
      credentials: "include",
      cache: "no-store",
    });

  let response = await requestMe(token);
  if (response.status === 401) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) {
      clearAccessToken();
      return null;
    }
    response = await requestMe(refreshed);
  }
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as AuthUser;
}

export async function logout(): Promise<void> {
  try {
    await fetch("/auth/logout", {
      method: "POST",
      credentials: "include",
      cache: "no-store",
    });
  } finally {
    clearAccessToken();
  }
}

export async function logoutAll(): Promise<void> {
  try {
    await authorizedFetch("/auth/logout-all", { method: "POST" });
  } finally {
    clearAccessToken();
  }
}

export async function verifyEmail(token: string): Promise<void> {
  const response = await fetch("/auth/verify-email", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
    cache: "no-store",
  });
  if (!response.ok) {
    throw await readError(response);
  }
}

export async function resendVerification(): Promise<void> {
  const response = await authorizedFetch("/auth/resend-verification", {
    method: "POST",
  });
  if (!response.ok) {
    throw await readError(response);
  }
}
