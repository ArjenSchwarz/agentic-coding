---
name: pr-pilot
description: Push a branch, open a change request, iterate on reviews until clean, then squash-merge. Runs /pr-review-fixer in a loop until no blockers/critical/major issues remain, rebases onto latest origin/main, and squash-merges. Works on both GitHub (gh) and GitLab (glab) — it detects the forge from the git remote. Works with or without Transit tickets. Use when you want to shepherd a PR/MR from push to merge, e.g. "push and merge this", "get this merged", "review-fix-merge loop".
# model: inherit
# allowed-tools: Read,Write,Edit,Bash,Grep,Glob,Task
---

# PR Pilot

Push a branch, open a change request (CR), loop through reviews until clean, then
squash-merge.

This skill is **forge-aware**: the repo may be on GitHub (`gh`) or GitLab (`glab`).
It does not hard-code either CLI — it follows the shared operation contract and the
adapter for whichever forge the repo uses. Local reviews can run in independent
native subagents; a Claude installation or subscription is not required when that
route works. `/pr-review-fixer` handles the resulting findings on either forge.

## Forge setup (do this first)

1. Read `~/.claude/forge-adapters/CONTRACT.md` for the neutral terms and operations.
2. Run **`PREFLIGHT`** to determine `FORGE` and confirm the CLI is authenticated. If
   not, stop and tell the user how to authenticate.
3. Read the matching adapter `~/.claude/forge-adapters/<FORGE>.md`. Every concrete
   command comes from there — do not improvise `gh`/`glab` commands.

## Input

Works in the current working directory (or a specified worktree path). It needs:

- A branch with committed changes ready to push
- Optionally a Transit ticket reference (`T-{id}`) for status tracking
- Optionally an existing CR id (skips push and CR creation)

If invoked with arguments, parse them for:
- `T-{number}` — Transit ticket to track
- a CR id (`#123` / `!1` / bare number) — existing CR to work with
- A path — working directory override

## Workflow

### 1. Push and Open the CR

If no existing CR id was provided, run **`CR_CREATE`** with `target` = `main` (pass a
`title` that includes the `T-{number}` prefix if the branch name carries one). Keep
the returned id as `<id>`.

If an existing CR id was provided, fetch its details with **`CR_VIEW`** instead.

### 1.5 Select a Reviewer

Use an independent reviewer, separate from the agent implementing fixes:

1. **Native subagent (preferred):** start a fresh reviewer using the host's agent
   tools. In Claude Code, the registered `local-review` agent can fill this role;
   in Codex or another host, spawn a fresh review-only subagent with the brief in
   [references/review.md](references/review.md). Supply the repository/worktree,
   CR id, forge adapter paths, and the head SHA from `CR_VIEW`. Do not seed it with
   the implementer's conclusions or use an agent that authored the changes.
2. **Claude fallback:** if independent native subagents are unavailable, use the
   existing `local-review` agent through an available, authenticated Claude runtime,
   with the same review brief. Do not require Claude login before trying a working
   native route. Honour an explicit user choice of reviewer.
3. If neither route can complete, report the missing capability/authentication and
   stop before merge. The implementer's own reread cannot satisfy this gate.

Read the review brief before dispatch. Both routes must inspect the full current
CR diff and project instructions, return a verdict with grounded findings, and post
one review note via `CR_COMMENT`. A native reviewer may return the complete body to
its parent to post if it lacks posting tools; preserve its verdict and findings.
Use the compatibility sentinel `<!-- claude-local-review -->` even for native
reviews so `/pr-review-fixer` recognises them; state the actual reviewer/runtime in
visible text rather than claiming every review is Claude.

Run local review up front unless `AUTO_REVIEWER_DETECT == 1`. Detection only avoids
an up-front duplicate: a successful automated job alone never satisfies review.

### 2. Review Loop

#### 2.1 Obtain and Verify Review Evidence

Before starting the round, fetch `CR_VIEW` for `HEAD_SHA` and `CR_NOTES_LIST` for the
baseline note ids. Run the selected local reviewer if no automated reviewer is
expected. Wait up to 10 minutes for checks/review input when CI exists; when there
is no CI, proceed as soon as a completed review note is verified.

