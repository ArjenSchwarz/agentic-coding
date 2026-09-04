---
name: pr-overview
description: Pull a PR from GitHub, run parallel review agents (code reuse, quality, efficiency, spec adherence) in read-only mode, surface unresolved comments, and write a self-contained HTML overview page to the repo root. Use whenever the user wants a read-only summary of a PR before deciding what to do — phrases like "overview of PR X", "summarise this PR", "what's the state of PR X", "give me an HTML overview", or any time they want a browseable artifact without touching the code.
---

# PR Overview

Fetch a GitHub PR, review it through multiple specialized agents (read-only), collect any unresolved comments, and produce a self-contained HTML overview at `pr-overview.html` in the repo root so the user can read it in a browser.

This skill never modifies code, never commits, never pushes, and never resolves comment threads. It only produces an overview. For a workflow that also applies fixes, use `pr-review-html`; for one that addresses reviewer comments, use `pr-review-fixer`.

Two caveats to "never touches the repository": when CI has no usable test artifacts and the PR is a same-repo PR in a repository you have cloned, Phase 1b executes the branch's install scripts and tests on this machine, in a throwaway git worktree under the job directory, with your environment and credentials; and fetching the PR head writes a ref into the clone's `.git` (`FETCH_HEAD`), which touches no working-tree file and no branch.

## Phase 1: Fetch the PR

Resolve which PR to look at, in this order:
- An explicit number, URL, or branch name from the user
- Otherwise the PR for the current branch via `gh pr view --json number`

Pull what you need:

```bash
gh pr view <pr> -R <owner>/<repo> --json number,title,author,baseRefName,headRefName,headRefOid,isCrossRepository,headRepository,body,url,state,commits,files,createdAt
```

**Pin the snapshot.** `SHA=<headRefOid>` from that JSON is the commit every later step describes — the diffs, the CI lookup, the fetch, the worktree, and the diagram all use it, so a branch that moves mid-review cannot give the page data from two trees. `isCrossRepository: true` means a fork PR. Every `gh api` and `gh run` call in this skill carries `-R <owner>/<repo>` so it works without a clone, and list endpoints use `--paginate`.

**Working directory.** Every generated input — diff fragments, downloaded artifacts, the diagram, the overview JSON itself — lives in `$INPUTS`, outside any working tree:

```bash
INPUTS="${CLAUDE_JOB_DIR:-$(mktemp -d)}/review-inputs"; mkdir -p "$INPUTS"
```

Both `$CLAUDE_JOB_DIR` and `mktemp -d` yield absolute paths; never use a relative one, as the Phase 1b subshell would resolve it into the worktree.

**Read the trees without checking out.** Do **not** run `gh pr checkout`. The user may be on a different branch deliberately, and switching branches risks losing work. Decide whether the current directory is a clone of the PR's repository (`git remote get-url origin` names `<owner>/<repo>`):

- *With a clone:* `git fetch origin refs/pull/<n>/head` and verify `test "$(git rev-parse FETCH_HEAD)" = "$SHA"` — the pull ref exists for every PR, forks included, and fetching executes nothing. Stop if the SHAs differ (the PR moved between `gh pr view` and the fetch; re-pin and fetch again). Then `git fetch origin <baseRefName>`, `MERGE_BASE=$(git merge-base origin/<baseRefName> "$SHA")`, and take the full diff for the agents from `git diff "$MERGE_BASE" "$SHA"`. Per-file fragments (Phase 6 step 1) come from `git diff "$MERGE_BASE" "$SHA" -- <path>`. Code context beyond the diff comes from `git show "$SHA":<path>`.
- *Without a clone:* `gh api -R <owner>/<repo> --paginate repos/<owner>/<repo>/compare/<baseRefName>...$SHA` gives `merge_base_commit.sha` as `MERGE_BASE` and one `patch` per entry in `files[]`. The API omits patches for binary files and lists at most 300 files; record any file without a patch as a missing fragment rather than fabricating one. Code context comes from `gh api -R <owner>/<repo> "repos/<owner>/<repo>/contents/<path>?ref=$SHA"`.

