---
name: smart-blitz
description: Triage-first batch bug fixing with streaming review and merge. Extends blitz-merge with an upfront triage phase that prioritises open bugs, groups them into conflict-free batches, and assigns each the minimum model tier capable of fixing it (Claude Code sonnet/opus, Kiro and Codex gpt-6 luna/sol). Reviews and merges each PR as soon as its fix lands instead of waiting for the whole batch. Use for "smart blitz", "triage and fix all bugs", "fix bugs by priority", "batch-fix with the cheapest model", or any request to blitz bugs with prioritisation or cost awareness.
# model: inherit
# allowed-tools: Read,Write,Edit,Bash,Grep,Glob,Task
---

# Smart Blitz

Triage all open bugs, then fix them in prioritised conflict-free batches — each bug on the smallest model that can handle it — and stream every PR through review and merge as soon as its fix completes.

This skill is harness-agnostic: the same workflow runs under Claude Code, Kiro, or Codex. Where the harnesses differ (model names, how to spawn a parallel agent), a mapping table says what to use; everything else is identical.

## Harness Mapping

Determine which harness you are running in (you know your own identity) and use that column throughout.

### Model tiers

Assign every bug one of three tiers during triage. The goal is the *minimum* model that can plausibly fix the bug — capacity above the tier is wasted spend.

| Tier | Claude Code | Kiro | Codex | Effort |
|----------|-------------|-----------------|-----------------|--------|
| light | sonnet | gpt-6-luna | gpt-6-luna | xhigh |
| standard | sonnet | gpt-6-sol | gpt-6-sol | high |
| heavy | opus | gpt-6-sol | gpt-6-sol | high |

Claude Code has only two usable models, so light and standard both map to sonnet. Likewise, gpt-6 has no mid-size model, so in Kiro and Codex standard and heavy both map to gpt-6-sol at high effort. Keep the three-tier assignment anyway — the tier travels with the bug if it is later re-run in another harness, and escalation (below) needs the distinction.

The effort ladder is deliberately inverted: a smaller model compensates with more reasoning effort, while the heavy model needs less. Apply it where the harness supports per-agent effort — Codex `spawn_agent` takes `reasoning_effort` directly; Kiro only honours effort at the session level (`--effort` in the CLI fallback), not in agent configs; Claude Code subagents have no effort control.

### Spawning a parallel fix agent

Each harness has a native subagent mechanism — use it rather than launching separate CLI sessions. The difference is where the model is selected: per call (Claude Code, Codex) or per named agent config (Kiro).

- **Claude Code**: Task tool, `subagent_type="general-purpose"`, with the `model` parameter set to the assigned model. Multiple Task calls in a single message run in parallel.
- **Kiro**: the `use_subagent` tool (`InvokeSubagents`, up to 4 subagents per call — split larger batches across calls). It has no model parameter; model comes from the named agent config. Before the first batch, ensure configs `gpt-light`, `gpt-standard`, and `gpt-heavy` exist in `~/.kiro/agents/` — create each by copying the `kiro` agent config (so tools, MCP servers, and hooks carry over) and setting `name`, `"model"` to the tier's model, and `"effort"` to the tier's effort (the effort field is ignored by current agent-config schemas but documents intent and applies if support lands). Then invoke each bug with the `agent_name` matching its tier.

  Effort is session-global in Kiro — subagents inherit the session's effort level, so one parallel wave cannot mix tiers. Split each batch into **effort groups**: bugs sharing a tier's effort, max 4 per group (the `InvokeSubagents` cap), groups ordered by the priority of the bugs they contain. Run the groups sequentially. Before starting each group, check the session's current effort level; if it does not match the group's effort — or you cannot confirm what it is — stop and ask the user to run `/effort {level}`, and wait for their confirmation before invoking the subagents.
- **Codex**: the `spawn_agent` tool with `fork_turns: "none"` (a fix agent needs a fresh context, and model overrides are only honoured when the history is not forked), `model` set to the assigned model, and `reasoning_effort` set to the tier's effort; collect results with `wait_agent`. The accepted override list may be a subset of the full ladder (luna is not always offered) — if a tier's model is rejected, use the nearest accepted tier above it.

If the native mechanism is unavailable for some reason, fall back to one headless process per bug (`kiro-cli chat --no-interactive --model {model} --effort {effort}` / `codex exec --cd {worktree_path} -m {model} -c model_reasoning_effort="{effort}" --full-auto`) run in the background from the bug's worktree.

### Escalation

The minimum-model bet will sometimes be wrong. If a fix agent fails to produce a PR, or its PR fails to converge in the review loop (see Phase 3), retry that bug **once** on the next tier up (light → standard → heavy; sonnet → opus). A bug that fails on the heavy tier is flagged for manual work — do not loop further.

