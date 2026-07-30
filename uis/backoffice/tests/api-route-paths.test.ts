import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { listManagedIncidents } from "@/lib/incidents-api";
import { listManagerIncidents } from "@/lib/incidents-manager-api";
import { fetchTaskStatus, taskPath } from "@/lib/tasks-api";
import { fetchSuppliers } from "@/lib/suppliers-api";
import { resolveTelemetryEndpoint } from "@/lib/telemetry";

const { authorizedFetchMock } = vi.hoisted(() => ({
  authorizedFetchMock: vi.fn(),
}));

vi.mock("@/lib/http", () => ({
  authorizedFetch: authorizedFetchMock,
}));

function emptyListResponse(): Response {
  return new Response("[]", {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  delete process.env.NEXT_PUBLIC_SUPPLIERS_API_BASE_URL;
  delete process.env.NEXT_PUBLIC_INCIDENTS_API_BASE_URL;
  delete process.env.NEXT_PUBLIC_TASKS_API_BASE_URL;
  delete process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT;
  delete process.env.NEXT_PUBLIC_TELEMETRY_API_BASE_URL;
  authorizedFetchMock.mockReset();
  authorizedFetchMock.mockImplementation(async () => emptyListResponse());
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("domain API route paths", () => {
  it("uses browser-facing /api paths for same-origin requests", async () => {
    await fetchSuppliers();
    await listManagedIncidents();
    await listManagerIncidents();

    expect(authorizedFetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/suppliers",
      undefined,
    );
    expect(authorizedFetchMock).toHaveBeenNthCalledWith(2, "/api/incidents");
    expect(authorizedFetchMock).toHaveBeenNthCalledWith(3, "/api/incidents");
  });

  it("uses bare FastAPI mounts for direct API requests", async () => {
    vi.stubEnv(
      "NEXT_PUBLIC_SUPPLIERS_API_BASE_URL",
      "https://api.example.test/",
    );
    vi.stubEnv(
      "NEXT_PUBLIC_INCIDENTS_API_BASE_URL",
      "https://api.example.test/",
    );

    await fetchSuppliers();
    await listManagedIncidents();
    await listManagerIncidents();

    expect(authorizedFetchMock).toHaveBeenNthCalledWith(
      1,
      "https://api.example.test/suppliers",
      undefined,
    );
    expect(authorizedFetchMock).toHaveBeenNthCalledWith(
      2,
      "https://api.example.test/incidents",
    );
    expect(authorizedFetchMock).toHaveBeenNthCalledWith(
      3,
      "https://api.example.test/incidents",
    );
  });

  it("uses browser-facing /api paths for telemetry and tasks", () => {
    expect(resolveTelemetryEndpoint()).toBe("/api/telemetry/events");
    expect(taskPath("abc-123")).toBe("/api/tasks/abc-123");
  });

  it("uses bare FastAPI mounts for direct telemetry and tasks requests", async () => {
    vi.stubEnv("NEXT_PUBLIC_TELEMETRY_API_BASE_URL", "https://api.example.test/");
    vi.stubEnv("NEXT_PUBLIC_TASKS_API_BASE_URL", "https://api.example.test/");

    expect(resolveTelemetryEndpoint()).toBe(
      "https://api.example.test/telemetry/events",
    );
    expect(taskPath("abc-123")).toBe("/tasks/abc-123");

    await fetchTaskStatus("abc-123");
    expect(authorizedFetchMock).toHaveBeenCalledWith(
      "https://api.example.test/tasks/abc-123",
    );
  });

  it("honors explicit NEXT_PUBLIC_TELEMETRY_ENDPOINT overrides", () => {
    vi.stubEnv(
      "NEXT_PUBLIC_TELEMETRY_ENDPOINT",
      "https://api.example.test/telemetry/events",
    );
    expect(resolveTelemetryEndpoint()).toBe(
      "https://api.example.test/telemetry/events",
    );
  });
});
