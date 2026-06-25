import type { Config } from "jest";

/**
 * Jest is scoped to the authentication-related TypeScript utilities only, via
 * the `*.auth.test.ts` naming convention. This keeps it from colliding with the
 * repository's existing Vitest suites (`npm test`), which remain unchanged.
 *
 * The utilities under test are pure (no DOM, no network), so the lightweight
 * `node` environment is used and `window`/`localStorage` are stubbed in the one
 * spec that needs them.
 */
const config: Config = {
  testEnvironment: "node",
  // Specs live in a dedicated top-level dir, isolated from the repository's
  // Vitest globs and from the backoffice's Next.js/tsc compilation.
  roots: ["<rootDir>/jest-tests"],
  testMatch: ["**/*.auth.test.ts"],
  transform: {
    "^.+\\.tsx?$": [
      "ts-jest",
      {
        // Inline tsconfig so ts-jest doesn't inherit the root project's
        // `rootDir`/`include`, which are scoped to `src/`.
        tsconfig: {
          target: "ES2022",
          module: "commonjs",
          moduleResolution: "node",
          esModuleInterop: true,
          strict: true,
          skipLibCheck: true,
          resolveJsonModule: true,
          types: ["jest", "node"],
        },
      },
    ],
  },
  collectCoverageFrom: [
    "uis/backoffice/lib/auth-config.ts",
    "uis/backoffice/lib/api-error.ts",
    "uis/backoffice/lib/auth-storage.ts",
  ],
  coverageDirectory: "<rootDir>/coverage/jest-auth",
};

export default config;
