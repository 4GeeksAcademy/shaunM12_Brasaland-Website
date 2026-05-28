# Development Rules

## Rule: Centralized Validation Logic

### Scope: Always Active
This rule applies to all files and modules in the codebase.

### Description:
- All validation logic must be centralized in reusable functions or modules.
- Validation functions should be stored in a dedicated `utils/validations.ts` file or similar.
- Avoid duplicating validation logic across components or modules.
- Ensure validation functions are unit-tested and cover edge cases.

### Benefits:
- Reduces code duplication.
- Simplifies maintenance and updates to validation rules.
- Improves consistency and reliability of validation logic.

### Example:
```typescript
// utils/validations.ts
export function isValidEmail(email: string): boolean {
  const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return EMAIL_REGEX.test(email.trim());
}

// Usage in a React component
import { isValidEmail } from "@/utils/validations";

if (!isValidEmail(userInput.email)) {
  console.error("Invalid email address");
}
```