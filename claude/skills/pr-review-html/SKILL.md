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

## Phase 6: Implementation explanation (if spec exists)

Invoke the `explain-like` skill to generate explanations at multiple expertise levels, written to `specs/{feature_name}/implementation.md`. Use it as a validation pass:
- Anything in the spec that can't be cleanly explained → flag as potentially incomplete
- Anything in the explanation that diverges from the design → flag the divergence
- Add a "Completeness Assessment" with what's fully implemented, partially implemented, and missing

## Phase 7: Generate the review HTML

Always write to `{repo-root}/pr-review.html` (overwrite if it exists). The fixed location makes it predictable — the user can bookmark it, and the next review just refreshes the page.

Required sections:
1. **Header** — PR number, title, author, head → base, PR URL, and the commit list (SHA, subject, author, date)
2. **Summary** — files changed with added/removed line counts
3. **Per-file diffs** — render each file's unified diff with syntax highlighting. Load highlight.js from a CDN (`cdn.jsdelivr.net/gh/highlightjs/cdn-release` with the `diff` language) and call `hljs.highlightAll()`. Wrap each diff in `<pre><code class="language-diff">…</code></pre>` and HTML-escape the content.
4. **How it works** — plain-English of what the changes do, how they fit into existing code, and any new abstractions. Pull from Phase 6's explanation if available.
5. **Key decisions** — notable choices: algorithm picks, trade-offs, alternatives rejected. Summarize relevant decision-log entries if a spec exists.
6. **Review findings** — what the agents flagged in Phase 3 and what was fixed (or skipped, with reason) in Phase 4
7. **Things to double-check** — risky areas, untested paths, follow-ups worth attention before merging

Keep CSS inline and minimal. Monospace for diffs, sans-serif for prose. Wrap each per-file diff in `<details>` so long reviews stay navigable.

Print the absolute path after writing so the user can open it in a browser.

## Phase 8: Summary

End with a clear verdict: **Ready to merge**, **Needs fixes** (with must-fix list), or **Requires discussion** (with architectural concerns). List what was fixed automatically and what still needs attention. Include the path to the HTML. Don't push or merge — that's the user's call.