Keep the PR `body`, `author`, `createdAt`, and `url` from the `gh pr view` JSON — these flow into Phase 6's `pr_description` section so the reader can see the author's framing verbatim.

Show the user which PR you're about to summarise (number, title, author, head → base, commit count, pinned SHA, fork or not) before doing the heavier work — a cheap sanity check that catches the wrong PR number early.

## Phase 1b: Collect test results

Test data comes from GitHub Actions artifacts for the pinned SHA first, and from a local run in a throwaway worktree only when CI has nothing and the trust conditions below hold. Record what happened in the `tests` block (Phase 6): `provenance.ci_state` and `provenance.fallback_state` are separate fields, so "fork PR with expired artifacts" is two facts.

### CI artifacts

```bash
gh run list -R <owner>/<repo> --commit "$SHA" --json databaseId,status,conclusion,name,url
gh api -R <owner>/<repo> --paginate repos/<owner>/<repo>/actions/runs/<id>/artifacts   # name, expired, size_in_bytes
gh api -R <owner>/<repo> --paginate repos/<owner>/<repo>/actions/runs/<id>/jobs        # name, conclusion, html_url
gh run download <id> -R <owner>/<repo> -n <artifact> -D "$INPUTS/artifacts/<id>/<artifact>"
```

Record every job's name, outcome, and URL in `tests.jobs`. Download only artifacts with `expired: false` and `size_in_bytes` at most 100 MB; list larger ones by name and size in `tests.skipped_artifacts`. Identify files by content, never by name: JUnit is XML whose root element is `testsuites` or `testsuite`; Cobertura is XML rooted at `coverage`; lcov starts with `TN:` or `SF:`; coverprofile starts with `mode: `. Copy each recognised file into `$INPUTS` as `<run_id>-<artifact>--<basename>` so two artifacts or two runs cannot collide, and reference those names from `tests.junit`, `tests.coverage`, and `tests.artifacts[]`.

**CI state** is derived after sniffing, first rule that matches:

1. Any completed run yielded a JUnit file → `artifacts usable`; runs still `in_progress` or `queued` go into `tests.pending_runs` and the page notes them.
2. Any run `in_progress` or `queued` → `run in progress or queued`.
3. No runs → `no run`.
4. At least one artifact exists across completed runs and every one is expired → `artifacts expired`.
5. Any completed run with `conclusion: failure` and zero artifacts → `run failed before upload`.
6. Otherwise → `artifacts absent` (covers artifacts that contain no JUnit).

**Job attribution.** Artifacts belong to a run, not a job, so attribution is a convention: tokenise job and artifact names into lowercase alphanumeric runs; a file is attributed to the job whose token set is a subset of the artifact's token set, choosing the job with the most tokens; a tie leaves it attributed to the artifact. `test (ubuntu)` → `{test, ubuntu}` matches `test-results-ubuntu`. Put the winner in `tests.artifacts[].job`, or omit it.

### Worktree fallback

Permitted only when the CI state is `no run`, `run failed before upload`, `artifacts expired`, or `artifacts absent`. Otherwise `fallback_state` is `not needed` (artifacts usable) or `blocked by run in progress`. Then two trust conditions, checked in this order and recorded as the blocked state when they fail: the PR must be a same-repo PR (`isCrossRepository: false`; otherwise `blocked by fork PR` — fork code never runs here), and the current directory must be a clone of the PR's repository (otherwise `blocked by no local clone`).

Choose the command as `pr-review-html` Phase 5 does: read `~/.claude/scripts/ecosystems.json`, pick the language row covering the most changed files and the runner whose `detect` rule matches, then take the first tier that applies reading text only — a Makefile target whose literal recipe lines contain one of the runner's `junit_flags` (never `make -n`), a documented project test command with such a flag, or the runner's `recipe` with `{junit}`, `{coverage}`, `{inputs}` replaced by absolute paths under `$INPUTS`, its `env` exported, and its `config_files` written first. A missing `requires` binary records `no_data_reason: "required tool missing"`; no row or runner records `runner not detected`. `coverage_scope` is `repository` for the ecosystem recipe and `project-configured` otherwise.

