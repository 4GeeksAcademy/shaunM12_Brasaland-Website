# Accessibility Baseline Preservation

**Scope:** All UI changes, feature updates, and localization affecting accessibility.

**Rationale:** Prevents regression of keyboard and assistive-technology usability.

**Guardrails:**
- Preserve skip links, semantic landmarks, and descriptive labels.
- Keep keyboard focus behavior and navigation operable.
- Maintain accessibility attributes when localization updates labels.

**Detection Signals:**
- Removed skip-link or landmark tags.
- Missing `aria-label` and heading associations.
- Non-focusable interactive controls.

**Verification:**
- Perform keyboard-only smoke test.
- Run accessibility lint/check tooling where configured.
- Validate localized labels still populate ARIA attributes.