## Workflow

### Phase 1: Fetch Bugs

Determine the current project by calling `mcp__transit__get_projects()` and matching the current repository name against the project list. If no matching Transit project is found, inform the user and stop.

Query Transit for all bug-type tasks in "idea" status, filtered by the matched project:

```
mcp__transit__query_tasks(type="bug", status=["idea"], project="{project_name}")
```

If no bugs are found, inform the user and stop.

### Phase 2: Triage

Investigate each bug before spending anything on fixing it. For a handful of bugs do this inline with Grep/Read; for larger sets spawn parallel **read-only** triage agents on the light tier — triage itself should be cheap. Each bug's triage answers three questions:

1. **Where will the fix land?** Predict the files/subsystem the fix will touch. This drives batching, so be honest about uncertainty — if you cannot localise a bug, treat it as touching its whole subsystem.
2. **How urgent is it?** Use the Transit priority field if set; otherwise rank by severity: data loss / crash / security first, then broken core behaviour, then incorrect edge-case behaviour, then cosmetic.
3. **How hard is it?** Assign the tier:
   - **light**: fix location is certain and mechanical — typo, message text, config value, missing guard clause, off-by-one with an obvious repro.
   - **standard**: localised logic bug in one module; root cause findable from the description; needs a real fix plus a regression test.
   - **heavy**: root cause unclear, cross-cutting, concurrency/ordering involved, or touches data models/migrations/public API. When in doubt between standard and heavy, pick standard — escalation covers underestimates, but overestimates are pure waste.

#### Build batches

Two bugs **conflict** if their predicted fix areas overlap (shared files, or same tightly-coupled module). Batching rule: no two bugs in the same batch may conflict, and higher-priority bugs go in earlier batches. Build greedily: sort by priority, put each bug in the earliest batch where it conflicts with nothing, never placing a bug in an earlier batch than a higher-priority bug it conflicts with. Bugs in *different* batches are allowed to conflict — that is exactly what the batch boundary is for.

#### Present for approval

Show the triage result and wait for explicit approval before touching anything:

| Bug | Priority | Predicted area | Tier | Model | Batch |
|-----|----------|----------------|------|-------|-------|
| T-{id}: {name} | high/med/low | {files or subsystem} | light/standard/heavy | {model} | 1..N |

The user may exclude bugs, reorder priorities, change tiers, or move bugs between batches. Do not start Phase 3 without a go-ahead.

### Phase 3: Execute Batches with Streaming Review and Merge

Process batches strictly in order. Within a batch everything is parallel and event-driven: each bug flows through fix → review → merge independently, reacting to completions as they arrive. **Never hold a finished fix hostage to its batch siblings** — the moment one fix agent completes, its PR enters the review pipeline while the others are still working.

Start batch N+1 only when every bug in batch N has reached a terminal state (merged, or flagged for manual work). Cross-batch bugs may conflict, so an early start would build fixes on a main that is about to change under them.

#### 3.1 Fix (per batch)

For each bug in the current batch:

1. Derive a bug name in kebab-case from the task name
2. Create a worktree based off `main` with branch `T-{displayId}/bugfix-{bug-name}`:
   ```
   git worktree add ../{repo-name}-worktrees/T-{displayId} -b T-{displayId}/bugfix-{bug-name} main
   ```
   Worktrees live in the sibling directory `../{repo-name}-worktrees/` to keep the main repo clean. If a worktree or branch already exists for a bug, reuse it.
3. Spawn a fix agent (see Harness Mapping) on the bug's assigned model with this prompt:

```
You are working in a git worktree at {worktree_path}.

Fix the bug described by Transit ticket T-{displayId}:
- Name: {task_name}
- Description: {task_description}

Run the /fix-bug skill with the ticket reference T-{displayId}.
The worktree already has the correct branch checked out — do NOT create a new branch or switch branches.
Work entirely within {worktree_path} as your working directory.
```

Spawn all fix agents for the batch in parallel (under Kiro, as sequential effort groups — see Harness Mapping). As each one completes: if it produced a PR, immediately start 3.2 for that PR; if it failed, apply the escalation rule (one retry, next tier up) and only then flag for manual work.

#### 3.2 Review Loop (per PR, starts as each fix lands)

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

**Wait for CI and reviews — and guarantee one exists.** Record `PRE_REVIEWS=$(count_reviews "$pr_number")` before waiting. Poll `gh pr checks $pr_number` until the checks leave `pending`, capped at ~10 minutes after the PR was created (or after the last push). Run the poll in the background so a single failure cannot cancel sibling pipelines.

Once the checks conclude, confirm this round actually produced a review:

