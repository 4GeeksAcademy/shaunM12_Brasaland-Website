import { describe, expect, it } from "vitest";

import { formatApiError, parseFieldErrors } from "@/lib/api-error";

describe("formatApiError", () => {
  it("joins FastAPI validation detail arrays", () => {
    const body = JSON.stringify({
      detail: [{ msg: "field required" }, { msg: "too short" }],
    });
    expect(formatApiError(422, body)).toBe("field required; too short");
  });

  it("returns string detail as-is", () => {
    expect(formatApiError(400, JSON.stringify({ detail: "Email already registered" }))).toBe(
      "Email already registered",
    );
  });

  it("falls back to raw body then status", () => {
    expect(formatApiError(500, "boom")).toBe("boom");
    expect(formatApiError(500, "")).toBe("Request failed (500)");
  });
});

describe("parseFieldErrors", () => {
  it("keys messages by the last loc segment", () => {
    const body = JSON.stringify({
      detail: [
        { loc: ["body", "email"], msg: "not an email" },
        { loc: ["body", "password"], msg: "too short" },
      ],
    });
    expect(parseFieldErrors(body)).toEqual({
      email: "not an email",
      password: "too short",
    });
  });

  it("returns empty object for non-validation bodies", () => {
    expect(parseFieldErrors(JSON.stringify({ detail: "nope" }))).toEqual({});
  });
});
