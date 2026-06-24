import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // Root suite covers shared TypeScript utilities under src/ (tests live in tests/).
    // App-level suites (e.g. uis/backoffice) run under their own vitest config.
    include: ["tests/**/*.test.ts"],
  },
});
