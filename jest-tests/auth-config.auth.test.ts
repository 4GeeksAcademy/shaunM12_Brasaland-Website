import { isPublicPath, PUBLIC_PATHS } from "../uis/backoffice/lib/auth-config";

/**
 * `isPublicPath` is the routing-gate decision: which paths a logged-out user may
 * reach. The boundary cases (look-alike prefixes) are where bugs hide, so they
 * are tested explicitly.
 */
describe("isPublicPath", () => {
  describe("happy path — public routes resolve as public", () => {
    it.each(PUBLIC_PATHS)("treats %s as public", (path) => {
      expect(isPublicPath(path)).toBe(true);
    });

    it("treats nested public paths (e.g. token in the URL) as public", () => {
      expect(isPublicPath("/reset-password/abc123")).toBe(true);
      expect(isPublicPath("/verify-email/xyz")).toBe(true);
    });
  });

  describe("failure mode — gated routes are not public", () => {
    it("treats application routes as gated", () => {
      expect(isPublicPath("/")).toBe(false);
      expect(isPublicPath("/dashboard")).toBe(false);
      expect(isPublicPath("/suppliers")).toBe(false);
      expect(isPublicPath("/account/users")).toBe(false);
    });

    it("does NOT treat look-alike prefixes as public (boundary)", () => {
      // `/loginx` must not be considered public just because it starts with
      // `/login` — only an exact match or a `/login/...` sub-path counts.
      expect(isPublicPath("/loginx")).toBe(false);
      expect(isPublicPath("/registered")).toBe(false);
    });
  });
});
