# Agent Operating Protocol

## Required session startup reads

At the start of every coding session, the agent must read these files before proposing changes:

1. `memory-bank/projectbrief.md`
2. `memory-bank/techContext.md`
3. `memory-bank/progress.md`
4. `memory-bank/historical-reference/context-4-milestone-4.md`
5. `memory-bank/historical-reference/context-6-supplier-directory.md`
6. `memory-bank/historical-reference/context-7-authentication-and-route-restriction.md`
7. `CONTEXT.md`

## Mandatory pre-commit workflow

Before any commit is created, complete these steps in order:

1. Re-read scope and acceptance criteria from the active milestone context file.
2. Run static checks and tests for affected apps/packages.
3. Confirm user-facing flows changed in this task still work end-to-end.
4. Update memory-bank progress/historical notes to reflect what changed.
5. Prepare a concise change summary with risk notes and rollback hints.

## Protected paths (require explicit developer confirmation)

The agent must not modify the following paths unless the developer explicitly confirms:

- `memory-bank/historical-reference/**`
- `data/raw/**`
- `workflows/**`
- `vercel.json`
- `.agents/**`

## Alignment requirement

All implementation and documentation decisions must stay aligned with Brasaland data/process constraints captured in milestone context references, including `context-4-milestone-4.md`, `context-6-supplier-directory.md`, `context-7-authentication-and-route-restriction.md`, and memory-bank historical records.
