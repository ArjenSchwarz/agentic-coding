---
name: pr-pilot
description: Push a branch, create a PR, iterate on reviews until clean, then squash-merge. Runs /pr-review-fixer in a loop until no blockers/critical/major issues remain, rebases onto latest origin/main, and squash-merges. Works with or without Transit tickets. Use when you want to shepherd a PR from push to merge, e.g. "push and merge this", "get this PR merged", "review-fix-merge loop".
# model: inherit
# allowed-tools: Read,Write,Edit,Bash,Grep,Glob,Task
---

# PR Pilot

Push a branch, create a PR, loop through reviews until clean, then squash-merge.

## Input

The skill works in the current working directory (or a specified worktree path). It needs:

- A branch with committed changes ready to push
- Optionally a Transit ticket reference (`T-{id}`) for status tracking
- Optionally an existing PR number (skips push and PR creation)

If invoked with arguments, parse them for:
- `T-{number}` — Transit ticket to track
- `#{number}` or a PR number — existing PR to work with
- A path — working directory override

## Workflow

### 1. Push and Create PR

If no existing PR number was provided:

1. **Push the branch**:
   ```bash
   git push -u origin HEAD
   ```

2. **Create the PR**:
   ```bash
   PR_NUM=$(gh pr create --fill --json number --jq '.number')
   ```
   If the branch name contains a `T-{number}` prefix, include it in the PR title.

If an existing PR was provided, fetch its details:
```bash
gh pr view {pr_number} --json number,headRefName,state
```

### 1.5 Detect Claude Review Marker

Check whether this repo has opted in to Claude PR reviews by looking for an **active** workflow that references the upstream action. By convention the workflow is named `claude-code-review.yml`, but the check matches by content so any filename works as long as the file is a real workflow (`*.yml` or `*.yaml`):

```bash
HAS_CLAUDE_REVIEW=0
FOUND=$(find .github/workflows -maxdepth 1 -type f \( -name '*.yml' -o -name '*.yaml' \) 2>/dev/null)
if [ -n "$FOUND" ] && printf '%s\n' "$FOUND" | xargs grep -lq 'anthropics/claude-code-action' 2>/dev/null; then
  HAS_CLAUDE_REVIEW=1
fi
```

The `find` step is the bit that matters: it deliberately excludes files GitHub Actions does not execute (`claude-code-review.yml.disabled`, `.bak`, editor swap files, etc.). Renaming the workflow to `*.yml.disabled` is the easiest way to keep the file as a marker while preventing the upstream Action from running — but doing so also turns `HAS_CLAUDE_REVIEW` off, so `local-review` will be skipped too. If you want local-only Claude reviews, keep the file as `*.yml` and gate the workflow's `on:` trigger (e.g. to a tag or label) instead of renaming.

If `HAS_CLAUDE_REVIEW=0`, skip every "Run Local Claude Review" step below.

### 2. Review Loop

#### 2.1 Run Local Claude Review and Wait for CI

If `HAS_CLAUDE_REVIEW=1`, invoke the `local-review` agent on the PR (pass the PR number from step 1) so the Claude review comment is posted from your local subscription instead of being produced by GitHub Actions. The agent reads the repo's `CLAUDE.md`, fetches `gh pr diff`, and posts one `gh pr comment` that `pr-review-fixer` will absorb in step 2.2 alongside any other reviewer comments.

Then wait 10 minutes after the PR was created (or after the last push) to allow CI checks and other reviewer comments to arrive.

#### 2.2 Run PR Review Fixer

Run the `/pr-review-fixer` skill to fetch unresolved PR comments and CI failures, validate them, and fix any issues found.

After the skill completes, evaluate the results:
- **CLEAN**: No blockers, critical, or major issues were found. Minor and nitpick items are acceptable.
- **HAS_ISSUES**: There were blockers, critical, or major items that were fixed and pushed. Another round is needed.

#### 2.3 Evaluate and Repeat

- **HAS_ISSUES**: Wait 10 minutes, then go back to step 2.1.
- **CLEAN**: Proceed to merge.

Cap the loop at 5 iterations. If still not clean after 5 rounds, inform the user and stop. Do not merge.

If a Transit ticket is tracked, add a comment: "Automated review loop did not converge after 5 iterations — manual review needed."

### 3. Rebase and Merge

#### 3.1 Rebase onto Latest Main

```bash
git fetch origin main
git rebase origin/main
```

If conflicts arise, resolve them. After resolving:
```bash
git rebase --continue
```

Run the project's test suite and linter to verify the rebase is clean.

#### 3.2 Push Rebased Branch

```bash
git push --force-with-lease
```

#### 3.3 Run Local Claude Review and Wait for CI

If `HAS_CLAUDE_REVIEW=1`, invoke `local-review` again on the PR so the post-rebase diff gets a fresh Claude comment locally. Skip otherwise.

Wait 10 minutes after the force push to allow CI checks and other agent reviewers to run.

Then run `/pr-review-fixer` to check for new review comments and CI failures — agent reviewers will post fresh comments on the rebased code.

- **CLEAN**: Proceed to merge.
- **HAS_ISSUES**: Fix, push, and repeat (up to 3 iterations). If still not clean, inform the user and stop.

#### 3.4 Squash and Merge

```bash
gh pr merge {pr_number} --squash --delete-branch
```

### 4. Update Transit Ticket

If a Transit ticket is being tracked, move it to `done`:

```
mcp__transit__update_task_status(displayId={id}, status="done", comment="Merged via squash-and-merge — PR #{pr_number}", authorName="claude[bot]")
```

If no Transit ticket is tracked, skip this step.

### 5. Summary

Report the outcome:

```
PR #{pr_number} — {MERGED|FAILED}
- Review rounds: N
- Transit: T-{id} → done (or N/A)
```