```bash
POST_REVIEWS=$(count_reviews "$pr_number")
if [ "${POST_REVIEWS:-0}" -le "${PRE_REVIEWS:-0}" ]; then
  echo "No new Claude/bot review landed for PR $pr_number — falling back to local-review"
  # invoke the local-review agent on $pr_number, then give it ~1-2 min to post before continuing.
fi
```

The delta catches every empty case — an Action that finished `success` without commenting, a review that errored, a token-less Action — without re-running local-review when a review did land. Run the fallback at most once per round.

**Run the review fixer.** Spawn a subagent in the PR's worktree (default model — review fixing is not tier-assigned):

```
You are working in a git worktree at {worktree_path}.
The branch {branch_name} is checked out and has PR #{pr_number} open.

Run the /pr-review-fixer skill to fetch unresolved PR comments and CI failures, validate them, and fix any issues found.

After the skill completes, output a summary line in exactly this format:
REVIEW_RESULT: {CLEAN|HAS_ISSUES}
- CLEAN means no blockers, critical, or major issues were found (minor/nitpick items are acceptable)
- HAS_ISSUES means there were blockers, critical, or major items that were fixed (another round is needed)
```

- **HAS_ISSUES**: the fixer already pushed fixes. Wait ~10 minutes for fresh reviews, then repeat the wait-and-fix round.
- **CLEAN**: proceed to the pre-push artifact.

Cap the loop at 5 rounds per PR. A PR still not clean after 5 rounds triggers the escalation rule: re-run the fix on the next tier up in the same worktree (once), or — if already on the heavy tier — flag for manual review and comment on the Transit ticket: "Automated review loop did not converge after 5 iterations — manual review needed."

**Generate a reviewable pre-push artifact.** The automated loop is Claude reviewing Claude, so produce the independent record a human can audit. Spawn a subagent in the worktree:

```
You are working in the git worktree at {worktree_path} with branch {branch_name} (PR #{pr_number}) checked out.

Run the /pre-push-review skill, reviewing the changes this PR will add to main. Fetch origin/main first (`git fetch origin main`) and review the diff `git diff origin/main...HEAD` — NOT the already-pushed feature branch (that diff is empty). Produce the review HTML artifact and, if `pulsar` is on PATH, let the skill publish it.

Report back: the path to the review artifact, and the verdict — Ready to push / Needs fixes / Requires discussion.
```

Record the artifact path. **Needs fixes** or **Requires discussion** sends the PR back for another review round rather than to the merge queue. Only a CLEAN PR with a generated artifact enters the merge queue.

#### 3.3 Merge Queue (serialized, drains as PRs become ready)

Review-complete PRs enter a queue that is drained **one PR at a time**, concurrently with fix agents and review loops that are still running. Streaming applies here too: merge the first ready PR immediately rather than waiting for the batch. Serialization is only per-merge — rebasing onto a main that another merge is simultaneously moving is how conflicts pile up.

For each PR leaving the queue:

1. In the worktree: `git fetch origin main && git rebase origin/main`. Resolve any conflicts, then run the project's test suite and linter to verify.
2. `git push --force-with-lease` (safe — feature branch).
3. Wait for CI on the rebased branch: `gh pr checks {pr_number} --watch`.
4. Merge only if BOTH hold: `count_reviews {pr_number}` returns ≥ 1, **and** the pre-push artifact exists with a verdict other than "Requires discussion". If either is missing, skip and flag for manual review.
   ```bash
   gh pr merge {pr_number} --squash --delete-branch
   ```
5. Move the Transit ticket to done:
   ```
   mcp__transit__update_task_status(displayId={id}, status="done", comment="Merged via squash-and-merge — PR #{pr_number}", authorName="claude[bot]")
   ```

When the last bug of the batch reaches a terminal state, start the next batch at 3.1.

### Phase 4: Update Local Main

After all batches are done:

```bash
cd {original_repo_path}
git checkout main
git pull origin main
```

If the repo uses `master` instead of `main`, substitute accordingly.

### Phase 5: Report and Cleanup

Present a final summary:

| Bug | Batch | Model (final) | Escalated | PR | Review Rounds | Merge Status | Transit |
|-----|-------|---------------|-----------|-----|---------------|--------------|---------|
| T-{id}: {name} | N | {model} | yes/no | #{pr} | N | merged/failed/manual review | done/ready-for-review |

Note in the report where triage guessed wrong (escalations, unpredicted conflicts at rebase time) — that feedback is what makes the next triage better.

Remove worktrees for successfully merged bugs:

```bash
git worktree remove ../{repo-name}-worktrees/T-{displayId}
```

Keep worktrees for bugs that failed during fixing, PRs that did not pass the review loop, and PRs that failed to merge. Inform the user which worktrees were kept and why.
