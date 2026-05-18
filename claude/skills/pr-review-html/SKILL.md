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
- `gh pr view <pr> --json number,title,author,baseRefName,headRefName,body,url,state,commits,files`
- `gh pr diff <pr>` for the unified diff

If the user isn't on the PR branch, run `gh pr checkout <pr>` so any fixes land on the right local branch. If the working tree is dirty, stop and ask before checking out — silently switching branches risks losing work.

Keep the PR `body`, `author`, `createdAt`, and `url` from the `gh pr view` JSON — these flow into Phase 7's `pr_description` section so the reader can see the author's framing verbatim.

Show the user which PR you're about to review (number, title, author, head → base, commit count) before doing the heavier work — it's a cheap sanity check that catches a wrong PR number early.

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

After fixes:
- Run the project's test suite (use Makefile commands if present)
- Run linters and validators per project config
- If a test fails, treat it as a regression in the fix — investigate and revert/adjust rather than editing the test to make it pass

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

For each changed file in the PR, dump the unified diff to a separate `.txt` file. Use `gh pr diff <pr> -- <path>` or split the full PR diff. Put the fragments in a working directory next to where the JSON will live, e.g. `{repo-root}/.claude/pr-review-diffs/` or `$CLAUDE_JOB_DIR`. Keep filenames simple (e.g. `diff-services-foo.txt`); the JSON references them by name.

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

  "publish_metadata": {                       // always populate (see Phase 8).
    "title":    "PR #123 — Add foo",
    "repoUrl":  "https://github.com/owner/repo",
    "pr":       123,                          // use `pr` here — exactly one of pr or branch.
    "severity": "needs-changes",              // lgtm | suggestions | needs-changes | blocking
    "summary":  "1-3 sentence headline finding shown in the feed reader."
  }
}
```

**Rendering contract** (implemented by the script — informational, you don't enforce it):
- Pass-through HTML fields: `subtitle`, `at_a_glance` items, `verdict.detail`, every `explanation` panel, `decisions[].body`, `double_check[].body`. Write actual HTML.
- All other fields are HTML-escaped automatically. Write plain text.
- `pr_description.body` is HTML-escaped and rendered in a `pre-wrap` block with monospace styling — markdown markers (`##`, lists, fenced code) and any HTML comments survive on screen as the author wrote them. **Do not** rewrite, trim, or summarise the body; the whole point is verbatim authorial intent.
- Diffs are escaped and dropped into `<pre><code class="language-diff">…</code></pre>` with highlight.js, then restyled to the Prism Dark green/red tokens.
- The three-level explanation renders as CSS-only radio-button tabs in Beginner → Intermediate → Expert order.
- Important-change cards show a magenta-bordered **Takeaway** callout and a cyan-bordered **Rationale** callout. `rationale_unknown: true` swaps Rationale for a warning-bordered **Open question**. `rationale_inferred: true` appends `(inferred — not stated by the author)`.
- Findings counts (raised / fixed / skipped) derive from the `status` field.
- TOC, overview cards, and section anchors are generated automatically. Empty sections vanish.
- `publish_metadata` is emitted as a `<script type="application/json" id="review-meta">` block in `<head>`, JSON-encoded with `</` escaped. Required by `pulsar publish` (see `docs/agent-contract.md` in the pulsar repo); harmless when present, ignored when absent.

### Step 3: Invoke the script

```bash
python3 ~/.claude/scripts/build_review_html.py \
  --data    /path/to/review.json \
  --output  {repo-root}/pr-review.html \
  --diff-dir /path/to/diff-fragments     # defaults to the JSON file's directory
```

The script prints the output path on success. Surface that path to the user so they can open it in a browser. Missing diff fragments degrade gracefully — they show as `(diff fragment 'name.txt' missing)` placeholders, so the rest of the review remains usable.

### When to edit the script vs the SKILL.md

- **Edit the script** (`~/.claude/scripts/build_review_html.py`) when you need a new card, callout colour, layout tweak, or theme adjustment. The Prism Dark palette lives in the `CSS` constant inside the script. Changes there are shared with `pre-push-review`.
- **Edit this SKILL.md** when you change the JSON contract, the output location, or the upstream phase semantics specific to PR reviews.

### Populating `publish_metadata`

Always populate this field. Mapping rules:

- `title`: human-readable, typically the PR title (e.g. `PR #123 — Add foo`).
- `repoUrl`: the PR's repo URL (from `gh pr view --json url` or `git remote get-url origin`); the binary normalises SSH → HTTPS and strips `.git`.
- `pr`: the PR number as an integer. **Do not** also set `branch` — exactly one is allowed.
- `severity`: derive from the verdict tone and findings — `success` and no major issues → `lgtm`; nits only → `suggestions`; major findings raised → `needs-changes`; blocking/security/correctness issues → `blocking`.
- `summary`: 1–3 sentences leading with the headline finding (not "I reviewed PR X"). This is the feed-reader description.

## Phase 8: Publish

Check whether the `pulsar` binary is on PATH (`command -v pulsar`). If it is, invoke `pulsar publish <path-to-html>` — the binary validates the metadata block, normalises the repo URL, moves the file into `$HOME/CodeReviews/YYYY-MM/`, and deletes the source. Surface the archived path in Phase 9 instead of the source path. Treat a non-zero exit code as a hard error and surface the stderr message verbatim. If `pulsar` is not on PATH, skip this phase silently.

## Phase 9: Summary

End with a clear verdict: **Ready to merge**, **Needs fixes** (with must-fix list), or **Requires discussion** (with architectural concerns). List what was fixed automatically and what still needs attention. Include the path to the HTML (or the archived path returned by Phase 8 if publish ran). Don't push or merge — that's the user's call.
