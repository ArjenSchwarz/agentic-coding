---
name: pr-review-html
description: Pull a PR from GitHub, run parallel review agents (code reuse, quality, efficiency, spec adherence), apply local fixes, and write a self-contained HTML review page to the repo root. Use whenever the user wants to review a PR before merging or asks to "review PR <number>", "look at this PR", "give me an HTML review of PR X", or wants a browseable artifact for a GitHub pull request — even if they don't explicitly say "HTML".
---

# PR Review HTML

Fetch a GitHub PR, review it through multiple specialized agents, and produce a self-contained HTML review at `pr-review.html` in the repo root so the user can read it in a browser before merging.

## Phase 1: Fetch the PR

Resolve which PR to review, in this order:
- An explicit number, URL, or branch name from the user
- Otherwise the PR for the current branch via `gh pr view --json number`

Pull what you need to review:
- `gh pr view <pr> --json number,title,author,baseRefName,headRefName,headRefOid,isCrossRepository,body,url,state,commits,files,createdAt`
- `gh pr diff <pr>` for the unified diff the review agents read (Phase 7 regenerates per-file diffs from the working tree after fixes)

Record `headRefOid` (the head SHA), `isCrossRepository` (true for a fork PR), and `baseRefName`; Phases 5 and 7 use them. Note `<owner>/<repo>` from `url` — every `gh api` and `gh run` call in this skill carries `-R <owner>/<repo>`, and list endpoints use `--paginate`.

If the user isn't on the PR branch, run `gh pr checkout <pr>` so any fixes land on the right local branch. If the working tree is dirty, stop and ask before checking out — silently switching branches risks losing work. After checkout, `git fetch origin <baseRefName>` and record `MERGE_BASE=$(git merge-base origin/<baseRefName> HEAD)`; the diffs, the diagram, and the baseline lookup all compare against it.

Phases 4 and 5 execute the branch's install scripts and tests on this machine, with your environment and credentials. That applies to fork PRs too: this skill checks out and runs whatever PR it is asked to review.

Keep the PR `body`, `author`, `createdAt`, and `url` from the `gh pr view` JSON — these flow into Phase 7's `pr_description` section so the reader can see the author's framing verbatim.

Show the user which PR you're about to review (number, title, author, head → base, commit count, fork or not) before doing the heavier work — it's a cheap sanity check that catches a wrong PR number early.

**Working directory.** Every generated input — diff fragments, JUnit and coverage files, the diagram, the review JSON itself — lives in `$INPUTS`, outside the working tree so nothing lands in `git status`:

```bash
INPUTS="${CLAUDE_JOB_DIR:-$(mktemp -d)}/review-inputs"; mkdir -p "$INPUTS"
```

Both `$CLAUDE_JOB_DIR` and `mktemp -d` yield absolute paths; never use a relative one, as later steps run in subshells where it would resolve into the wrong directory.

## Phase 2: Locate the spec (if any)

Phase 4 review and Phase 6 explanation are both richer when grounded in the design intent, so look for a matching feature spec.

- Use the PR head branch name and title as hints
- Search `specs/` for a folder matching that feature
- If found, read requirements, design, tasks, and decision log
- If not found, skip spec-aware checks and continue

## Phase 3: Launch review agents in parallel

Spawn all agents in a single message so they run concurrently. Pass each one the full diff — they need complete context to spot cross-file issues, and re-fetching it per agent wastes time.

### Agent 1 — Code reuse

For each change:
- Grep for existing utilities, helpers, and similar patterns. Common locations: utility directories, shared modules, files adjacent to the changes.
- Flag any new function that duplicates existing functionality, and suggest the existing one.
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
- Pre-checking file/resource existence before operating (TOCTOU anti-pattern) — operate directly and handle the error
- Unbounded data structures, missing cleanup, listener leaks
- Reading whole files when a slice would do, loading everything when filtering for one

