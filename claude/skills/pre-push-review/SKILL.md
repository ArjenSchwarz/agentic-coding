---
name: pre-push-review
description: Review unpushed commits before pushing to remote repository
---

# Pre-Push Code Review

Review and fix unpushed commits before they reach the remote repository.

## Phase 1: Identify Changes

Determine which commits haven't been pushed to the remote repository. Use `git diff origin/<branch>..HEAD` to get the full diff of unpushed changes. Show the user which commits will be reviewed.

If there is no remote tracking branch yet, diff against `origin/main`.

## Phase 2: Locate Relevant Specifications

Check if there's a spec for the feature being worked on:

- Examine the current branch name for feature indicators
- Look in the specs directory for matching feature folders
- Review all documents in the feature folder: requirements, design, tasks, and decision log
- If no spec exists, proceed with general review only

## Phase 3: Launch Review Agents in Parallel

Use the Agent tool to launch all agents concurrently in a single message. Pass each agent the full diff so it has the complete context.

### Agent 1: Code Reuse Review

For each change:

1. **Search for existing utilities and helpers** that could replace newly written code. Use Grep to find similar patterns elsewhere in the codebase — common locations are utility directories, shared modules, and files adjacent to the changed ones.
2. **Flag any new function that duplicates existing functionality.** Suggest the existing function to use instead.
3. **Flag any inline logic that could use an existing utility** — hand-rolled string manipulation, manual path handling, custom environment checks, ad-hoc type guards, and similar patterns are common candidates.

### Agent 2: Code Quality Review

Review the same changes for hacky patterns:

1. **Redundant state**: state that duplicates existing state, cached values that could be derived, observers/effects that could be direct calls
2. **Parameter sprawl**: adding new parameters to a function instead of generalizing or restructuring existing ones
3. **Copy-paste with slight variation**: near-duplicate code blocks that should be unified with a shared abstraction
4. **Leaky abstractions**: exposing internal details that should be encapsulated, or breaking existing abstraction boundaries
5. **Stringly-typed code**: using raw strings where constants, enums (string unions), or branded types already exist in the codebase

### Agent 3: Efficiency Review

Review the same changes for efficiency:

1. **Unnecessary work**: redundant computations, repeated file reads, duplicate network/API calls, N+1 patterns
2. **Missed concurrency**: independent operations run sequentially when they could run in parallel
3. **Hot-path bloat**: new blocking work added to startup or per-request/per-render hot paths
4. **Unnecessary existence checks**: pre-checking file/resource existence before operating (TOCTOU anti-pattern) — operate directly and handle the error
5. **Memory**: unbounded data structures, missing cleanup, event listener leaks
6. **Overly broad operations**: reading entire files when only a portion is needed, loading all items when filtering for one

### Agent 4: Spec & Documentation Review (only if spec exists)

1. **Spec adherence**: Verify implementation matches requirements and design. Identify divergences. Ensure divergences are documented in the decision log.
2. **Documentation**: Check if README, CLAUDE.md, or other docs need updates to reflect the changes.
3. **Testing gaps**: Verify presence of appropriate tests for new/modified code. Check that tests test behavior, not implementation.

## Phase 4: Fix Issues

Wait for all agents to complete. Aggregate their findings and fix each issue directly.

**Constraints:**

- **Do not modify test files** unless fixing an actual bug (e.g., a test that tests the wrong thing or has a genuine error). Refactoring production code must not require test changes — if it would, reconsider the refactoring approach.
- If a finding is a false positive or not worth addressing, skip it without debate.

## Phase 5: Verify

After all fixes are applied:

1. Run the project's test suite (use Makefile commands if available). All tests must pass.
2. Run linters and validators as specified in project configuration.
3. If any test fails, investigate whether the fix introduced a regression and revert or adjust the fix — do not modify the test to make it pass.

## Phase 6: Generate Implementation Explanation and Insight Material

Use the explain-like skill (invoke the Skill tool with skill="explain-like") to generate explanations of the implementation at all three expertise levels (beginner, intermediate, expert). If a spec was found in Phase 2, write the explanation to `specs/{feature_name}/implementation.md`; otherwise keep it in memory for the HTML output only.

**Use the explanation as a validation mechanism:**

- If any requirement from the spec cannot be clearly explained, flag it as potentially incomplete.
- If the explanation reveals logic that doesn't align with the design, flag it as a divergence.
- Add a "Completeness Assessment" section summarizing: what's fully implemented, what's partially implemented, and what's missing.

