# Centralized Validation Contract

**Scope:** All validation logic and user-facing error messages.

**Rationale:** Prevents validation drift, duplicated logic, and inconsistent error messaging.

**Guardrails:**
- Keep validation logic in shared utility modules.
- Reuse shared validators in UI and business logic layers.
- Do not duplicate regex or business-rule checks in multiple components.

**Detection Signals:**
- Similar validation conditions repeated across files.
- Error message variations for the same failed rule.
- Form-level checks diverging from shared validation module behavior.

**Verification:**
- Run validator unit tests including edge cases.
- Confirm form flows use shared validators and expected message text.