### Agent 4 — Spec & docs (only if a spec was found)

- Implementation matches requirements and design; divergences are documented in the decision log
- README, CLAUDE.md, or related docs need updates to reflect the changes
- Tests exist for new/modified behavior and test behavior, not implementation details

## Phase 4: Fix issues locally

Aggregate the agent findings and fix them on the checked-out PR branch. The user reviews the HTML and decides what to do with the fixes — don't push or commit them automatically. They might want to amend, squash, or open a discussion before anything lands.

- Don't modify test files unless a test is genuinely wrong. If a refactor would force test changes, the refactor itself is suspect — reconsider before changing tests.
- Skip false positives or trivial nits without debate. Style preferences aren't always worth a fix.

## Phase 5: Verify

The verification run is also the source of the page's test results, so choose a command that emits JUnit XML before running anything, and run it once.

### Choose the command

Read `~/.claude/scripts/ecosystems.json`. The language row is the one whose `extensions` cover the most changed files; the runner within it is the first whose `detect` rule matches (`files` globs at the repo root, or top-level `package_json_keys` in `package.json`). Then, reading text only and executing nothing, take the first tier that applies:

1. **Makefile target.** A target whose literal recipe lines (read from the Makefile — never `make -n`, which still expands `$(shell …)` and runs `+` lines) contain one of the runner's `junit_flags`. Pass over a target whose output path is a `$(VAR)` reference you cannot read. Run the target and copy the outputs the recipe names into `$INPUTS`.
2. **Project instructions.** A command in CLAUDE.md or the README described as the test command, if it contains such a flag.
3. **Ecosystem recipe.** The runner's `recipe` with `{junit}`, `{coverage}`, and `{inputs}` replaced by absolute paths under `$INPUTS`, its `env` exported, and any `config_files` templates written under `$INPUTS` first. Every binary in `requires` must be on PATH; a missing one records `no_data_reason: "required tool missing"`. No row, or no runner whose `detect` rule matches, records `runner not detected`. Read the row's `notes` — they say where the coverage file lands, which extra JUnit files appear, and what the install line assumes.

A Makefile target or project command that emits nothing structured is passed over in favour of the next tier, not run as a second suite. `coverage_scope` is `repository` for tier 3 and `project-configured` for tiers 1 and 2; the page shows it.

### Run once

