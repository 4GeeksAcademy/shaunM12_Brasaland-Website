/** Client for the Brasaland user-management endpoints (admin + self-service). */

import { AuthUser, UserUpdateInput } from "@/types/auth";
import { AuthApiError } from "./auth-api";
import { authorizedFetch } from "./http";

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new AuthApiError(response.status, await response.text());
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function listUsers(): Promise<AuthUser[]> {
  return parse<AuthUser[]>(await authorizedFetch("/users"));
}

export async function getUser(userId: number): Promise<AuthUser> {
  return parse<AuthUser>(await authorizedFetch(`/users/${userId}`));
}

export async function updateUser(
  userId: number,
  payload: UserUpdateInput,
): Promise<AuthUser> {
  return parse<AuthUser>(
    await authorizedFetch(`/users/${userId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function deleteUser(userId: number): Promise<void> {
  await parse<void>(
    await authorizedFetch(`/users/${userId}`, { method: "DELETE" }),
  );
}
