---
name: make-it-so
description: 4. Make it so (implement all tasks)
---

### 4. Make it so (implement all tasks)

Implement all the remaining tasks from the spec, one phase at a time. The main agent NEVER implements tasks itself — it always delegates the work to one or more subagents, oversees their spawning, integrates their results, and handles phase-level bookkeeping (review, changelog, specs overview).

**Constraints:**

**Phase Retrieval (main agent):**
- The main agent MUST use the rune skill to retrieve the next phase to work on
- Use `rune next --phase --format json` to get the next incomplete phase
- If `rune next` reports that all tasks are complete, stop the loop and report completion to the user

**Stream Detection (main agent):**
- Once a phase is selected, the main agent MUST run `rune streams --available --json` to detect ready work streams
- 2 or more ready streams → **Parallel Delegation** (worktree per stream)
- 1 ready stream, or the phase has no streams defined → **Single-Subagent Delegation** (no worktree, in place)
- Whichever path is taken, the main agent MUST delegate. It MUST NOT implement tasks itself.

**Parallel Delegation (multiple streams):**

Subagents work in isolated git worktrees so their parallel commits don't race on the shared index or on `tasks.md`.

For each ready stream the main agent MUST:
1. Create a worktree branched from the current working branch:
   - `git worktree add .claude/worktrees/<phase>-stream-<N> -b stream/<phase>-<N>`
2. Spawn one subagent per worktree, all in a single message so they run in parallel (Agent tool, `general-purpose` subagent unless a more specific type fits)

Each subagent prompt MUST include:
- The stream number it owns
- The absolute path to its worktree (it MUST `cd` there before doing anything)
- The path to the tasks file inside the worktree
- The list of `front_matter_references` to read before implementing
- These instructions:
  - Use `rune next --phase --stream N --format json` to retrieve all tasks for the stream
  - Read all referenced files before implementing
  - Implement tasks in dependency order. Use tools/skills as needed (the library-documentation tools for library docs, efficiency-optimizer for verification, etc.)
  - Mark each task complete with `rune complete <task-id>` as it finishes
  - Run all formatting and test commands for the project before committing
  - Stage changes (including any reformatting and the modified `tasks.md`) and commit using the **Subagent Commit Conventions** below
  - Stop when all tasks in the stream are complete, when blocked by tasks in other streams, or on unrecoverable failure
  - Report back: branch name, list of completed task IDs, list of blocking task IDs (if any), and final status (`done` | `blocked` | `failed`)

**Main Agent Oversight (parallel mode):**
- Wait for all spawned subagents to return
- Track which streams reported `done` / `blocked` / `failed`
- After any return, re-run `rune streams --available --json`. If newly unblocked streams appear (because another stream's completion satisfied their deps), spawn fresh subagents for them in new worktrees — same parallel pattern as above
- If every remaining stream reports `blocked` and no new work surfaces, report a circular dependency to the user and stop
- If a subagent reports `failed`, surface the failure to the user and stop the phase rather than masking it

**Integration (main agent, after all parallel subagents have returned `done`):**
1. From the main working branch, merge each completed stream branch in turn:
   - `git merge --no-ff stream/<phase>-<N> -m "[merge]: phase <P> stream <N>"`
2. Conflicts on `tasks.md` are expected (each stream marked different tasks complete). Resolve by accepting both sides' completions
3. After all stream branches are merged, remove their worktrees and delete the branches:
   - `git worktree remove .claude/worktrees/<phase>-stream-<N>`
   - `git branch -d stream/<phase>-<N>`

**Single-Subagent Delegation (single stream or no streams):**

No worktree is needed — there is no parallel commit race when only one subagent is working.

The main agent MUST spawn one subagent (Agent tool, `general-purpose` unless a more specific type fits) with a prompt containing:
- The phase number
- The stream number if the phase has exactly one ready stream (otherwise note that streams are not defined for this phase)
- The path to the tasks file
- The list of `front_matter_references` to read before implementing
- These instructions:
  - Use `rune next --phase --stream N --format json` if a single stream is in play, otherwise `rune next --phase --format json`, to retrieve all tasks for the phase
  - Read all referenced files before implementing
  - Implement all tasks (including subtasks) in the order specified, using tools/skills as needed
  - Mark each task complete with `rune complete <task-id>` as it finishes
  - Run all formatting and test commands for the project before committing
  - Stage changes (including any reformatting and the modified `tasks.md`) and commit on the current working branch using the **Subagent Commit Conventions** below
  - Report back: list of completed task IDs and final status (`done` | `failed`)

The main agent waits for the subagent to return and surfaces any failure to the user before continuing.

**Review (main agent):**
- Once the phase is fully integrated (parallel mode) or the single subagent has returned `done` (single-subagent mode), use the design-critic skill over the resulting state and verify it's correct. Issues detected should be fixed (delegate the fix as a follow-up subagent if it involves code, or update the decision log directly)

**Phase Changelog & Specs Overview (main agent):**
- After review, write a single phase-level changelog entry summarising the work done in this phase (subagent commits never touch the changelog — see Subagent Commit Conventions). Read `CHANGELOG.md` (create if missing), prepend the entry if not already present, and commit it as `[doc]: changelog for phase <P>` (or with a ticket prefix if applicable)
- Then check if all tasks in the spec are complete: `rune list specs/{feature_name}/tasks.md --format json` and verify no incomplete tasks remain
- If all tasks complete AND `specs/OVERVIEW.md` exists:
  - Update the spec's status from `Planned` or `In Progress` to `Done`
  - If new files were created in the spec directory during implementation (e.g., `implementation.md`), add them to the spec's detail section file list
- If tasks remain AND `specs/OVERVIEW.md` exists AND the spec's status is `Planned`:
  - Update the spec's status from `Planned` to `In Progress`
- Commit any overview/decision-log updates

**Compact and Continue (main agent):**
- If incomplete tasks remain in the spec, continue with the next phase (the harness compacts context when needed)
- If all tasks are complete, report completion to the user and stop

---

**Subagent Commit Conventions** (used by ALL subagents — parallel stream subagents and single-subagent mode; the main agent's phase changelog commit is a separate single-file commit and follows its own format):

1. Run all formatting and test commands.
2. Use the command line to get an overview of the staged git changes. If no changes are staged, stage all files. If running the formatting resulted in unstaged changes to files, stage these as well. DO NOT revert code changes unless specifically asked to do so.
3. Subagents MUST NOT touch `CHANGELOG.md`. The main agent writes the per-phase changelog entry after the subagents return (and, in parallel mode, after their branches are merged).
4. Verify the current branch with git. Parallel stream subagents are on `stream/<phase>-<N>`; single-subagent mode is on the user's working branch. The ticket prefix below should be derived from the **base** working branch (the branch the worktree was created from, or — in single-subagent mode — the current branch directly).
5. Extract any ticket numbers from the base branch:
    a. JIRA-style ticket: `ABC-123` (3–5 letters/digits, `-`, 1–5 digits) at the start of the branch name, possibly after `feature/` or `hotfix/`.
    b. A pure number, which would likely reflect a GitHub Issue.
6. If a ticket number was found, use it as the commit message prefix; otherwise use `[feat]` / `[bug]` / `[doc]` based on the branch and the nature of the changes.
7. Write a multi-line commit message prefixed with `<prefix>:`. Do NOT include any co-authored-by lines.
8. Commit.