Run everything in **one Bash call** with `timeout: 600000` (the tool's maximum, covering install and tests), with `WT="$CLAUDE_JOB_DIR/wt-<n>-<sha7>"` (or under the same `mktemp -d` parent as `$INPUTS` when the job directory is unset):

```bash
git worktree prune
git fetch origin refs/pull/<n>/head && test "$(git rev-parse FETCH_HEAD)" = "$SHA"
git worktree add --detach "$WT" "$SHA"
(cd "$WT" && <install> && <recipe with absolute $INPUTS paths>); status=$?
python3 ~/.claude/scripts/blast_radius.py --repo "$WT" --snapshot "$SHA" --base "$MERGE_BASE" --tools --out "$INPUTS"
git worktree remove --force "$WT"; git worktree prune
echo "recipe-status=$status"
```

`git worktree prune` at the start drops only entries whose directories are gone and skips locked ones; never remove a worktree that still exists on disk. The recipe's exit status becomes `run_outcome` (`passed` or `failed`) and `fallback_state` becomes `ran`. `blast_radius.py --tools` runs inside the same call because the worktree is the only checkout this skill has and it is gone afterwards; Phase 6 then skips its own `blast_radius.py` invocation. All outputs are under `$INPUTS`, so nothing is lost when the worktree goes.

If the call times out: run `git worktree remove --force "$WT"; git worktree prune` separately, keep whatever JUnit XML was written, set `run_outcome: "timed_out"`, `partial: true`, `fallback_state: "timed out"`, and `no_data_reason: "local run timed out"` when no JUnit was written. Nothing in the user's own checkout is touched, so there is nothing to restore.

## Phase 2: Fetch unresolved comments

Use the same GraphQL query as `pr-review-fixer` to pull every code-level thread, PR-level review, and discussion comment:

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes {
            id isResolved url
            comments(first: 50) {
              nodes { id body author { login } path line createdAt url }
            }
          }
        }
        reviews(first: 50) {
          nodes { id body state author { login } createdAt url }
        }
        comments(first: 100) {
          nodes { id body author { login } createdAt url }
        }
      }
    }
  }
