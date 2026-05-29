# Environment-First API Base URL

**Scope:** All API client configuration and environment variable usage (e.g., `apps/talent-pipeline-tracker/lib/api.ts`).

**Rationale:** Prevents accidental calls to unintended APIs by enforcing explicit environment configuration.

**Guardrails:**
- Require explicit API base URL in non-development environments.
- If a fallback is used for development, document and label it clearly in code comments.
- Keep API base URL configuration centralized in one place per app.

**How to Apply:**
1. In production and staging, always set `NEXT_PUBLIC_TRACKER_API_BASE_URL` (or equivalent) in environment variables.
2. In code, only allow fallback URLs when `NODE_ENV` is `development`.
3. Add a comment above any fallback explaining it is for local/dev use only.
4. Add a test to ensure the app throws or warns if the env var is missing in production.

**Example:**
- Bad:
	```js
	const API_URL = process.env.NEXT_PUBLIC_TRACKER_API_BASE_URL ?? "https://playground.4geeks.com/tracker/api/v1";
	```
- Good:
	```js
	const API_URL = process.env.NEXT_PUBLIC_TRACKER_API_BASE_URL;
	if (!API_URL) {
		if (process.env.NODE_ENV === "development") {
			// Dev fallback for local testing only
			API_URL = "https://playground.4geeks.com/tracker/api/v1";
		} else {
			throw new Error("API base URL must be set in production!");
		}
	}
	```

**Detection Signals:**
- Hardcoded external URL used as unconditional fallback.
- Missing env var checks in startup/runtime code paths.
- Different environments silently sharing one default endpoint.

**Verification:**
- Validate environment requirements during build/start for non-dev modes.
- Add tests for API client behavior with and without the environment variable set.
