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

### 2. Review Loop

#### 2.1 Wait for CI and Reviews

Wait 10 minutes after the PR was created (or after the last push) to allow CI checks and reviewer comments to arrive.

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

#### 3.3 Wait for CI

```bash
gh pr checks {pr_number} --watch
```

If CI fails after rebase, run `/pr-review-fixer` once more to fix CI issues. If it still fails, inform the user and stop.

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
