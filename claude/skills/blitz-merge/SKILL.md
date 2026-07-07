---
name: blitz-merge
description: Batch-fix all open bugs in parallel, iterate on PR reviews until clean, then squash-merge each PR sequentially. Extends bug-blitz with automated review cycles and merge. Fetches bug-type tasks from Transit, creates worktrees, spawns parallel fix agents, runs /pr-review-fixer in a loop until no blockers/critical/major issues remain, then merges PRs one by one with squash-and-merge.
# model: inherit
# allowed-tools: Read,Write,Edit,Bash,Grep,Glob,Task
---

# Blitz Merge

Resolve all open bugs in parallel, get PRs review-clean, then squash-merge them one by one.

## Workflow

### Phase 1: Fix Bugs (same as bug-blitz)

#### 1.1 Fetch Bugs

First, determine the current project by calling `mcp__transit__get_projects()` and matching the current repository name against the project list. If no matching Transit project is found, inform the user and stop.

Then query Transit for all bug-type tasks in "idea" status, filtered by the matched project:

```
mcp__transit__query_tasks(type="bug", status=["idea"], project="{project_name}")
```

If no bugs are found, inform the user and stop.

Present the list of bugs to the user with their `T-{displayId}` references and names. Ask for confirmation before proceeding. The user may choose to exclude specific bugs.

#### 1.2 Create Worktrees

For each confirmed bug:

1. Derive a bug name in kebab-case from the task name
2. Create a worktree based off `main` with branch `T-{displayId}/bugfix-{bug-name}`:
   ```
   git worktree add ../{repo-name}-worktrees/T-{displayId} -b T-{displayId}/bugfix-{bug-name} main
   ```

All worktrees go in a sibling directory `../{repo-name}-worktrees/` to keep the main repo clean. Use the repo's directory name as `{repo-name}`.

If a worktree or branch already exists for a bug, skip creation and reuse it.

#### 1.3 Spawn Fix Subagents

Spawn one Task subagent per bug using `subagent_type="general-purpose"`. Run all subagents in parallel (single message, multiple Task tool calls).

Each subagent receives this prompt (fill in the values):

```
You are working in a git worktree at {worktree_path}.

Fix the bug described by Transit ticket T-{displayId}:
- Name: {task_name}
- Description: {task_description}

Run the /fix-bug skill with the ticket reference T-{displayId}.
The worktree already has the correct branch checked out — do NOT create a new branch or switch branches.
Work entirely within {worktree_path} as your working directory.
```

#### 1.4 Collect Fix Results

After all fix subagents complete, collect results into a tracking table:

| Bug | Branch | Fix Status | PR |
|-----|--------|------------|----|
| T-{id}: {name} | T-{id}/bugfix-{name} | success/failed | #{pr} or — |

If a bug failed to produce a PR, exclude it from the review and merge phases. Keep its worktree for manual investigation.

### Phase 2: Review Loop

For each PR that was successfully created, run the review-fix cycle. Process PRs in parallel where possible.

A merge must never land code that no review ever looked at. Define a helper that counts the review comments already on a PR — a comment qualifies if its author is a Claude/GitHub bot **or** its body carries the `local-review` sentinel:

```bash
count_reviews() {
  gh api graphql -f query='
    query($owner:String!,$repo:String!,$pr:Int!){repository(owner:$owner,name:$repo){pullRequest(number:$pr){
      reviews(first:50){nodes{body author{login}}}
      comments(first:100){nodes{body author{login}}}}}}' \
    -f owner=OWNER -f repo=REPO -F pr="$1" \
    --jq '[.data.repository.pullRequest.reviews.nodes[], .data.repository.pullRequest.comments.nodes[]]
       | map(select((.author.login | test("claude|github-actions";"i")) or (.body | test("claude-local-review"))))
       | length'
}
```

#### 2.1 Wait for CI and Reviews — and guarantee one exists

Record the review count before waiting, so you can tell whether a review actually lands:

```bash
PRE_REVIEWS=$(count_reviews "$pr_number")
```

Wait for CI and reviewers to arrive. Prefer polling `gh pr checks $pr_number` until the checks leave `pending`, capped at ~10 minutes after the PR was created (or after the last push). Run the poll in the background so a single failure can't cancel sibling work.

**Fallback — never proceed with no review.** Once the checks conclude, confirm this round actually produced a review:

```bash
POST_REVIEWS=$(count_reviews "$pr_number")
if [ "${POST_REVIEWS:-0}" -le "${PRE_REVIEWS:-0}" ]; then
  echo "No new Claude/bot review landed for PR $pr_number — falling back to local-review"
  # invoke the local-review agent on $pr_number, then give it ~1-2 min to post before continuing.
fi
```

The delta (`POST <= PRE`) catches every empty case — a GH Action that finished `success` without commenting, a review that errored, or a token-less Action — without re-running `local-review` when a review did land. Run the fallback at most once per round. A silent, errored, or skipped GH Action therefore never leaves the loop with nothing to act on. (This is the safeguard `pr-pilot` gained after a zero-review merge slipped through; blitz-merge now has parity.)

#### 2.2 Run PR Review Fixer

For each PR, spawn a subagent in its worktree:

