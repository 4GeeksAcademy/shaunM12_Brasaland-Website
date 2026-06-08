# Project Progress

## Current State of Development
- **Repository Structure:**
  - Active UI runtime is consolidated to `uis/website` and `uis/backoffice`.
  - Legacy duplicate app code has been removed from runtime paths.
  - Context, rules, and technical documentation consolidated in the `memory-bank` and `.agents` directories.
- **Validation:**
  - Validation logic is centralized and deduplicated; all forms and business logic use shared validators.
- **Type Safety & Testing:**
  - TypeScript strict mode enforced; typecheck and test coverage required for all subprojects and tests.
  - Unit tests in place for core business logic and validation.
- **Deployment:**
  - Vercel configuration updated; deployment rewrites and routes validated against the real file structure.
- **Accessibility:**
  - Accessibility features (skip links, ARIA labels) are present and required for all UI changes.
- **Rules & Risk Mitigation:**
  - Comprehensive, actionable ruleset created and refined; rules are now directly connected to real workflows and enforced in reviews.
- **Documentation:**
  - Business, technical, and ruleset documentation is up to date and accessible in `memory-bank`.
- **Agent Governance:**
  - Root `agents.md` now exists with required startup memory reads, pre-commit workflow steps, and protected path rules.
- **Milestone 2 Visibility in Backoffice:**
  - Backoffice dashboard now renders a visible shared-business-logic snapshot alongside live API KPI cards.

## Planned Next Steps
- **Path Consistency Cleanup:**
  - Refactor all remaining legacy path references in code, tests, and deployment configs to use canonical names.
- **Rewrite & Routing Validation:**
  - Update and test all deployment rewrites to ensure no 404s or broken routes.
- **CI/CD Hardening:**
  - Ensure all typecheck and test scripts are run in CI for all subprojects.
  - Add smoke tests for key routes and deployment verification.
- **Accessibility Audits:**
  - Run accessibility linting and manual keyboard navigation tests on all major UI flows.
- **Runtime Dependency Review:**
  - Audit all CDN and runtime dependencies; add fallbacks or migrate to build-time integration where needed.
- **Ongoing Rule Enforcement:**
  - Integrate ruleset checks into PR review templates and CI pipelines.
- **Documentation Expansion:**
  - Add onboarding and workflow guides for new contributors.