' -f owner=OWNER -f repo=REPO -F pr=$PR_NUM
```

A comment counts as a "Claude review" if **either** the author is `claude[bot]` (the upstream `anthropics/claude-code-action` Action) **or** the body contains the sentinel `<!-- claude-local-review -->` (emitted by the `local-review` agent when pr-pilot runs it locally). Treat both sources uniformly in the rules below.

Filter:
- **Code-level threads**: drop any thread where `isResolved: true`. For each remaining thread, surface the first comment as the top-level entry and any later comments as `replies`. If multiple Claude review comments exist in a thread, keep only the latest as the top-level entry.
- **PR-level reviews**: drop reviews with empty/whitespace bodies. Drop reviews where `state == "APPROVED"` and the body has no actionable feedback. For Claude reviews, keep only the most recent.
- **Discussion comments**: drop pure acknowledgements, CI bot noise, and `pr-review-fixer`'s "PR Review Overview" iteration reports (matched by the `<!-- pr-review-overview -->` sentinel or, for legacy comments, `claude[bot]` author + "PR Review Overview" in the body — they're already in the GitHub UI). For Claude reviews, keep only the latest.

Each surviving item becomes an entry in Phase 6's `unresolved_comments` array. Preserve the comment body **verbatim** — don't rewrite, summarise, or "clean up" reviewer markdown.

If there are no unresolved comments, the section is simply omitted from the output. Don't fabricate one.

## Phase 3: Locate the spec (if any)

Phase 4 review and Phase 5 explanation are both richer when grounded in the design intent, so look for a matching feature spec.

- Use the PR head branch name and title as hints
- Search `specs/` for a folder matching that feature
- If found, read requirements, design, tasks, and decision log
- If not found, skip spec-aware checks and continue

## Phase 4: Launch review agents in parallel (read-only)

Spawn all agents in a single message so they run concurrently. Pass each one the full diff — they need complete context to spot cross-file issues. Each agent **reports** findings only; nothing is fixed.

### Agent 1 — Code reuse

For each change:
- Grep for existing utilities, helpers, and similar patterns. Common locations: utility directories, shared modules, files adjacent to the changes.
- Flag any new function that duplicates existing functionality, and point at the existing one.
- Flag inline logic that could use an existing utility — hand-rolled string manipulation, manual path handling, ad-hoc type guards, custom env checks.

### Agent 2 — Code quality

Look for hacky patterns:
- Redundant state (duplicates existing state, cached values that could be derived, observers that could be direct calls)
- Parameter sprawl (new params bolted onto a function instead of restructuring it)
- Copy-paste with slight variation (near-duplicates that should share an abstraction)
- Leaky abstractions (exposing internals or breaking existing boundaries)
- Stringly-typed code where existing constants, enums, or branded types would fit

### Agent 3 — Efficiency

Look for waste:
- Redundant computations, repeated reads, duplicate API calls, N+1 patterns
- Independent operations run sequentially that could run in parallel
- New blocking work added to startup or per-request hot paths
- Pre-checking file/resource existence before operating (TOCTOU anti-pattern)
- Unbounded data structures, missing cleanup, listener leaks
- Reading whole files when a slice would do, loading everything when filtering for one

### Agent 4 — Spec & docs (only if a spec was found)

- Implementation matches requirements and design; divergences are documented in the decision log
- README, CLAUDE.md, or related docs need updates to reflect the changes
- Tests exist for new/modified behavior and test behavior, not implementation details

Aggregate the findings. Every finding's `status` is `"raised"` in the output — there are no `"fixed"` entries in this skill. Skip false positives and trivial style nits.

## Phase 5: Implementation explanation and insight material

Invoke the `explain-like` skill (Skill tool with `skill="explain-like"`) to produce all three expertise levels — Beginner, Intermediate, Expert. Keep the explanation in memory for the HTML output. Do **not** write it to `specs/{feature_name}/implementation.md` — this skill doesn't modify the repo.

Use the explanation as a validation pass:
- Anything in the spec that can't be cleanly explained → flag as potentially incomplete
- Anything in the explanation that diverges from the design → flag the divergence
- Add a "Completeness Assessment" with what's fully implemented, partially implemented, and missing

In the same pass, extract three pieces of structured content from the diff, commit messages, PR description/body, and (if present) the decision log. This feeds Phase 6 and must be produced even when no spec exists:

1. **Important changes** — the 3–7 commits or hunks that matter most for a reviewer. For each: a one-line title (file or area + verb), why it matters (correctness, performance, API surface, user-visible behaviour, security), and the specific line range or symbol.
2. **Learnings** — patterns, idioms, or APIs introduced in this PR that a reader could reuse elsewhere. One short "takeaway" per item, with a pointer to the example in the diff. Skip pure mechanical changes.
3. **Decision rationale** — for each non-trivial choice, capture the reason. Source order: (a) decision log entries that match the PR, (b) PR description, (c) commit message bodies, (d) inline code comments added in the diff, (e) inferred from the diff. Mark inferred entries explicitly as `inferred`. If a decision is non-trivial but no rationale can be found anywhere, list it under "Open questions for the author" rather than inventing one.

## Phase 6: Generate the overview HTML

Render `{repo-root}/pr-overview.html` (overwrite if it exists) using the shared renderer script. Do **not** hand-write the HTML — assemble a JSON description and invoke the script. The same renderer is used by `pre-push-review` and `pr-review-html`; keep template/palette changes in the script, not duplicated across skills.

**Script:** `~/.claude/scripts/build_review_html.py`.

### Step 1: Write per-file diff fragments

For each changed file, write its diff from the pinned SHA to `$INPUTS/<name>.txt`: `git diff "$MERGE_BASE" "$SHA" -- <path>` with a clone, or the compare API's `files[].patch` without one (a file the API gave no patch for stays a missing fragment). Keep filenames simple (e.g. `diff-services-foo.txt`); the JSON references them by name.

### Step 1b: Baseline, blast radius, and classification

**Baseline** — test results for the merge base, used for new/removed tests and the overall coverage delta:

```bash
gh run list -R <owner>/<repo> --branch <baseRefName> --status success --limit 30 --json databaseId,headSha,url
```

The first candidate whose `headSha` equals `$MERGE_BASE` or is its ancestor wins. With a clone: `git merge-base --is-ancestor <headSha> "$MERGE_BASE"`, treating exit status 128 (commit not present locally) as "skip this candidate". Without a clone: `gh api -R <owner>/<repo> repos/<owner>/<repo>/compare/<headSha>...$MERGE_BASE` with `status` of `identical` or `ahead`. Never use a run later than the merge base — tests added on the base branch since would show as removed. Download and sniff the winner's artifacts exactly as in Phase 1b (same size cap, same content sniffing, same `<run_id>-<artifact>--<basename>` naming) and reference them as `baseline_junit` and `baseline_coverage`, with `baseline_provenance` naming the run. A winning run with no usable artifacts ends the search: `baseline_provenance: null`, and new/removed tests fall back to `diff-tests.json` below.

**Blast radius** — skip this when Phase 1b's worktree run already wrote `$INPUTS/diagram.json`. Otherwise run without `--tools` (there is no checkout to run a dependency tool in):

```bash
python3 ~/.claude/scripts/blast_radius.py --repo . --snapshot "$SHA" --base "$MERGE_BASE" --out "$INPUTS"          # with a clone
python3 ~/.claude/scripts/blast_radius.py --remote <owner>/<repo> --snapshot "$SHA" --base "$MERGE_BASE" --out "$INPUTS"   # without one
```

With a clone the script reads both trees from the fetched git objects, never from the working tree, so it works for fork PRs too. `--remote` reads them through the trees and blobs API, capped at 500 blob calls; past the cap the dependents column is marked partial. Both forms write `$INPUTS/diagram.json` and `$INPUTS/diff-tests.json`; reference them by file name and never transcribe them into the JSON.

**Classification** — the change is `docs-only` when every changed file is documentation (`.md`, `.rst`, `.adoc`, anything under a `docs/` directory), a `README`, `CHANGELOG`, `LICENSE`, `CONTRIBUTING`, or `CODEOWNERS` file with any extension, an image, a lockfile, or an editor/VCS dotfile such as `.gitignore`. Anything else — CI workflows, build configuration, dependency manifests, `.txt` files elsewhere — makes it `code`.

### Step 2: Assemble `overview.json`

Schema (every top-level key is optional except `repo` and `files` — empty sections are dropped from the body and TOC):

```jsonc
{
  "repo":      {"name": "myrepo", "path": "/abs/path",
                "branch": "feature/x", "remote": "origin/main"},
  "title":     "PR overview: #123 — Add foo",
  "subtitle":  "<html> PR #123 by @author · merging feature/x → main · <a href=\"<pr-url>\">view on GitHub</a>",
  "metrics":   [{"label": "PR", "value": "#123"},
                {"label": "author", "value": "@someone"},
                {"label": "head → base", "value": "feature/x → main"},
                {"label": "commits", "value": "5"},
                {"label": "files", "value": "12 touched"},
                {"label": "lines", "value": "+820 / -94"},
                {"label": "unresolved", "value": "3 comments"}],

  "verdict":   {"label": "Ready to merge",
                "tone":  "success",          // success | warning | error
                "detail": "<html> one-paragraph justification"},

  "at_a_glance": ["<html> what this PR does in plain English", "..."],

  "pr_description": {                         // shown verbatim — the author's framing
    "author":     "@someone",
    "url":        "https://github.com/.../pull/123",
    "created_at": "2026-05-16",
    "body":       "raw PR body from `gh pr view --json body`, passed UNMODIFIED"
  },

  "explanation": {                            // from explain-like (Phase 5)
    "beginner":     "<html> What Changed / Why It Matters / Key Concepts",
    "intermediate": "<html> Architecture / Patterns / Trade-offs",
    "expert":       "<html> Deep dive / Architecture impact / Edge cases"
  },

  "commits": [{"sha": "abc1234", "subject": "feat: foo", "author": "Name", "date": "2026-05-16"}],

  "important_changes": [                      // from Phase 5, 3-7 items
    {
      "title":  "services/foo: new retry policy",
      "file":   "services/foo.go",
      "why":    "Why this matters for the reviewer.",
      "what":   "services/foo.go:88-142",
      "takeaway": "What a reader can learn from this — reusable insight.",
      "rationale": "Why this approach was chosen.",
      "rationale_inferred": false
      // OR: "rationale_unknown": true
    }
  ],

  "decisions": [
    {"title": "Pin tokio version.",
     "body":  "<html> body, may include <code>…</code>",
     "inferred": false}
  ],

  "findings": [                               // from Phase 4 — all status: "raised"
    {"severity": "major", "area": "services/foo concurrency",
     "finding": "...", "resolution": "Suggested approach — left for the author to decide.",
     "status": "raised"}
  ],

  "unresolved_comments": [                    // from Phase 2 — verbatim reviewer text
    {
      "author":     "@reviewer",
      "type":       "code",                   // code | review | discussion
      "path":       "services/foo.go",         // only for type=code
      "line":       88,                        // only for type=code
      "body":       "raw markdown comment body, passed UNMODIFIED",
      "url":        "https://github.com/.../pull/123#discussion_r1234567",
      "created_at": "2026-05-16",
      "replies":    [                          // optional; later comments in the same thread
        {"author": "@author", "body": "...", "created_at": "2026-05-16"}
      ]
    }
  ],

  "double_check": [{"title": "Migration ordering.", "body": "<html> body"}],

  "files": [
    {"path": "services/foo.go", "badge": "Modified", "stat": "+140 / -22",
     "diff_file": "diff-services-foo.txt"}
  ],

  "change_classification": "code",            // from Step 1b: code | docs-only
  "diagram_file": "diagram.json",             // written by blast_radius.py, relative to $INPUTS

  "tests": {                                  // from Phase 1b and Step 1b; present for every code change,
    "provenance": {                           // with no_data_reason set when nothing could be collected
      "source":   "ci",                       // ci | local (local = the worktree fallback ran)
      "run_ids":  [123], "run_urls": ["https://github.com/.../actions/runs/123"],   // CI
      "timestamp": "2026-09-04T10:22:00+10:00",                                     // local
      "snapshot": {"sha": "<SHA>", "dirty": false},
      "ci_state": "artifacts usable",         // no run | run in progress or queued | run failed before upload |
                                              // artifacts expired | artifacts absent | artifacts usable
      "fallback_state": "not needed"          // not needed | ran | blocked by fork PR | blocked by no local clone |
    },                                        // blocked by run in progress | timed out
    "baseline_provenance": {"source": "ci", "run_id": 120,  // or null
                            "run_url": "https://github.com/.../actions/runs/120", "sha": "<headSha>"},
    "coverage_scope": "project-configured",   // project-configured for CI and tiers 1-2; repository for the ecosystem recipe
    "run_outcome": "passed",                  // passed | failed | timed_out | not_run (CI source: not_run)
    "partial": false,                         // true when a fallback timeout cut the run short
    "junit":    ["123-test-results-ubuntu--junit.xml"],       // file names under $INPUTS
    "coverage": ["123-test-results-ubuntu--coverage.out"],
    "baseline_junit":    ["120-test-results-ubuntu--junit.xml"],
    "baseline_coverage": ["120-test-results-ubuntu--coverage.out"],
    "path_map": {"strip": null, "prepend": null},   // only when suffix matching cannot resolve coverage paths
    "jobs":      [{"run_id": 123, "name": "test (ubuntu)", "outcome": "success", "url": "…"}],
    "artifacts": [{"name": "test-results-ubuntu", "run_id": 123,
                   "junit": ["123-test-results-ubuntu--junit.xml"],
                   "coverage": ["123-test-results-ubuntu--coverage.out"],
                   "job": "test (ubuntu)"}],  // omit job when attribution failed
    "pending_runs": [{"run_id": 124, "name": "integration", "status": "in_progress", "url": "…"}],
    "skipped_artifacts": [{"name": "build-output", "size_in_bytes": 412000000}],
    "run_touched_files": [],                  // always empty here: the fallback runs in a worktree
    "diff_tests_file": "diff-tests.json",     // written by blast_radius.py; used when there is no baseline
    "no_data_reason": null                    // no tests found | runner not detected | required tool missing |
  },                                          // local run failed | local run timed out | ci

  "publish_metadata": {
    "title":    "PR #123 — Add foo (overview)",
    "repoUrl":  "https://github.com/owner/repo",
    "pr":       123,
    "severity": "suggestions",
    "summary":  "1-3 sentence headline finding shown in the feed reader."
  }
}
```

`no_data_reason: "ci"` tells the renderer to word the no-data card from `ci_state` and `fallback_state` (adding that the workflow must upload a JUnit XML artifact when the state is `no run`, `artifacts absent`, or `artifacts expired`). With `change_classification: "docs-only"` the Tests card, Tests section, and diagram are all omitted, whatever else is present.

**Rendering contract** (implemented by the script — informational, you don't enforce it):
- Pass-through HTML fields: `subtitle`, `at_a_glance` items, `verdict.detail`, every `explanation` panel, `decisions[].body`, `double_check[].body`. Write actual HTML.
- All other fields are HTML-escaped automatically. Write plain text.
- `pr_description.body` and `unresolved_comments[].body` are HTML-escaped and rendered in a `pre-wrap` monospace block — markdown markers (`##`, lists, fenced code) survive on screen as the author wrote them. **Do not** rewrite, trim, or summarise. Verbatim is the whole point.
- Each unresolved comment renders as a warning-bordered card with a type pill (code/review/discussion), author, file:line (if code-level), date, and a "view on GitHub" link. Replies collapse into a `<details>` block.
- Diffs are escaped and coloured by the script's own stylesheet — no external assets. Added lines that have coverage data and zero hits carry an uncovered mark; added lines in files with no coverage data carry none.
- The three-level explanation renders as CSS-only radio-button tabs in Beginner → Intermediate → Expert order.
- Important-change cards show a magenta-bordered **Takeaway** callout and a cyan-bordered **Rationale** callout.
- Findings counts derive from the `status` field; in this skill every finding is `"raised"`.
- `tests` renders a Tests card in the overview grid (pass rate, new tests, diff coverage) and a Tests section: provenance with CI links, CI state and fallback state, availability of run / JUnit / coverage / baseline as independent states, totals with the flaky count, pending runs, one row per job (or per artifact when unattributed), failed tests with messages redacted for secrets and truncated to 500 characters, new and removed tests (by identity with a baseline, by declaration name from `diff_tests_file` without one), a per-file diff-coverage table, the overall coverage delta when both sides have it, skipped artifacts, and any warnings. With no readable results it renders a no-data card from `no_data_reason`, `ci_state`, and `fallback_state`.
- `diagram_file` renders the Blast radius section as inline SVG before the per-file diffs: dependents, changed files, dependencies, grouped by package or directory, changed nodes linked to their diff. Test files leave the side columns, packages with more than 3 expansion-only files collapse, side columns cap at 15 nodes, and a column the script could not derive shows the reason instead. An absent or invalid file warns and omits the section.
- TOC, overview cards, and section anchors are generated automatically. Empty sections vanish.
- `publish_metadata` is emitted as a `<script type="application/json" id="review-meta">` block in `<head>`.

