---
name: pr-overview
description: Pull a PR from GitHub, run parallel review agents (code reuse, quality, efficiency, spec adherence) in read-only mode, surface unresolved comments, and write a self-contained HTML overview page to the repo root. Use whenever the user wants a read-only summary of a PR before deciding what to do — phrases like "overview of PR X", "summarise this PR", "what's the state of PR X", "give me an HTML overview", or any time they want a browseable artifact without touching the code.
---

# PR Overview

Fetch a GitHub PR, review it through multiple specialized agents (read-only), collect any unresolved comments, and produce a self-contained HTML overview at `pr-overview.html` in the repo root so the user can read it in a browser.

This skill never modifies code, never commits, never pushes, and never resolves comment threads. It only produces an overview. For a workflow that also applies fixes, use `pr-review-html`; for one that addresses reviewer comments, use `pr-review-fixer`.

## Phase 1: Fetch the PR

Resolve which PR to look at, in this order:
- An explicit number, URL, or branch name from the user
- Otherwise the PR for the current branch via `gh pr view --json number`

Pull what you need:
- `gh pr view <pr> --json number,title,author,baseRefName,headRefName,body,url,state,commits,files,createdAt`
- `gh pr diff <pr>` for the unified diff

Do **not** run `gh pr checkout`. This skill is read-only — the user may be on a different branch deliberately, and switching branches risks losing work. If the agents need code context beyond the diff, read files at the PR's `headRefName` via `gh api` rather than checking out.

Keep the PR `body`, `author`, `createdAt`, and `url` from the `gh pr view` JSON — these flow into Phase 6's `pr_description` section so the reader can see the author's framing verbatim.

Show the user which PR you're about to summarise (number, title, author, head → base, commit count) before doing the heavier work — a cheap sanity check that catches the wrong PR number early.

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

For each changed file in the PR, dump the unified diff to a separate `.txt` file. Use `gh pr diff <pr> -- <path>` or split the full PR diff. Put the fragments in a working directory next to where the JSON will live, e.g. `{repo-root}/.claude/pr-overview-diffs/` or `$CLAUDE_JOB_DIR`. Keep filenames simple (e.g. `diff-services-foo.txt`); the JSON references them by name.

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

  "publish_metadata": {
    "title":    "PR #123 — Add foo (overview)",
    "repoUrl":  "https://github.com/owner/repo",
    "pr":       123,
    "severity": "suggestions",
    "summary":  "1-3 sentence headline finding shown in the feed reader."
  }
}
```

**Rendering contract** (implemented by the script — informational, you don't enforce it):
- Pass-through HTML fields: `subtitle`, `at_a_glance` items, `verdict.detail`, every `explanation` panel, `decisions[].body`, `double_check[].body`. Write actual HTML.
- All other fields are HTML-escaped automatically. Write plain text.
- `pr_description.body` and `unresolved_comments[].body` are HTML-escaped and rendered in a `pre-wrap` monospace block — markdown markers (`##`, lists, fenced code) survive on screen as the author wrote them. **Do not** rewrite, trim, or summarise. Verbatim is the whole point.
- Each unresolved comment renders as a warning-bordered card with a type pill (code/review/discussion), author, file:line (if code-level), date, and a "view on GitHub" link. Replies collapse into a `<details>` block.
- Diffs are escaped and dropped into `<pre><code class="language-diff">…</code></pre>` with highlight.js, then restyled to the Prism Dark green/red tokens.
- The three-level explanation renders as CSS-only radio-button tabs in Beginner → Intermediate → Expert order.
- Important-change cards show a magenta-bordered **Takeaway** callout and a cyan-bordered **Rationale** callout.
- Findings counts derive from the `status` field; in this skill every finding is `"raised"`.
- TOC, overview cards, and section anchors are generated automatically. Empty sections vanish.
- `publish_metadata` is emitted as a `<script type="application/json" id="review-meta">` block in `<head>`.

### Step 3: Invoke the script

```bash
python3 ~/.claude/scripts/build_review_html.py \
  --data    /path/to/overview.json \
  --output  {repo-root}/pr-overview.html \
  --diff-dir /path/to/diff-fragments
```

The script prints the output path on success. Surface that path to the user so they can open it in a browser.

### When to edit the script vs the SKILL.md

- **Edit the script** (`~/.claude/scripts/build_review_html.py`) when you need a new card, callout colour, layout tweak, or theme adjustment. Changes there are shared with `pre-push-review` and `pr-review-html`.
- **Edit this SKILL.md** when you change the JSON contract, the output location, or phase semantics specific to PR overviews.

### Populating `publish_metadata`

Always populate this field. Mapping rules:

- `title`: human-readable, typically the PR title with `(overview)` suffix.
- `repoUrl`: the PR's repo URL (from `gh pr view --json url` or `git remote get-url origin`).
- `pr`: the PR number as an integer. **Do not** also set `branch`.
- `severity`: derive from the findings and the unresolved-comments count — no findings or unresolved comments → `lgtm`; nits or low-stakes unresolved threads only → `suggestions`; major findings or substantive unresolved threads → `needs-changes`; blocking/security/correctness issues → `blocking`.
- `summary`: 1–3 sentences leading with the headline takeaway (e.g. "3 unresolved threads, all on error handling in foo.go").

## Phase 7: Publish

Check whether the `pulsar` binary is on PATH (`command -v pulsar`). If it is, invoke `pulsar publish <path-to-html>` — the binary validates the metadata block, normalises the repo URL, moves the file into `$HOME/CodeReviews/YYYY-MM/`, and deletes the source. Surface the archived path in Phase 8 instead of the source path. Treat a non-zero exit code as a hard error and surface the stderr message verbatim. If `pulsar` is not on PATH, skip this phase silently.

## Phase 8: Summary

End with a short verdict for the user: **Looks good**, **Worth a closer look** (with the top 2–3 findings), or **Blocking concerns** (with the must-address list). Mention the unresolved-comment count and link to the HTML output (or the archived path returned by Phase 7 if publish ran).

This skill never pushes, commits, merges, or resolves threads — surface what's there and let the user decide what to do next.
