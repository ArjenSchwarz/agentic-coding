# Independent local review brief

Use this brief for either a native reviewer subagent or the Claude `local-review`
agent. The reviewer must not have authored the changes or implemented this round's
fixes. Start with a fresh review context, without the implementer's conclusions.

## Inputs and setup

The caller supplies the repository/worktree path, CR id, expected head SHA, and
forge adapter paths. If invoked directly without an id/SHA, resolve them with
`CR_VIEW` (infer the CR from the current branch). Stop if no open CR is found.

Read the forge contract and matching adapter (normally
`~/.claude/forge-adapters/CONTRACT.md` and `<FORGE>.md`); run `PREFLIGHT` to confirm
forge authentication. Use adapter operations for forge access. If these resources
are unavailable, report that prerequisite rather than guessing commands.

## Inspect the current change

1. Resolve `CR_VIEW`, including its `sha`, and confirm it matches the supplied head.
   Fetch `CR_DIFF` and `CR_FILES`. Inspect the full diff and enough surrounding code
   and tests to assess the change. Never substitute a summary of the implementation
   for the diff. Check any local files used as evidence are from the reviewed SHA;
   do not review unrelated or uncommitted worktree content as if it were the CR.
2. Read applicable root and nested `AGENTS.md`, `CLAUDE.md`, and sibling project
   rules for touched paths. Follow their scope and precedence, without inventing
   project-specific requirements.
3. Cover code quality, potential bugs, performance, security, test coverage, and
   project-specific rules. Prioritise behaviour-bearing files in large diffs, but
   account for every changed file. If access, truncation, or time prevents complete
   coverage, explicitly report an incomplete review and its limits; do not return
   a clean verdict. Documentation-only changes still need correctness review.
4. Ground every finding in `file:line-range` at the reviewed SHA with the smallest
   useful snippet, severity (blocker/critical/major/minor/nitpick), concrete impact,
   and a suggested fix. Prefer real issues over speculative style complaints.
5. Re-fetch `CR_VIEW` after inspection. If the head changed, report the review as
   stale; it cannot satisfy the current-head review gate.

## Produce and post one note

Use British English. Start with `**Verdict:**` and a clear clean/findings/incomplete
result. Include `**Reviewed SHA:** <full SHA>` and `**Reviewer:** <actual agent/runtime>`.
Group findings under non-empty category headings; if none, explicitly say no
findings. State coverage and any limitations. End with the legacy compatibility
sentinel on its own line:

```html
<!-- claude-local-review -->
```

This marker identifies the review format to `pr-review-fixer`; it does not imply
that Claude performed a native review. Do not change it without updating consumers.

Write the body to a temporary file outside the repository and use `CR_COMMENT`
with that file. If a native reviewer lacks posting tools, return the complete body
for its parent to post unchanged. Verify the posted body through `CR_NOTES_LIST`
and report the CR URL, reviewed SHA, verdict, and note id. Report posting failures
or uncertain outcomes explicitly; producing text alone is not a posted review.

Stay read-only on the working tree. Do not edit code, run fixers, push commits,
formally approve, or merge. Do not consult other AI systems or delegate the review
further. Return actionable findings even when review is incomplete; the caller must
not count that partial result as clean.
