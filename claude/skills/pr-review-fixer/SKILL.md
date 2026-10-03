---
name: pr-review-fixer
description: Fetch unresolved change-request review threads (both diff-anchored and CR-level), validate issues, and fix them. Also checks CI status and fixes failing tests, lint errors, and build issues. Works on both GitHub (gh) and GitLab (glab) — it detects the forge from the git remote. Use when reviewing and addressing PR/MR feedback. Filters out resolved threads, keeps only the last Claude review comment per thread (matching the `<!-- claude-local-review -->` sentinel from the local-review agent), validates issues, posts a review report as a CR comment, then fixes validated issues.
# model: inherit
# allowed-tools: Bash,Read,Write,Edit,Grep,Glob
---

# PR Review Fixer

Fetch unresolved review threads on a change request (CR), validate each issue, create
a fix plan, implement fixes, and verify CI checks pass (tests, lint, build).

This skill is **forge-aware**: the repo may be on GitHub (`gh`) or GitLab (`glab`).
It does not hard-code either CLI — it follows the shared operation contract and the
adapter for whichever forge the repo uses.

## Forge setup (do this first)

1. Read `~/.claude/forge-adapters/CONTRACT.md` — it defines the neutral terms (CR,
   thread, note, `<id>`) and the operations this workflow calls.
2. Run **`PREFLIGHT`** to determine `FORGE` and confirm the CLI is authenticated. If
   not, stop and tell the user how to authenticate.
3. Read the matching adapter `~/.claude/forge-adapters/<FORGE>.md`. Every concrete
   command below comes from that adapter's `## OPERATION` section — do not improvise
   `gh`/`glab` commands.

## Workflow

### 1. Fetch CR and Threads

```text
CR_VIEW            → keep `id` and `source_branch`
THREADS_FETCH <id> → normalised array, one element per thread (see CONTRACT.md):
                     {thread_id, scope, resolved, resolvable, author, path, line, body}
```

Because `THREADS_FETCH` returns the same shape on both forges, the rest of this
workflow is identical regardless of forge. Save the array to
`/tmp/cr-review-${id}/threads.json`.

### 2. Filter Threads

A thread is a "Claude review" if its `body` contains the sentinel
`<!-- claude-local-review -->` (emitted by the `local-review` agent). On neither
forge is there a bot author — notes post under the invoking user — so the sentinel
is the only reliable signal.

From the normalised array:
1. **Exclude resolved**: drop elements where `resolved == true`.
2. **Claude review dedup**: when several elements are Claude reviews, keep only the
   most recent (the adapter already collapsed each thread to its last note; here you
   dedup *across* threads if the same review was reposted).
3. **Bucket by `scope`**: `diff` (has `path`/`line`) vs `cr-level`.
4. **Keep only actionable items**: requested changes, questions, concrete
   suggestions. Skip pure acknowledgements, thanks, or informational notes.

### 3. Determine Working Location

Nothing from this skill is written into the repo. Review reports go out as CR
comments.

**Working directory**: `/tmp/cr-review-${id}/`. Create it before step 1. Never write
under the repo (no `.claude/reviews/`, no report files beside the code).

**Iteration tracking**: count prior overview comments via `CR_NOTES_LIST` whose body
contains the sentinel `<!-- pr-review-overview -->`. That count + 1 is the current
iteration N. The sentinel is required because notes post under your own account, so
an author check cannot find prior iterations.

```text
N = (CR_NOTES_LIST <id> | count bodies containing "<!-- pr-review-overview -->") + 1
```

### 4. Validate Issues

