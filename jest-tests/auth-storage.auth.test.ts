import {
  clearAccessToken,
  getAccessToken,
  setAccessToken,
} from "../uis/backoffice/lib/auth-storage";

/**
 * Access-token persistence. The decisions under test:
 *  - happy path: set → get → clear round-trips through `localStorage`.
 *  - failure mode (SSR): with no `window`, every call is a safe no-op / null,
 *    never a thrown ReferenceError.
 *
 * Runs in the `node` environment, so `window` is undefined by default; the happy
 * path stubs a minimal `window.localStorage`.
 */

function installFakeWindow(): Record<string, string> {
  const store: Record<string, string> = {};
  (globalThis as unknown as { window: unknown }).window = {
    localStorage: {
      getItem: (k: string) => (k in store ? store[k] : null),
      setItem: (k: string, v: string) => {
        store[k] = v;
      },
      removeItem: (k: string) => {
        delete store[k];
      },
    },
  };
  return store;
}

function removeWindow(): void {
  delete (globalThis as unknown as { window?: unknown }).window;
}

describe("auth-storage", () => {
  afterEach(() => {
    removeWindow();
  });

  describe("happy path (browser)", () => {
    it("round-trips a token through set → get → clear", () => {
      installFakeWindow();

      expect(getAccessToken()).toBeNull();

      setAccessToken("jwt-abc");
      expect(getAccessToken()).toBe("jwt-abc");

      clearAccessToken();
      expect(getAccessToken()).toBeNull();
    });
  });

  describe("failure mode (server-side render, no window)", () => {
    it("getAccessToken returns null instead of throwing", () => {
      expect(getAccessToken()).toBeNull();
    });

    it("setAccessToken / clearAccessToken are safe no-ops", () => {
      expect(() => setAccessToken("ignored")).not.toThrow();
      expect(() => clearAccessToken()).not.toThrow();
    });
  });
});
