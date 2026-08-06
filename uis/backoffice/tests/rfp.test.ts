import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import {
  isRfpTerminalStatus,
  RFP_STATUS_ANALYZING,
  RFP_STATUS_DISCARDED,
  RFP_STATUS_FAILED,
  RFP_STATUS_INTAKE_COMPLETE,
  resolveRfpTicketsPath,
  rfpPath,
} from "@/lib/rfp";

const DEPARTMENT_OWNERS: Record<string, string> = {
  marketing: "Camila Ospina",
  operations: "Felipe Guerrero",
  procurement: "Lucia Fernandez",
  training: "Jake Morrison",
};

describe("rfp client helpers", () => {
  it("resolves same-origin ticket list path", () => {
    expect(resolveRfpTicketsPath()).toBe("/api/rfp/tickets");
  });

  it("resolves same-origin ticket detail path", () => {
    expect(rfpPath("/tickets/ticket-abc")).toBe("/api/rfp/tickets/ticket-abc");
  });

  it("detects Part 1 terminal statuses", () => {
    expect(isRfpTerminalStatus(RFP_STATUS_INTAKE_COMPLETE)).toBe(true);
    expect(isRfpTerminalStatus(RFP_STATUS_DISCARDED)).toBe(true);
    expect(isRfpTerminalStatus(RFP_STATUS_FAILED)).toBe(true);
    expect(isRfpTerminalStatus(RFP_STATUS_ANALYZING)).toBe(false);
  });

  it("documents department owners for routing display", () => {
    expect(DEPARTMENT_OWNERS.marketing).toBe("Camila Ospina");
    expect(DEPARTMENT_OWNERS.operations).toBe("Felipe Guerrero");
  });
});

describe("rfp next.config proxy", () => {
  it("rewrites /api/rfp to FastAPI /rfp", () => {
    const configPath = path.resolve(__dirname, "../next.config.mjs");
    const source = readFileSync(configPath, "utf8");
    expect(source).toContain('source: "/api/rfp/:path*"');
    expect(source).toContain("destination: `${apiOrigin}/rfp/:path*`");
  });
});