**In addition to the three-level explanation, extract the following content from the diff, commit messages, and (if present) the decision log. This material feeds Phase 7 and should be saved into memory even when no spec exists:**

1. **Important changes** — the 3–7 commits or hunks that matter most for a reviewer. For each, record:
   - A one-line title (file or area + verb).
   - Why it matters (correctness, performance, API surface, user-visible behaviour, security).
   - The specific line range or symbol to look at.
2. **Learnings** — patterns, idioms, or APIs introduced in this branch that a reader could reuse elsewhere. Capture each as a short "takeaway" with a pointer to the example in the diff. Skip pure mechanical changes (renames, formatting).
3. **Decision rationale** — for each non-trivial choice, capture the reason. Source order: (a) decision log entries that match the commits, (b) commit message bodies, (c) inline code comments added in the diff, (d) inferred from the diff itself. Mark inferred entries explicitly as `inferred` so the reviewer knows the rationale wasn't stated by the author.

If a decision is non-trivial but no rationale can be found anywhere, list it under "Open questions for the author" rather than fabricating a reason.

## Phase 7: Generate Review HTML

Render a self-contained HTML page using the bundled renderer script. Do **not** hand-write the HTML — assemble a JSON description and invoke the script. The script owns the Prism Dark theme, the overview grid, the three-level explanation tabs, the important-change cards (with Takeaway / Rationale / Open-question callouts), and the diff rendering. Your job is to populate the JSON.

**Script:** `~/.claude/scripts/build_review_html.py`. The same renderer powers `pr-review-html` — keep changes to the template/palette in the script itself, not duplicated across skills.

**Output location** (in priority order, use the first that applies):

1. `specs/{feature_name}/pre-push-review.html` if a matching spec was found in Phase 2
2. `{repo-root}/.claude/pre-push-review.html` if `.claude/` exists
3. `/tmp/pre-push-review-{branch-name}.html`

Overwrite any existing file.

### Step 1: Write per-file diff fragments

For each changed file, dump the unified diff (`git diff $BASE -- <path>` or equivalent) to a separate `.txt` file. Pick a working directory next to where the JSON will live, e.g. `{repo-root}/.claude/review-diffs/` or `$CLAUDE_JOB_DIR`. Keep the filenames simple (e.g. `diff-main.go.txt`); the JSON references them by name.

### Step 2: Assemble `review.json`

Write a JSON file with this shape. Every top-level key is optional except `repo` and `files` — empty sections are omitted from both the body and the TOC.

```jsonc
{
  "repo":      {"name": "myrepo", "path": "/abs/path", "branch": "main", "remote": "origin/main"},
  "title":     "Pre-push review: myrepo",
  "subtitle":  "<html> short blurb under the H1 — pass-through HTML",
  "metrics":   [{"label": "branch", "value": "main"},
                {"label": "commits", "value": "3"},
                {"label": "files", "value": "21 touched"},
                {"label": "lines", "value": "+2700 / -50"}],

  "verdict":   {"label": "Ready to push",
                "tone":  "success",          // success | warning | error
                "detail": "<html> one-paragraph justification"},

  "at_a_glance": ["<html> bullet 1", "<html> bullet 2"],

  "explanation": {                            // from the explain-like skill (Phase 6)
    "beginner":     "<html> What Changed / Why It Matters / Key Concepts",
    "intermediate": "<html> Architecture / Patterns / Trade-offs",
    "expert":       "<html> Deep dive / Architecture impact / Edge cases"
  },

  "commits": [{"sha": "725ae99", "subject": "feat: ...", "author": "Name", "date": "2026-05-16"},
              {"sha": "working-tree", "subject": "Fixes applied in this review", "meta": "free-form trailer"}],

  "important_changes": [                      // from Phase 6, 3-7 items
    {
      "title":  "publish: atomic move with prior-version cleanup",
      "file":   "publish.go",                  // used to build the diff anchor link
      "why":    "Why this matters for the reviewer.",
      "what":   "publish.go:31-108",
      "takeaway": "What a reader can learn from this — reusable insight.",
      "rationale": "Why this approach was chosen.",
      "rationale_inferred": true               // optional; appends a muted disclaimer
      // OR: "rationale_unknown": true         // renders an Open Question callout instead
    }
  ],

  "decisions": [                              // every non-trivial decision, not just important-change ones
    {"title": "Regex over full HTML parser.",
     "body":  "<html> body, may include <code>…</code>",
     "inferred": false}
  ],

  "findings": [                               // from Phase 3 / Phase 4
    {"severity": "major", "area": "serve.go traversal",
     "finding": "...", "resolution": "...", "status": "fixed"}    // status: fixed | skipped
  ],

  "double_check": [{"title": "Concurrent publish.", "body": "<html> body"}],

  "files": [
    {"path": "publish.go", "badge": "Modified", "stat": "+140 / -0",
     "diff_file": "diff-publish.go.txt"}      // OR "diff": "<inline diff text>"
  ],

  "publish_metadata": {                       // always populate (see Phase 8).
    "title":    "Pre-push review: <branch>",
    "repoUrl":  "https://github.com/owner/repo",
    "branch":   "<branch-name>",              // use `branch` here — no PR exists pre-push.
    "severity": "lgtm",                       // lgtm | suggestions | needs-changes | blocking
    "summary":  "1-3 sentence headline finding shown in the feed reader."
  }
}
```

