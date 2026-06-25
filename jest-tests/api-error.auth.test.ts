import {
  formatApiError,
  parseFieldErrors,
} from "../uis/backoffice/lib/api-error";

/**
 * These helpers turn raw FastAPI error bodies into UI-safe messages. The logic
 * decision is: extract a meaningful message when possible, and degrade safely
 * (never throw, never surface raw internals) when the body is unexpected.
 */
describe("formatApiError", () => {
  describe("happy path", () => {
    it("returns a string `detail` verbatim", () => {
      const body = JSON.stringify({ detail: "Incorrect email or password" });
      expect(formatApiError(401, body)).toBe("Incorrect email or password");
    });

    it("joins a validation-error array into one message", () => {
      const body = JSON.stringify({
        detail: [{ msg: "field required" }, { msg: "too short" }],
      });
      expect(formatApiError(422, body)).toBe("field required; too short");
    });

    it("substitutes a default when array items lack a msg", () => {
      const body = JSON.stringify({ detail: [{}, {}] });
      expect(formatApiError(422, body)).toBe("Validation error; Validation error");
    });
  });

  describe("failure mode — degrades safely", () => {
    it("falls back to the raw body when it is not JSON", () => {
      expect(formatApiError(500, "Internal Server Error")).toBe(
        "Internal Server Error",
      );
    });

    it("falls back to a status message when the body is empty", () => {
      expect(formatApiError(503, "")).toBe("Request failed (503)");
    });
  });
});

describe("parseFieldErrors", () => {
  describe("happy path", () => {
    it("keys messages by the last segment of `loc`", () => {
      const body = JSON.stringify({
        detail: [
          { loc: ["body", "email"], msg: "invalid email" },
          { loc: ["body", "password"], msg: "too short" },
        ],
      });
      expect(parseFieldErrors(body)).toEqual({
        email: "invalid email",
        password: "too short",
      });
    });
  });

  describe("failure mode", () => {
    it("returns an empty map for a non-JSON body", () => {
      expect(parseFieldErrors("not json")).toEqual({});
    });

    it("uses `_` as the key when `loc` is missing", () => {
      const body = JSON.stringify({ detail: [{ msg: "general error" }] });
      expect(parseFieldErrors(body)).toEqual({ _: "general error" });
    });

    it("keeps the first message when a field appears twice", () => {
      const body = JSON.stringify({
        detail: [
          { loc: ["body", "email"], msg: "first" },
          { loc: ["body", "email"], msg: "second" },
        ],
      });
      expect(parseFieldErrors(body)).toEqual({ email: "first" });
    });
  });
});