### Step 3: Invoke the script

```bash
python3 ~/.claude/scripts/build_review_html.py \
  --data    "$INPUTS/overview.json" \
  --output  {repo-root}/pr-overview.html \
  --diff-dir "$INPUTS"
```

Always pass `--diff-dir` explicitly; every file the JSON references (fragments, JUnit, coverage, baseline, `diagram.json`, `diff-tests.json`) is resolved against it. The script prints the output path on success. Surface that path to the user so they can open it in a browser.

**Error handling.** Missing diff fragments show as `(diff fragment 'name.txt' missing)` placeholders. A test, coverage, or diagram input that is missing, malformed, not UTF-8, over 50 MB, or XML with a `DOCTYPE` prints a `warning:` line naming the file, is listed in the Tests section, and the rest of the page still renders with exit status 0. Only an unreadable `overview.json` exits non-zero.

**Severity floor.** When a `tests` block is present and the change is not docs-only, the script's last two stderr lines are `summary coverage: matched=N unmatched=N` and `summary tests: passed=N failed=N errored=N skipped=N flaky=N` (head JUnit only, every job aggregated). Grep stderr for the `summary tests:` prefix. If `failed` or `errored` is non-zero: set `verdict.tone` to `warning` unless it is already `error`, prepend the failure count to `verdict.detail` (e.g. "3 failing tests — "), raise `publish_metadata.severity` to `needs-changes` unless it is already `blocking`, and run the script again to the same output path. When the line is absent there is no test data and no floor applies. Flaky tests and coverage values never change the verdict or severity.

