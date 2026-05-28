# Runtime Dependency Stability

**Scope:** All runtime-loaded dependencies, especially CDN scripts and external assets (e.g., Tailwind via CDN in `index.html`).

**Rationale:** Reduces availability and performance risk from runtime-loaded dependencies.

**Guardrails:**
- Review all runtime dependencies that affect critical UX (e.g., layout, navigation, forms) for fallback strategy.
- Prefer build-time integration (npm, bundler) for core styling/logic dependencies (e.g., Tailwind, React).
- If a runtime CDN dependency is retained, document the rationale and provide a fallback or warning for users.

**How to Apply:**
1. For each `<script src="...">` or external asset, ask: "If this fails, does the app still work?"
2. For critical dependencies (e.g., Tailwind for layout), prefer installing via npm and bundling at build time.
3. If using a CDN for dev/demo, add a `<noscript>` or warning for users if the CDN fails.
4. Document in code comments why a CDN is used and what the fallback is.

**Example:**
- Bad:
	```html
	<script src="https://cdn.tailwindcss.com"></script>
	<!-- No fallback, no explanation -->
	```
- Good:
	```html
	<!-- Tailwind via CDN for demo only. For production, use npm build. -->
	<script src="https://cdn.tailwindcss.com" onerror="document.body.innerHTML='Please reload or contact support.'"></script>
	```

**Detection Signals:**
- Critical UX relies on a single external runtime script.
- No fallback behavior or offline tolerance for essential assets.
- Repeated outages tied to third-party script loading.

**Verification:**
- Test page behavior with constrained network.
- Validate app still renders a usable baseline when runtime dependency is delayed.
