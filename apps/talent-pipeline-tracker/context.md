# CONTEXT — Brasaland · Milestone 3: Talent Pipeline Tracker

> **Repository path:** `03-talent-pipeline-tracker/CONTEXT-brasaland.en.md`

---

## Your company

You are part of the **Brasaland Digital** team, the internal technology unit of Brasaland, a grilled food restaurant chain with 14 locations in Colombia and Florida. Your job is to build the tools that operational teams will use every day.

---

## The assignment

Ashley Turner, People Manager, has sent the following email with Nicolás Park, CTO, on copy:

> **To:** Nicolás Park (CTO)
> **CC:** Brasaland Digital Team
> **Subject:** URGENT — We need the candidate management tool this week
>
> Nicolás,
>
> I'm writing to you directly because we can no longer manage the **Executive Assistant** selection process in a Google Sheet. We have over a hundred applications and three people editing the same file at the same time. This morning we lost the data of two candidates due to a save conflict.
>
> I understand the backend is ready. I need someone from the team to build the frontend this week — this cannot wait any longer.
>
> What I need the tool to do:
>
> - Show all candidates at a glance: name, position, status, and stage.
> - Filter by status and stage, and search by name or email without reloading the page.
> - Open a candidate's detail and update their status or stage from there.
> - Add internal notes after each call or interview, and delete them when they're no longer needed.
> - Register candidates who apply through other channels and correct data when it comes in wrong.
>
> Thank you for escalating this.
>
> Ashley

---

## Context of the active search

| Field    | Value                                                                              |
| -------- | ---------------------------------------------------------------------------------- |
| Position | Executive Assistant                                                                |
| Company  | Brasaland                                                                          |
| Location | Corporate headquarters, Medellín                                                   |
| Profile  | Executive support experience, calendar and travel management, professional English |

---

## API and data

The mock API is centrally deployed and shared across all company contexts in the course. Fields, values, and structure are as defined in the backend technical specification. No adaptation is required.

### `status` values

| API value     | UI label    |
| ------------- | ----------- |
| `received`    | Received    |
| `in_progress` | In progress |
| `selected`    | Selected    |
| `discarded`   | Discarded   |

### `stage` values

| API value             | UI label            |
| --------------------- | ------------------- |
| `pending`             | Pending review      |
| `review`              | Under review        |
| `personal_interview`  | Personal interview  |
| `technical_interview` | Technical interview |
| `offer_presented`     | Offer presented     |

> Raw API values (`in_progress`, `personal_interview`, etc.) must never be visible in the interface. Always use the labels from this table.

---

## Specific acceptance criteria

- Status and stage fields show human-readable labels, never raw API values.
- Notes are visible only within the candidate detail view.
- The registration form includes all fields required by the API.

---

## Frontend implementation requirements

Use this section as the source of truth for Milestone 3 implementation.

### Views and routing

- Build a candidate list page at `/` that displays all candidates from `GET /records`.
- Build a candidate detail page at `/candidates/[id]` that fetches full candidate data from `GET /records/{id}`.
- Navigation between list and detail must use Next.js App Router transitions only (no full page reloads).

### Candidate list

- Display each candidate's full name, applied position, current status, and current stage.
- Implement filtering by status and stage through query parameters using `useSearchParams`.
- Implement a search input that filters by name or email without reloading the page.
- Show UI states for list fetching: loading, success, and error.

### Candidate detail

- Display all available candidate fields:
	- Full name
	- Email
	- Phone
	- Position
	- LinkedIn URL
	- CV URL
	- Years of experience
	- Status
	- Stage
	- Application date
- Include a control to update status via `PATCH /records/{id}`.
- Include a control to update stage via `PATCH /records/{id}`.
- Display notes from `GET /records/{id}/notes`.
- Allow adding a note via `POST /records/{id}/notes`.
- Allow deleting a note via `DELETE /records/{id}/notes/{note_id}`.

### Candidate management

- Include a form to register a new candidate via `POST /records`.
- Include a form to edit candidate data via `PUT /records/{id}`.
- Validate required fields in both forms before submission.
- Show success and error feedback after each submission.

### State and async handling

- Handle all API calls using `async/await`.
- Every data-fetching operation must expose at least three UI states: loading, success, and error.
- After `PATCH`, `PUT`, and `POST` requests, update the UI immediately without full page reload.

### Code structure and technical constraints

- Organize the app with clear folders such as `components`, `hooks` (if used), `types`, and `lib` or `services`.
- Define TypeScript types for all data structures received from the API.
- Do not use prop drilling; use composition or shared state patterns compatible with project constraints.
- Required stack: Next.js (App Router), React, TypeScript, Tailwind CSS.
- All UI styling must be implemented with Tailwind utility classes; do not use standard CSS files, CSS modules, or inline style objects for component styling.
- Do not use Redux, Zustand, or Jotai.

### UX and terminology

- All visible labels and wording must reflect the Brasaland context in this document.
- Use human-readable status and stage labels from the mapping tables above, never raw API values in UI.

---

_Internal document — 4Geeks Academy · AI Engineering Track_
_For exclusive use in programme project generation_

This file provides context and documentation for the talent-pipeline-tracker application. Add relevant project details, environment notes, and usage instructions here as needed.