### When to edit the renderer vs the SKILL.md

- **Edit the renderer** (the `~/.claude/scripts/review_html/` package; `build_review_html.py` is only the command line) when you need a new card, callout colour, layout tweak, or theme adjustment. The Prism Dark palette lives in `review_html/css.py`; section markup in `sections.py`, the Tests section in `tests_section.py`, the diagram in `diagram.py`. Changes there are shared with `pre-push-review` and `pr-review-html`; `make test` in the agentic-coding repo covers them.
- **Edit this SKILL.md** when you change the JSON contract, the output location, or phase semantics specific to PR overviews.

### Populating `publish_metadata`

Always populate this field. Mapping rules:

- `title`: human-readable, typically the PR title with `(overview)` suffix.
- `repoUrl`: the PR's repo URL (from `gh pr view --json url` or `git remote get-url origin`).
- `pr`: the PR number as an integer. **Do not** also set `branch`.
- `severity`: derive from the findings and the unresolved-comments count — no findings or unresolved comments → `lgtm`; nits or low-stakes unresolved threads only → `suggestions`; major findings or substantive unresolved threads → `needs-changes`; blocking/security/correctness issues → `blocking`. Failing or errored tests floor it at `needs-changes` (Step 3).
- `summary`: 1–3 sentences leading with the headline takeaway (e.g. "3 unresolved threads, all on error handling in foo.go").

## Phase 7: Publish

Check whether the `pulsar` binary is on PATH (`command -v pulsar`). If it is, invoke `pulsar publish <path-to-html>` — the binary validates the metadata block, normalises the repo URL, moves the file into `$HOME/CodeReviews/YYYY-MM/`, and deletes the source. Surface the archived path in Phase 8 instead of the source path. Treat a non-zero exit code as a hard error and surface the stderr message verbatim. If `pulsar` is not on PATH, skip this phase silently.

## Phase 8: Summary

End with a short verdict for the user: **Looks good**, **Worth a closer look** (with the top 2–3 findings), or **Blocking concerns** (with the must-address list). Mention the unresolved-comment count and link to the HTML output (or the archived path returned by Phase 7 if publish ran).

This skill never pushes, commits, merges, or resolves threads — surface what's there and let the user decide what to do next. If Phase 1b ran the worktree fallback, say so, and if it was blocked, say why (fork PR, no local clone, run in progress).