- **Before:** record `git status --porcelain -z` and copy every dirty tracked file to `$INPUTS/pre-run/<path>` — those are the Phase 4 fixes and must survive.
- **Run** the chosen command in one Bash call with `timeout: 600000` (the tool's maximum; it covers dependency installation and the tests) with every output under `$INPUTS`. The exit status becomes `run_outcome` (`passed` or `failed`). Run linters and validators per project config as well.
- **After:** for each tracked file whose content differs from before, restore a file that was clean pre-run with `git checkout -- <path>` and copy a file that was dirty pre-run back from `$INPUTS/pre-run/`. Untracked files that appeared outside `$INPUTS` are reported, never deleted. List touched and appeared paths in `tests.run_touched_files`. Never use `git stash` — it would carry away the fixes the run exists to verify.
- **On timeout:** keep whatever JUnit XML was written, set `run_outcome: "timed_out"` and `partial: true`, and add "fix verification incomplete: test run timed out" to `verdict.detail`.

If a test fails, treat it as a regression in the fix — investigate and revert/adjust rather than editing the test to make it pass. If you re-run after adjusting, repeat the before/after steps; the last run is the one the page reports.

## Phase 6: Implementation explanation and insight material

Invoke the `explain-like` skill (Skill tool with `skill="explain-like"`) to produce all three expertise levels — Beginner, Intermediate, Expert. If a spec was found in Phase 2, write the explanation to `specs/{feature_name}/implementation.md`; otherwise keep it in memory for the HTML output only.

Use the explanation as a validation pass:
- Anything in the spec that can't be cleanly explained → flag as potentially incomplete
- Anything in the explanation that diverges from the design → flag the divergence
- Add a "Completeness Assessment" with what's fully implemented, partially implemented, and missing

In the same pass, extract three pieces of structured content from the diff, commit messages, PR description/body, and (if present) the decision log. This feeds Phase 7 and must be produced even when no spec exists:

1. **Important changes** — the 3–7 commits or hunks that matter most for a reviewer. For each: a one-line title (file or area + verb), why it matters (correctness, performance, API surface, user-visible behaviour, security), and the specific line range or symbol.
2. **Learnings** — patterns, idioms, or APIs introduced in this PR that a reader could reuse elsewhere. One short "takeaway" per item, with a pointer to the example in the diff. Skip pure mechanical changes.
3. **Decision rationale** — for each non-trivial choice, capture the reason. Source order: (a) decision log entries that match the PR, (b) PR description, (c) commit message bodies, (d) inline code comments added in the diff, (e) inferred from the diff. Mark inferred entries explicitly as `inferred`. If a decision is non-trivial but no rationale can be found anywhere, list it under "Open questions for the author" rather than inventing one.

## Phase 7: Generate the review HTML

Render `{repo-root}/pr-review.html` (overwrite if it exists) using the shared renderer script. Do **not** hand-write the HTML — assemble a JSON description and invoke the script. The same renderer is used by `pre-push-review`; keep template/palette changes in the script, not duplicated across skills.

**Script:** `~/.claude/scripts/build_review_html.py`.

### Step 1: Write per-file diff fragments

Diffs come from the working tree after the fixes, not from `gh pr diff`, so the coverage marks land on the lines the reader sees. For each changed file (`git diff --name-status -M $MERGE_BASE`), write `git diff $MERGE_BASE -- <path>` to `$INPUTS/<name>.txt`. Files listed by `git ls-files --others --exclude-standard -z` are untracked additions: write `git diff --no-index /dev/null <path>` for them (exit status 1 is normal) and badge them `Added`. Keep filenames simple (e.g. `diff-services-foo.txt`); the JSON references them by name.

### Step 1b: Baseline, blast radius, and classification

**Baseline** — test results for the merge base, used for new/removed tests and the overall coverage delta:

```bash
gh run list -R <owner>/<repo> --branch <baseRefName> --status success --limit 30 --json databaseId,headSha,url
```

The first candidate whose `headSha` equals `$MERGE_BASE` or is its ancestor wins: `git merge-base --is-ancestor <headSha> $MERGE_BASE`, treating exit status 128 (commit not present locally) as "skip this candidate". Never use a run later than the merge base — tests added on the base branch since would show as removed. For the winner, list its artifacts with `gh api -R <owner>/<repo> --paginate repos/<owner>/<repo>/actions/runs/<id>/artifacts`, skip any with `expired: true` or `size_in_bytes` over 100 MB, download the rest with `gh run download <id> -R <owner>/<repo> -n <artifact> -D "$INPUTS/artifacts/<id>/<artifact>"`, and sniff the files by content: JUnit is XML whose root is `testsuites` or `testsuite`; Cobertura is XML rooted at `coverage`; lcov starts with `TN:` or `SF:`; coverprofile starts with `mode: `. Copy recognised files into `$INPUTS` as `<run_id>-<artifact>--<basename>` and reference them as `baseline_junit` and `baseline_coverage`, with `baseline_provenance` naming the run. A winning run with no usable artifacts ends the search: `baseline_provenance: null`, and new/removed tests fall back to `diff-tests.json` below.

**Blast radius** — run after Phase 5 so the working tree holds the fixes:

```bash
python3 ~/.claude/scripts/blast_radius.py --repo . --snapshot working-tree --base "$MERGE_BASE" --tools --out "$INPUTS"
```

This writes `$INPUTS/diagram.json` (the one-hop dependency graph) and `$INPUTS/diff-tests.json` (test declarations added and removed in changed test files). Reference both by file name; never transcribe them into the JSON.

**Classification** — the change is `docs-only` when every changed file is documentation (`.md`, `.rst`, `.adoc`, anything under a `docs/` directory), a `README`, `CHANGELOG`, `LICENSE`, `CONTRIBUTING`, or `CODEOWNERS` file with any extension, an image, a lockfile, or an editor/VCS dotfile such as `.gitignore`. Anything else — CI workflows, build configuration, dependency manifests, `.txt` files elsewhere — makes it `code`.

### Step 2: Assemble `review.json`

Schema (every top-level key is optional except `repo` and `files` — empty sections are dropped from the body and TOC):

```jsonc
{
  "repo":      {"name": "myrepo", "path": "/abs/path",
                "branch": "feature/x", "remote": "origin/main"},
  "title":     "PR review: #123 — Add foo",
  "subtitle":  "<html> PR #123 by @author · merging feature/x → main · <a href=\"<pr-url>\">view on GitHub</a>",
  "metrics":   [{"label": "PR", "value": "#123"},
                {"label": "author", "value": "@someone"},
                {"label": "head → base", "value": "feature/x → main"},
                {"label": "commits", "value": "5"},
                {"label": "files", "value": "12 touched"},
                {"label": "lines", "value": "+820 / -94"}],

  "verdict":   {"label": "Ready to merge",
                "tone":  "success",          // success | warning | error
                "detail": "<html> one-paragraph justification"},

  "at_a_glance": ["<html> what this PR does in plain English", "..."],

  "pr_description": {                         // shown verbatim — the author's framing
    "author":     "@someone",                  // optional, rendered in the section header
    "url":        "https://github.com/.../pull/123",   // optional, wraps author as link
    "created_at": "2026-05-16",                // optional, free-form display string
    "body":       "raw PR body from `gh pr view --json body`, passed UNMODIFIED"
  },

  "explanation": {                            // from explain-like (Phase 6)
    "beginner":     "<html> What Changed / Why It Matters / Key Concepts",
    "intermediate": "<html> Architecture / Patterns / Trade-offs",
    "expert":       "<html> Deep dive / Architecture impact / Edge cases"
  },

  "commits": [{"sha": "abc1234", "subject": "feat: foo", "author": "Name", "date": "2026-05-16"}],

  "important_changes": [                      // from Phase 6, 3-7 items
    {
      "title":  "services/foo: new retry policy",
      "file":   "services/foo.go",
      "why":    "Why this matters for the reviewer.",
      "what":   "services/foo.go:88-142",
      "takeaway": "What a reader can learn from this — reusable insight.",
      "rationale": "Why this approach was chosen.",
      "rationale_inferred": false              // optional; appends a muted disclaimer
      // OR: "rationale_unknown": true         // renders an Open Question callout
    }
  ],

  "decisions": [                              // every non-trivial decision, not only important-change ones
    {"title": "Pin tokio version.",
     "body":  "<html> body, may include <code>…</code>",
     "inferred": false}
  ],

  "findings": [                               // from Phase 3 / Phase 4
    {"severity": "major", "area": "services/foo concurrency",
     "finding": "...", "resolution": "...", "status": "fixed"}    // status: fixed | skipped
  ],

  "double_check": [{"title": "Migration ordering.", "body": "<html> body"}],

  "files": [
    {"path": "services/foo.go", "badge": "Modified", "stat": "+140 / -22",
     "diff_file": "diff-services-foo.txt"}    // OR "diff": "<inline diff text>"
  ],

  "change_classification": "code",            // from Step 1b: code | docs-only
  "diagram_file": "diagram.json",             // written by blast_radius.py, relative to $INPUTS

  "tests": {                                  // from Phase 5 and Step 1b; present for every code change,
    "provenance": {                           // with no_data_reason set when nothing could be collected
      "source":    "local",
      "timestamp": "2026-09-04T10:22:00+10:00",
      "snapshot":  {"sha": "<headRefOid>", "dirty": true}   // dirty once fixes are applied
    },
    "baseline_provenance": {"source": "ci", "run_id": 120,  // or null
                            "run_url": "https://github.com/.../actions/runs/120", "sha": "<headSha>"},
    "coverage_scope": "repository",           // repository (tier 3) | project-configured (tiers 1-2)
    "run_outcome": "passed",                  // passed | failed | timed_out | not_run
    "partial": false,                         // true when a timeout cut the run short
    "junit":    ["junit.xml"],                // file names under $INPUTS
    "coverage": ["coverage.out"],
    "baseline_junit":    ["120-test-results--junit.xml"],
    "baseline_coverage": ["120-test-results--coverage.out"],
    "path_map": {"strip": null, "prepend": null},   // only when suffix matching cannot resolve coverage paths
    "run_touched_files": [],                  // from the Phase 5 restore step
    "diff_tests_file": "diff-tests.json",     // written by blast_radius.py; used when there is no baseline
    "no_data_reason": null                    // no tests found | runner not detected | required tool missing |
  },                                          // local run failed | local run timed out

  "publish_metadata": {                       // always populate (see Phase 8).
    "title":    "PR #123 — Add foo",
    "repoUrl":  "https://github.com/owner/repo",
    "pr":       123,                          // use `pr` here — exactly one of pr or branch.
    "severity": "needs-changes",              // lgtm | suggestions | needs-changes | blocking
    "summary":  "1-3 sentence headline finding shown in the feed reader."
  }
}
```

With `change_classification: "docs-only"` the Tests card, Tests section, and diagram are all omitted, whatever else is present.

**Rendering contract** (implemented by the script — informational, you don't enforce it):
- Pass-through HTML fields: `subtitle`, `at_a_glance` items, `verdict.detail`, every `explanation` panel, `decisions[].body`, `double_check[].body`. Write actual HTML.
- All other fields are HTML-escaped automatically. Write plain text.
- `pr_description.body` is HTML-escaped and rendered in a `pre-wrap` block with monospace styling — markdown markers (`##`, lists, fenced code) and any HTML comments survive on screen as the author wrote them. **Do not** rewrite, trim, or summarise the body; the whole point is verbatim authorial intent.
- Diffs are escaped and coloured by the script's own stylesheet — no external assets. Added lines that have coverage data and zero hits carry an uncovered mark; added lines in files with no coverage data carry none.
- The three-level explanation renders as CSS-only radio-button tabs in Beginner → Intermediate → Expert order.
- Important-change cards show a magenta-bordered **Takeaway** callout and a cyan-bordered **Rationale** callout. `rationale_unknown: true` swaps Rationale for a warning-bordered **Open question**. `rationale_inferred: true` appends `(inferred — not stated by the author)`.
- Findings counts (raised / fixed / skipped) derive from the `status` field.
- `tests` renders a Tests card in the overview grid (pass rate, new tests, diff coverage) and a Tests section: provenance, availability of run / JUnit / coverage / baseline as independent states, totals with the flaky count, failed tests with messages redacted for secrets and truncated to 500 characters, new and removed tests (by identity with a baseline, by declaration name from `diff_tests_file` without one), a per-file diff-coverage table, the overall coverage delta when both sides have it, and any warnings. With no readable results it renders a no-data card from `no_data_reason`.
- `diagram_file` renders the Blast radius section as inline SVG before the per-file diffs: dependents, changed files, dependencies, grouped by package or directory, changed nodes linked to their diff. Test files leave the side columns, packages with more than 3 expansion-only files collapse, side columns cap at 15 nodes. An absent or invalid file warns and omits the section.
- TOC, overview cards, and section anchors are generated automatically. Empty sections vanish.
- `publish_metadata` is emitted as a `<script type="application/json" id="review-meta">` block in `<head>`, JSON-encoded with `</` escaped. Required by `pulsar publish` (see `docs/agent-contract.md` in the pulsar repo); harmless when present, ignored when absent.

### Step 3: Invoke the script

```bash
python3 ~/.claude/scripts/build_review_html.py \
  --data    "$INPUTS/review.json" \
  --output  {repo-root}/pr-review.html \
  --diff-dir "$INPUTS"
```

Always pass `--diff-dir` explicitly; every file the JSON references (fragments, JUnit, coverage, baseline, `diagram.json`, `diff-tests.json`) is resolved against it. The script prints the output path on success. Surface that path to the user so they can open it in a browser.

**Error handling.** Missing diff fragments show as `(diff fragment 'name.txt' missing)` placeholders. A test, coverage, or diagram input that is missing, malformed, not UTF-8, over 50 MB, or XML with a `DOCTYPE` prints a `warning:` line naming the file, is listed in the Tests section, and the rest of the page still renders with exit status 0. Only an unreadable `review.json` exits non-zero.

**Severity floor.** When a `tests` block is present and the change is not docs-only, the script's last two stderr lines are `summary coverage: matched=N unmatched=N` and `summary tests: passed=N failed=N errored=N skipped=N flaky=N` (head JUnit only). Grep stderr for the `summary tests:` prefix. If `failed` or `errored` is non-zero: set `verdict.tone` to `warning` unless it is already `error`, prepend the failure count to `verdict.detail` (e.g. "3 failing tests — "), raise `publish_metadata.severity` to `needs-changes` unless it is already `blocking`, and run the script again to the same output path. When the line is absent there is no test data and no floor applies. Flaky tests and coverage values never change the verdict or severity.

### When to edit the renderer vs the SKILL.md

- **Edit the renderer** (the `~/.claude/scripts/review_html/` package; `build_review_html.py` is only the command line) when you need a new card, callout colour, layout tweak, or theme adjustment. The Prism Dark palette lives in `review_html/css.py`; section markup in `sections.py`, the Tests section in `tests_section.py`, the diagram in `diagram.py`. Changes there are shared with `pre-push-review` and `pr-overview`; `make test` in the agentic-coding repo covers them.
- **Edit this SKILL.md** when you change the JSON contract, the output location, or the upstream phase semantics specific to PR reviews.

### Populating `publish_metadata`

Always populate this field. Mapping rules:

- `title`: human-readable, typically the PR title (e.g. `PR #123 — Add foo`).
- `repoUrl`: the PR's repo URL (from `gh pr view --json url` or `git remote get-url origin`); the binary normalises SSH → HTTPS and strips `.git`.
- `pr`: the PR number as an integer. **Do not** also set `branch` — exactly one is allowed.
- `severity`: derive from the verdict tone and findings — `success` and no major issues → `lgtm`; nits only → `suggestions`; major findings raised → `needs-changes`; blocking/security/correctness issues → `blocking`. Failing or errored tests floor it at `needs-changes` (Step 3).
- `summary`: 1–3 sentences leading with the headline finding (not "I reviewed PR X"). This is the feed-reader description.

## Phase 8: Publish

Check whether the `pulsar` binary is on PATH (`command -v pulsar`). If it is, invoke `pulsar publish <path-to-html>` — the binary validates the metadata block, normalises the repo URL, moves the file into `$HOME/CodeReviews/YYYY-MM/`, and deletes the source. Surface the archived path in Phase 9 instead of the source path. Treat a non-zero exit code as a hard error and surface the stderr message verbatim. If `pulsar` is not on PATH, skip this phase silently.

## Phase 9: Summary

End with a clear verdict: **Ready to merge**, **Needs fixes** (with must-fix list), or **Requires discussion** (with architectural concerns). List what was fixed automatically and what still needs attention. Include the path to the HTML (or the archived path returned by Phase 8 if publish ran). Don't push or merge — that's the user's call.
