import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { authorizedFetch } from "@/lib/http";
import { ACCESS_TOKEN_STORAGE_KEY } from "@/lib/auth-config";
import { getAccessToken } from "@/lib/auth-storage";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const assign = vi.fn();

beforeEach(() => {
  window.localStorage.clear();
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, "old-token");
  assign.mockReset();
  Object.defineProperty(window, "location", {
    value: { pathname: "/suppliers", search: "", assign },
    writable: true,
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("authorizedFetch", () => {
  it("refreshes once for concurrent 401s, then retries with the new token", async () => {
    let refreshCount = 0;
    const fetchMock = vi.fn(async (url: string | URL, init?: RequestInit) => {
      const target = String(url);
      if (target.includes("/auth/refresh")) {
        refreshCount += 1;
        return jsonResponse(200, { access_token: "new-token" });
      }
      const auth = new Headers(init?.headers).get("Authorization");
      if (auth === "Bearer new-token") {
        return jsonResponse(200, { ok: true });
      }
      return jsonResponse(401, { detail: "expired" });
    });
    vi.stubGlobal("fetch", fetchMock);

    const [a, b] = await Promise.all([
      authorizedFetch("/api/suppliers"),
      authorizedFetch("/api/suppliers"),
    ]);

    expect(a.status).toBe(200);
    expect(b.status).toBe(200);
    expect(refreshCount).toBe(1);
    expect(getAccessToken()).toBe("new-token");
  });

  it("clears the session and redirects to login when refresh fails", async () => {
    const fetchMock = vi.fn(async (url: string | URL) => {
      const target = String(url);
      if (target.includes("/auth/refresh")) {
        return jsonResponse(401, { detail: "no session" });
      }
      return jsonResponse(401, { detail: "expired" });
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(authorizedFetch("/api/suppliers")).rejects.toThrow(/session/i);
    expect(getAccessToken()).toBeNull();
    expect(assign).toHaveBeenCalledWith(expect.stringContaining("/login"));
  });
});