Accept a round only when a **new note id**, absent from the baseline, contains a
completed independent review of `HEAD_SHA`: an explicit reviewed SHA, verdict, and
findings (or an explicit no-findings result). For local reviews, verify the sentinel
and actual reviewer identity too. Automated reviews must also demonstrably cover
that SHA and the review scope in the brief. Author matches, note counts, job success,
and fixer overview comments alone are insufficient evidence.

If no qualifying review landed, run the selected local reviewer as a fallback at
most once per round, regardless of automated-review detection, then re-fetch notes
and verify the same evidence. If the selected backend failed (including Claude auth
failure), use an available independent alternative from step 1.5 for this fallback;
do not treat failure as a clean review. If posting had an uncertain outcome, inspect
notes before retrying to avoid duplicates. If evidence is still absent, incomplete,
or failed, stop and report the blocker. Do not continue to the fixer or merge.

Re-fetch `CR_VIEW` after the review: if the head changed during review, invalidate
the round and review the new head within the loop cap. Reviews of an earlier head
cannot authorise the current one.

#### 2.2 Run PR Review Fixer

Run the `/pr-review-fixer` skill to fetch unresolved threads and any CI failures,
validate them, and fix issues found.

After it completes, evaluate:
- **CLEAN**: verified review evidence for the current head, no blockers, critical,
  or major issues, and no failed checks. Minor and nitpick items are acceptable.
- **HAS_ISSUES**: fixes or CI repairs were committed and pushed. Any head change
  requires another independent review, regardless of finding severity.

#### 2.3 Evaluate and Repeat

- **HAS_ISSUES**: re-run from step 2.1 (wait only if CI exists).
- **CLEAN**: proceed to merge.

Cap the loop at 5 iterations. If still not clean after 5 rounds, inform the user and
stop. Do not merge. If a Transit ticket is tracked, add a comment: "Automated review
loop did not converge after 5 iterations — manual review needed."

### 3. Rebase and Merge

#### 3.1 Rebase onto Latest Main

```bash
git fetch origin main
git rebase origin/main
```

Resolve any conflicts, then `git rebase --continue`. Run the project's tests and
linter (Makefile target if present, else the project's documented commands) to
verify the rebase is clean.

#### 3.2 Push Rebased Branch

```bash
git push --force-with-lease
```

#### 3.3 Review the Rebased Head and Wait

Run step 2.1 again with a fresh baseline and the rebased `HEAD_SHA`, using the same
reviewer selection, evidence checks, and bounded fallback. Even if the rebase was a
no-op, obtain a fresh review for this phase. Then run `/pr-review-fixer` for new
findings and CI failures.

- **CLEAN**: proceed to the final merge gate.
- **HAS_ISSUES** or any head change: fix, push, and repeat the review/fixer cycle
  (up to 3 iterations). If still not clean or review is blocked, inform the user
  and stop without merging.

#### 3.4 Squash and Merge

Immediately before merge, re-fetch `CR_VIEW` and `CI_STATUS`. The head must still
match the verified review and all blockers/critical/major findings must be addressed.
Apply the existing `CI_STATUS` contract: `[]` means no CI to wait on; otherwise
checks must pass. Running, failed, or `other` states block merge. If the operation
reports an error, stop and report it. If the head changed, return to review within
the phase cap. If checks time out, stop and report them.

Run **`CR_MERGE`** with `<id>` only after these gates pass and merge is within the
user's requested scope. Surface branch-protection refusals rather than forcing it.

### 4. Update Transit Ticket

If a Transit ticket is being tracked, move it to `done`:

```
# read the task first: mcp__transit__query_tasks(displayId={id}) -> revision
mcp__transit__update_task_status(displayId={id}, status="done",
  expectedRevision=<revision>, idempotencyKey=<fresh UUID>, comment="Merged via squash-and-merge — CR {id}", authorName="claude[bot]")
```

If no Transit ticket is tracked, skip this step.

### 5. Summary

Report the outcome:

```
CR {id} — {MERGED|FAILED}
- Review rounds: N
- Transit: T-{id} → done (or N/A)
```