```
You are working in a git worktree at {worktree_path}.
The branch {branch_name} is checked out and has PR #{pr_number} open.

Run the /pr-review-fixer skill to fetch unresolved PR comments and CI failures, validate them, and fix any issues found.

After the skill completes, output a summary line in exactly this format:
REVIEW_RESULT: {CLEAN|HAS_ISSUES}
- CLEAN means no blockers, critical, or major issues were found (minor/nitpick items are acceptable)
- HAS_ISSUES means there were blockers, critical, or major items that were fixed (another round is needed)
```

#### 2.3 Evaluate and Repeat

After each review-fixer run:

- **HAS_ISSUES**: The skill already fixed the problems and pushed. Wait 10 minutes, then run the review fixer again (go to step 2.1).
- **CLEAN**: No blockers, critical, or major issues remain. Mark this PR as review-complete.

Cap the loop at 5 iterations per PR. If still not clean after 5 rounds, flag it for manual review and exclude from the merge phase.

#### 2.4 Generate a Reviewable Pre-Push Artifact

Once a PR is review-complete (CLEAN), produce a durable review artifact you can read before it merges. The automated loop is Claude reviewing Claude, so this artifact is the independent record a human can audit — the point of blitz-merge is unattended throughput, not unattended *and* unreviewable.

Spawn a subagent in the PR's worktree that runs the `/pre-push-review` skill against what the PR will actually land on `main`:

```
You are working in the git worktree at {worktree_path} with branch {branch_name} (PR #{pr_number}) checked out.

Run the /pre-push-review skill, reviewing the changes this PR will add to main. Fetch origin/main first (`git fetch origin main`) and review the diff `git diff origin/main...HEAD` — NOT the already-pushed feature branch (that diff is empty). Produce the review HTML artifact and, if `pulsar` is on PATH, let the skill publish it.

Report back: the path to the review artifact, and the verdict — Ready to push / Needs fixes / Requires discussion.
```

Record the artifact path per PR. If the subagent reports **Needs fixes** or **Requires discussion**, treat the PR as HAS_ISSUES and go back to step 2.1 for another round rather than merging. Only a review-complete PR **with** a generated artifact is eligible for Phase 3.

#### 2.5 Update Transit Tickets

When a PR passes the review loop:
- The ticket should already be at `ready-for-review` from the fix-bug skill
- No status change needed yet — it moves to `done` after merge

If a PR is excluded (failed after 5 rounds), add a comment to the Transit ticket: "Automated review loop did not converge after 5 iterations — manual review needed."

### Phase 3: Sequential Merge

Merge completed PRs one at a time. Order does not matter, but sequential merging avoids conflicts piling up.

#### 3.1 Pre-merge Checklist (per PR)

For each review-complete PR:

1. **Fetch latest main**:
   ```bash
   cd {worktree_path}
   git fetch origin main
   ```

2. **Rebase onto latest main**:
   ```bash
   git rebase origin/main
   ```

3. **If conflicts arise**: Resolve them in the worktree. After resolving:
   ```bash
   git rebase --continue
   ```
   Run the project's test suite and linter to verify the merge is clean.

4. **Force-push the rebased branch** (safe because it's a feature branch):
   ```bash
   git push --force-with-lease
   ```

5. **Wait for CI**: Check that CI passes on the rebased branch:
   ```bash
   gh pr checks {pr_number} --watch
   ```

#### 3.2 Squash and Merge

Do **not** merge unless BOTH hold for this PR:

1. **A review is on record** — `count_reviews {pr_number}` returns ≥ 1 (the 2.1 fallback guarantees this), and
2. **The pre-push artifact from step 2.4 exists** and its verdict was not "Requires discussion".

If either is missing, skip the merge and flag the PR for manual review. Otherwise, once CI is green:

```bash
gh pr merge {pr_number} --squash --delete-branch
```

#### 3.3 Update Transit Ticket

After successful merge, move the Transit ticket to `done`:

```
mcp__transit__update_task_status(displayId={id}, status="done", comment="Merged via squash-and-merge — PR #{pr_number}", authorName="claude[bot]")
```

#### 3.4 Continue to Next PR

Pull the newly merged main into the next PR's worktree (handled by the fetch + rebase in step 3.1 for the next iteration).

### Phase 4: Update Local Main

After all merges are complete, update the local main/master branch so it reflects the merged changes:

```bash
cd {original_repo_path}
git checkout main
git pull origin main
```

If the repo uses `master` instead of `main`, substitute accordingly.

This ensures the local default branch is up to date with origin after all squash-merges.

### Phase 5: Report and Cleanup

#### 5.1 Final Report

Present a summary of all bugs:

| Bug | PR | Review Rounds | Merge Status | Transit |
|-----|-----|---------------|--------------|---------|
| T-{id}: {name} | #{pr} | N | merged/failed/manual review | done/ready-for-review |

#### 5.2 Cleanup Worktrees

Remove worktrees for successfully merged bugs:

```bash
git worktree remove ../{repo-name}-worktrees/T-{displayId}
```

Keep worktrees for:
- Bugs that failed during fixing
- PRs that didn't pass the review loop
- PRs that failed to merge

Inform the user which worktrees were kept and why.
