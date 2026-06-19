# Agent Operating Protocol

## Required session startup reads

At the start of every coding session, the agent must read these files before proposing changes:

1. `memory-bank/projectbrief.md`
2. `memory-bank/techContext.md`
3. `memory-bank/progress.md`
4. `CONTEXT.md`

Do not read files under `memory-bank/historical-reference/` as part of startup. Those documents capture point-in-time context that may have since changed and can conflict with current work. The developer will explicitly tell the agent which historical-reference file (if any) is relevant to the task at hand.

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

All implementation and documentation decisions must stay aligned with the current Brasaland data/process constraints captured in `CONTEXT.md` and the `memory-bank/` files listed under "Required session startup reads". Historical-reference documents are not authoritative by default — the agent should consult a `memory-bank/historical-reference/` file only when the developer explicitly designates it for the current task, and current sources take precedence on any conflict.