**Rendering contract** the script implements (you don't have to):
- Pass-through HTML fields: `subtitle`, `at_a_glance` items, `verdict.detail`, every `explanation` panel, `decisions[].body`, `double_check[].body`. Write actual HTML here (e.g. `<p>`, `<ul>`, `<code>`).
- Every other field is HTML-escaped automatically. Write plain text, no escaping.
- Diffs are escaped and dropped into `<pre><code class="language-diff">…</code></pre>`; highlight.js paints them and the stylesheet overrides additions/deletions to the Prism Dark green/red tokens.
- The three-level explanation renders as CSS-only radio-button tabs in Beginner → Intermediate → Expert order. The first level present is checked by default.
- Important-change cards render a magenta-bordered Takeaway callout and a cyan-bordered Rationale callout. `rationale_unknown: true` swaps the Rationale for a warning-bordered "Open question" callout. `rationale_inferred: true` appends a muted `(inferred — not stated by the author)`.
- Findings counts (raised / fixed / skipped) are derived from the `status` field.
- The TOC, overview cards, and per-section anchors are generated automatically; sections with no data are dropped.
- `publish_metadata` is emitted as a `<script type="application/json" id="review-meta">` block in `<head>`, JSON-encoded with `</` escaped. Required by `pulsar publish` (see `docs/agent-contract.md` in the pulsar repo); harmless in browsers when present, ignored when absent.

### Step 3: Invoke the script

```bash
python3 ~/.claude/scripts/build_review_html.py \
  --data    /path/to/review.json \
  --output  /path/to/pre-push-review.html \
  --diff-dir /path/to/diff-fragments     # defaults to the JSON file's directory
```

The script prints the output path on success. Surface that path to the user so they can open it in a browser. If the JSON is malformed or a referenced diff fragment is missing, the script still renders the page — missing diffs become a `(diff fragment 'name.txt' missing)` placeholder so the rest of the review remains usable.

### When to edit the script vs the SKILL.md

- **Edit the script** when you need a new card, callout colour, layout tweak, or theme adjustment. The Prism Dark palette lives in the `CSS` constant inside the script.
- **Edit the SKILL.md** when you change the JSON contract, the location-priority logic, or the upstream phase semantics.

### Populating `publish_metadata`

Always populate this field. Mapping rules:

- `title`: human-readable, mirror the H1 (e.g. `Pre-push review: <branch>`).
- `repoUrl`: from `git remote get-url origin`; the binary normalises SSH → HTTPS and strips `.git`.
- `branch`: the current branch name. **Do not** set `pr` for a pre-push review — no PR exists yet.
- `severity`: derive from the verdict tone and findings — `success`/no major findings → `lgtm`; `warning` with only nits → `suggestions`; major findings raised → `needs-changes`; blocking/security/correctness issues → `blocking`.
- `summary`: 1–3 sentences leading with the headline finding (not "I reviewed X"). This is what shows up in the user's feed reader.

## Phase 8: Publish

Check whether the `pulsar` binary is on PATH (`command -v pulsar`). If it is, invoke `pulsar publish <path-to-html>` — the binary validates the metadata block, normalises the repo URL, moves the file into `$HOME/CodeReviews/YYYY-MM/`, and deletes the source. Treat a non-zero exit code as a hard error and surface the stderr message verbatim. If `pulsar` is not on PATH, skip this phase silently.

## Phase 9: Summary

Provide a clear verdict: **Ready to push**, **Needs fixes** (with must-fix list), or **Requires discussion** (with architectural concerns).

List what was fixed automatically and what still needs attention. Include the path to the review HTML from Phase 7 (or the archived path returned by Phase 8 if publish ran).
