# Technical Context

## Tech Stack
- **Frontend:**
  - Next.js (v16.2.6) and React (v19.2.4) for `uis/website` and `uis/backoffice`
  - Tailwind CSS (v4) for styling
  - Static Brasa Points registration assets served from `uis/website/public`
- **Backend/API:**
  - API integration via REST endpoints (environment-configurable)
- **Tooling:**
  - Node.js/npm for dependency and script management
  - Vitest for unit testing
  - Custom Node.js scripts for static site serving
  - Vercel for deployment

## Architectural Decisions
- **Canonical Directory Structure:**
  - Active UI apps are `uis/website` (public) and `uis/backoffice` (internal).
  - Legacy duplicate app folders are retired when not part of active runtime paths.
- **Centralized Validation:**
  - Validation logic is shared in dedicated modules to prevent duplication and drift.
- **Type Safety:**
  - TypeScript is enforced with strict settings and CI coverage for all subprojects and tests.
- **Deployment Safety:**
  - All deployment rewrites and routes are validated against the real file structure; legacy paths are forbidden.
- **Accessibility:**
  - Accessibility features (skip links, ARIA labels) are baseline requirements for all UI changes.
- **Runtime Dependency Management:**
  - CDN dependencies are allowed only with documented fallbacks or for demo/dev use; production prefers build-time integration.
- **Rule-Driven Engineering:**
  - All development follows a formal ruleset for risk mitigation, code review, and merge gating.

## Technical Constraints
- **No legacy path references:**
  - All code, tests, and configs must use the canonical directory names.
- **Environment configuration required:**
  - API base URLs and other sensitive settings must be provided via environment variables in production/staging.
- **Typecheck and test coverage:**
  - CI must run typechecks and tests for all code, including subprojects and tests.
- **No ad-hoc validation:**
  - All validation must use shared modules; no inline or duplicated logic.
- **Deployment rewrites must match structure:**
  - All rewrite rules must point to existing files/directories; changes require review.
- **Accessibility cannot regress:**
  - UI changes must not remove or break accessibility features.
- **No critical runtime dependency without fallback:**
  - All essential runtime dependencies must have a documented fallback or be bundled at build time.