**Diff-anchored threads (`scope: "diff"`):**
1. Read the referenced code at `path:line`.
2. Evaluate: is the issue still present? Is the suggestion correct? Does it align
   with project conventions (consult the repo's `CLAUDE.md`)?
3. Mark valid or invalid with a brief rationale.

**CR-level threads (`scope: "cr-level"`):**
1. Parse the body for actionable items.
2. Check the feedback still applies to the current CR state.
3. Evaluate reasonableness and alignment with project goals.
4. Mark valid or invalid; skip pure acknowledgements.

### 5. Prepare Review Overview

Assemble in-context (not on disk). Step 11 posts the final version — including CI
status from step 9 — as a CR comment. Structure:

```markdown
# CR Review Overview - Iteration [N]

**CR**: [id] | **Branch**: [name] | **Date**: [YYYY-MM-DD]

## Valid Issues

### Diff-Anchored Issues
#### Issue 1: [title]
- **File**: `path:line`
- **Reviewer**: @user
- **Comment**: [quoted]
- **Validation**: [rationale]

### CR-Level Issues
#### Issue 2: [title]
- **Reviewer**: @user
- **Comment**: [quoted]
- **Validation**: [rationale]

## Invalid/Skipped Issues
### Issue A: [title]
- **Location**: `path:line` or CR-level
- **Reason**: [why invalid]
```

### 6. Create Task List

Create one task per validated issue with TaskCreate (`Fix: <issue>`).

### 7. Fix Issues

Work through the tasks, marking each in progress and complete with TaskUpdate; implement each fix following the project's existing patterns.

### 8. Check CI Status

```text
CI_STATUS <id> → normalised array of {name, state}
```

If the array is **empty**, the CR has no CI configured — skip steps 8–9 entirely and
note "no CI to verify" in the overview. Otherwise handle every element whose `state`
is `failed`.

### 9. Fix CI Issues

For each failed check:

1. **Get logs**: `CI_JOB_LOG <id> <name>`.
2. **Reproduce locally** using the project's own commands. Prefer a `Makefile`
   target if present (`make test`, `make lint`), otherwise the command documented in
   the repo's `CLAUDE.md`/README (e.g. `pytest`, `npm test`, `go test ./...`, `ruff`).
3. **Parse output**; persist any captured logs to `${WORK_DIR}/ci-output.txt`, never
   inside the repo.
4. **Fix**:
   - Test failures: decide whether the test expectation is wrong or the code has a
     bug — never edit a test purely to make it pass.
   - Lint/format: apply the project's auto-fix, then manual fixes.
   - Type/build: fix the reported mismatches.
5. **Re-run locally** to verify.
6. **Add to the task list** if not already tracked.

### 10. Reply in Threads and Resolve

For **every actionable thread that was processed** (validated-and-fixed *or*
marked invalid), post a short reply inside that thread — not a new CR-level
note — stating the outcome:

- **Fixed**: one or two sentences naming the change (file, what was done).
- **Invalid/skipped**: the one-line rationale from step 4.

Stage each reply body in `${WORK_DIR}/reply-<n>.md`, then:

```text
THREAD_REPLY <id> <thread_id> ${WORK_DIR}/reply-<n>.md
```

Then resolve with `THREAD_RESOLVE <thread_id>`:

- **Resolve** threads whose issue was fixed.
- **Resolve** Claude-review threads (body carries the
  `<!-- claude-local-review -->` sentinel) once every item in them is addressed —
  fixed or invalidated with rationale. They are machine-generated; nobody else
  will close them.
- **Leave unresolved** human-authored threads whose finding was disputed or
  skipped — the human gets the in-thread reply and decides whether to close.

Forge specifics (see adapters): on GitLab, `THREAD_REPLY` works on an individual
(non-thread) note too — the reply converts it into a thread, after which
`THREAD_RESOLVE` works even though `THREADS_FETCH` reported it
`resolvable: false`. So reply first, then resolve. On GitHub, only diff-anchored
review threads accept in-thread replies; for CR-level comments the reply rides in
the step 11 overview instead (quote the original), and resolution is skipped.

### 11. Post Review Report as CR Comment

Compose the final overview (structure from step 5, plus CI status from step 9), stage
it in `${WORK_DIR}/overview-${N}.md`, then:

```text
CR_COMMENT <id> ${WORK_DIR}/overview-${N}.md
```

The body MUST begin with the `<!-- pr-review-overview -->` sentinel on its own line —
that is what the iteration counter in step 3 matches on. Without it, N will not
increment between rounds.

### 12. Commit, Push, and Verify

After all fixes:

1. Run the full test suite locally (project command / Makefile target).
2. Run the linter.
3. Commit the code changes.
4. Push to remote (`git push`).
5. If CI exists, re-run `CI_STATUS` to confirm checks pass; otherwise note there is
   no CI to wait on.

Nothing from `/tmp/cr-review-${id}/` belongs in the commit — those paths are outside
the repo and git ignores them automatically.

## Key Behaviors

- **Forge-neutral**: never call `gh`/`glab` directly; go through the contract
  operations so the same workflow runs on GitHub and GitLab.
- **Auto-fix**: fix all validated issues without pausing for approval.
- **Convention adherence**: follow the project's existing patterns and tooling.
- **Deduplication**: consolidate multiple notes on the same issue into one task.
- **CI-aware but CI-optional**: handle checks when they exist, no-op when `CI_STATUS`
  is empty.
- **Local reproduction**: run tests/linters locally before pushing fixes.
- **Reports as comments**: post review reports as CR comments, never to disk under
  the repo.
- **Replies in-thread**: outcomes for individual findings go into the originating
  thread (`THREAD_REPLY`) and handled threads get resolved, so the CR's open-thread
  count reflects what actually still needs attention.
- **No in-repo working files**: captured output lives under
  `/tmp/cr-review-${id}/`, not in the repo.
