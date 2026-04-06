# QA Checklist - Milestone 1 (Brasaland)

## Submission Info
- Project URL:
- Date:
- Reviewer:

## 1. Semantic HTML and Structure
- [ ] `index.html` uses semantic tags: `header`, `nav`, `main`, `section`, `article`, `footer`.
- [ ] Section order matches context: Header, Hero, Our Story, What Makes Us Unique, Our Locations, Brasa Points, Contact, Footer.
- [ ] Hero includes exact required headline, subheadline, and CTA to `application.html`.
- [ ] All images include descriptive `alt` text.
- [ ] Form uses correct `label` + `for` and matching input `id`.
- [ ] Grouped controls use `fieldset` and `legend`.

## 2. Accessibility (WCAG 2.1 AA)
- [ ] Full keyboard navigation works (Tab/Shift+Tab, Enter, Space).
- [ ] Focus indicators are visible on links, buttons, and form fields.
- [ ] Navigation has meaningful `aria-label`.
- [ ] Error and success messages are announced (`role="alert"` and/or `aria-live`).
- [ ] Color contrast is readable for text and controls.
- [ ] Language switch updates page language correctly.

## 3. SEO and GEO
- [ ] Unique title and meta description on both pages.
- [ ] Canonical URL present and correct.
- [ ] Open Graph/Twitter metadata present on landing page.
- [ ] Crawlable internal links exist between landing and form pages.
- [ ] Content includes clear entity facts (founded year, locations, countries, contacts).

## 4. Schema.org
- [ ] JSON-LD present in landing page.
- [ ] `@type` is `Restaurant` with required fields.
- [ ] Contact and social links match context.
- [ ] `availableLanguage` reflects delivered languages.
- [ ] Schema validates in Rich Results / Schema Markup Validator.

## 5. Responsive Design (Tailwind)
- [ ] Mobile-first layout is usable at 320px width.
- [ ] Tablet behavior validated at `sm` and `md` breakpoints.
- [ ] Desktop behavior validated at `lg` breakpoint and above.
- [ ] No horizontal scrolling on key sections.
- [ ] Form controls remain readable and tappable on small screens.

## 6. Form Fields and Validation
- [ ] All required fields from `CONTEXT.md` are present.
- [ ] Input types are correct (`email`, `tel`, `date`, `select`, `checkbox`).
- [ ] Real-time validation runs on input/blur/change.
- [ ] Required English error messages match context text.
- [ ] Submit blocked when invalid fields exist.
- [ ] Success message shown when valid (simulated submit).
- [ ] Clear button resets values, dependent selects, errors, and status message.

## 7. Dependent Logic
- [ ] Country -> City options update dynamically.
- [ ] Country + City -> Favorite location options update dynamically.
- [ ] Colombia city list: Medellín, Bogotá, Cali.
- [ ] United States city list: Miami, Orlando.
- [ ] Favorite location list includes all 14 context locations.

## 8. Context Adherence
- [ ] Company description reflects Brasaland (grilled food chain, 2008, Colombia + US).
- [ ] Brasa Points value proposition and rules are present.
- [ ] Visible restriction message is present: online ordering coming soon.
- [ ] Tone reflects an established company going digital.

## 9. Performance Evidence (PageSpeed)
- [ ] PageSpeed Insights run on public URL.
- [ ] Mobile performance score >= 80 (target > 90).
- [ ] Main opportunities reviewed (images, blocking scripts, layout shifts).
- [ ] Final score documented.

### Results Log
- Landing score:
- Form score:
- Key fixes applied:
- Remaining risks:
