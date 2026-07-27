# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2026-07-27]

### Removed
- Gemini as a peer reviewer: `peer-review-validator` no longer lists `mcp__devtools__gemini-agent` in its tools or its external-model consultation list, and the selection strategy drops the "use Gemini for general analysis" line. External-model mode now names Codex and Kiro only, with an instruction to top up from subagent mode (and say so) if one of the two is unavailable, since the two-perspective minimum no longer has slack. README and `starwave-requirements` updated to match — the latter also had a stale "Q Developer" reference, now Kiro; `fix-bug`'s "do not use these MCP agents" list drops the Gemini entry

## [2026-07-07]

### Added
- `no-push-main.py`: regression test (`claude/hooks/test_no_push_main.py`) covering the protected-branch push matrix, including the newly-closed bypasses. Run with `python3 claude/hooks/test_no_push_main.py`
- `blitz-merge` skill: a review-availability guarantee (`count_reviews` — never merge a PR that no review looked at; falls back to `local-review` when a round produces no review comment) and a pre-push review artifact step (a subagent runs `/pre-push-review` against `origin/main` per PR, so a durable, human-auditable review exists before merge). Phase 3 now refuses to squash-merge unless a review is on record **and** the artifact was generated

### Changed
- `no-push-main.py`: harden `git push` protection to resolve the real destination ref — now blocks `+main` (force via refspec), `HEAD:refs/heads/main`, `HEAD` while on a protected branch, and `--mirror` / `--all`, all of which previously bypassed the hook
- `claude/CLAUDE.md`: calibrate the workflow gate prose to reversibility — keep the approval-gate and tool-result-verification guidance, drop the blanket "do not commit/push/open a PR/merge unless asked" sentence and the "run one command per turn" rule

### Removed
- `claude-remote.sh` and its SessionStart hook wiring (project `.claude/settings.json` and `project-init`'s `setup-project.sh`): the remote `curl | bash` configuration bootstrap is no longer part of the workflow

## [2026-06-20]

### Added
- Forge adapter layer (`claude/forge-adapters/`): a `CONTRACT.md` defining forge-neutral operations (`PREFLIGHT`, `CR_VIEW`, `CR_DIFF`, `THREADS_FETCH`, `CR_COMMENT`, `CR_MERGE`, etc.) and a shared vocabulary (CR/thread/note/CLI), plus per-forge adapters `github.md` (`gh`) and `gitlab.md` (`glab`) implementing each operation. Workflows call named operations and never hard-code a CLI command — when an operation is missing from the selected adapter they stop and report rather than improvise
- README: `Forge support (GitHub & GitLab)` and `Personal vs. work projects (PERSONAL_PROJECTS)` sections explaining the adapter architecture and the fail-closed external-AI gating

### Changed
- `local-review` agent, `pr-pilot` and `pr-review-fixer` skills: converted to forge-aware. Each detects the forge from `git remote get-url origin` via `PREFLIGHT`, reads the matching adapter, and calls the contract's named operations instead of hard-coded `gh` commands — so the same workflow runs unchanged on GitHub and GitLab
- README: updated the `local-review` and `peer-review-validator` agent descriptions (forge detection; `PERSONAL_PROJECTS` gating with Claude-subagent fallback), added `claude/forge-adapters/` to the File Structure list
- README: in the `Personal vs. work projects` section, document scoping `PERSONAL_PROJECTS` to a directory tree — a `.zshrc` `case` snippet for shell-startup evaluation, plus a full `chpwd` hook (with an `unset` branch and an initial call) for setting it on `cd` within a running shell
- `go-test-fixer` skill: add YAML frontmatter (`name`/`description`) so the skill is discoverable
- `release-prep` skill: replace the prompt-style `description` frontmatter with a plain one-line summary
- `capture-knowledge` skill: minor description wording
- `.gitignore`: ignore `claude/skills/.system/`
- `copilot/prompts/Main.instructions.md`: add placeholder instructions file

## [2026-06-11]

### Added
- `spec-cleanup` skill: Identify and clean up stale or superseded feature specs in a project's `specs/` directory. Detects supersession candidates via naming patterns (`-v2`, `-revised`), explicit supersedes/replaces/builds-on references, decision-log statuses, scope overlap, and git-history corroboration, then classifies each pair as fully replaced (recommend removal) or extended (consolidate-vs-remove is a user decision, with decision-log carry-over on consolidation). Presents an evidence-backed report behind a hard approval gate before touching any file, removes via `git rm` so specs stay recoverable, regenerates `specs/OVERVIEW.md` if present, and never touches `specs/bugfixes/`

## [2026-06-03]

### Changed
- `peer-review-validator` agent: Gate the external AI systems (Gemini/Codex/Kiro) behind the `PERSONAL_PROJECTS` environment variable. The Peer Consultation step now checks `echo "$PERSONAL_PROJECTS"` first: when it equals `1` the agent uses external-model mode (the MCP agents, as before); otherwise it uses subagent mode — spawning at least two `general-purpose` subagents via the Task tool with the same validation package but distinct lenses (correctness/edge-cases, architecture/maintainability, optional risk/security). The Communication and Key principles sections were reworded to describe both modes and to require stating which mode was used

## [2026-05-22]

### Changed
- `make-it-so` skill: Always delegate phase work to a subagent — the main agent no longer implements tasks itself in any path. Multi-stream phases still use one worktree-isolated subagent per stream as before. Single-stream and stream-less phases now spawn one subagent that implements the whole phase in place (no worktree, no merge step) and commits to the working branch. Subagent commit conventions are unified: no subagent touches `CHANGELOG.md`; the main agent always writes the single phase-level changelog entry after subagents return (and after merges, in parallel mode). Review (design-critic), specs/OVERVIEW.md update, and compact-and-continue still run on the main agent
- `make-it-so` skill: Restructure parallel execution so each ready work stream is owned end-to-end by a dedicated subagent running in its own git worktree. The main agent now only delegates and oversees — it creates a worktree per ready stream (`git worktree add .claude/worktrees/<phase>-stream-<N> -b stream/<phase>-<N>`), spawns one subagent per worktree in a single Task message, and re-checks `rune streams --available --json` after each return to spawn fresh subagents for newly unblocked streams. Stream subagents implement, mark tasks complete, run tests, and commit on their own stream branch using the project's commit conventions (skipping the changelog, which is now a single phase-level entry written by the main agent after merging all streams). After all streams report `done`, the main agent merges each stream branch with `--no-ff` (trivial `tasks.md` conflicts are expected — accept both sides), removes the worktrees, deletes the merged branches, runs design-critic, writes the phase changelog entry as a separate commit, updates `specs/OVERVIEW.md`, then compact-and-continues. Sequential single-stream / no-stream paths still work in place and still update the changelog themselves

## [2026-05-19]

### Changed
- `scripts/build_review_html.py`: Replace highlight.js diff highlighting with a self-rendered per-line markup. New `_render_diff()` splits the diff and tags each line as `diff-add`/`diff-del`/`diff-hunk`/`diff-file-header`/`diff-meta`/`diff-context`; the page CSS styles `.diff-line` as `display:block` with full-width backgrounds (via `display:inline-block; min-width:100%` on the surrounding `<code>`) so consecutive additions or deletions paint a continuous bar instead of per-line "row pills" separated by the trailing-newline gap hljs produced. The highlight.js stylesheet and three scripts are removed from the page template since nothing else used them
- `claude/CLAUDE.md` (user global): Add "Before editing any file, read it first. Before modifying a function, grep for all callers. Research before you edit" to the Development Workflow section
- `make-it-so` skill: Detect ready work streams per phase via `rune streams --available --json` and spawn one parallel subagent per stream (single message, single Task call each) when 2+ streams are ready, falling back to sequential execution when only one stream has ready work. Each subagent uses `rune next --phase --stream N --format json` to retrieve its tasks and marks them complete as it goes. The existing per-phase review → commit → specs-overview update → compact-and-continue loop is preserved, and the loop now stops cleanly without compacting when no incomplete tasks remain

## [2026-05-18]

### Added
- `local-review` agent: Sonnet-powered local replacement for the `anthropics/claude-code-action` PR review step. Reviews an open PR via `gh pr diff`, follows the project's `CLAUDE.md` for style/conventions and project-specific flag rules, and posts a single `gh pr comment` so the same review can run without burning private GitHub Actions minutes
- `pr-overview` skill: Read-only PR summary workflow that fetches a GitHub PR, surfaces unresolved code/review/discussion comments verbatim, runs the same parallel review agents as `pr-review-html` without applying fixes, and writes a self-contained `pr-overview.html` to the repo root for browsing before deciding what to do
- `scripts/build_review_html.py`: Shared HTML renderer used by `pre-push-review`, `pr-review-html`, and `pr-overview`. Consumes a JSON description plus optional per-file diff fragments and emits a self-contained Prism Dark themed page with overview cards, three-level explanation tabs (CSS-only radio buttons), important-change cards with Takeaway/Rationale/Open-question callouts, per-file diff `<details>` blocks, and an optional `<script id="review-meta">` block for `pulsar publish` consumption

### Changed
- `pr-pilot` skill: New step 1.5 runs `local-review` in steps 2.1 and 3.3 **by default** and skips it only when an active `anthropics/claude-code-action` workflow (`.github/workflows/*.yml` or `*.yaml` referencing the upstream action) will post the review on its own. Renamed `.yml.disabled` files, `.bak`, editor swap files, or a missing workflow all leave `local-review` running — the goal is "there should always be a Claude review on every PR; the local agent is the cheaper default, the GH Action is the only reason to skip it"
- `local-review` agent: Append a `<!-- claude-local-review -->` sentinel to every PR comment so downstream skills can identify it as a Claude review even though `gh pr comment` posts under the local user account, not `claude[bot]`
- `pr-review-fixer` skill: Treat `claude[bot]` author **and** body-sentinel `<!-- claude-local-review -->` as Claude reviews in all three dedup rules (code-level, PR-level reviews, PR-level issue comments). Emit `<!-- pr-review-overview -->` at the top of the iteration overview comment and match on that sentinel for iteration counting — the previous `claude[bot]`-only check missed every iteration when the skill ran outside the upstream Action
- `pr-overview` skill: Same Claude-review sentinel handling as `pr-review-fixer`; also match the iteration-overview sentinel when filtering noise out of the discussion-comments stream
- `pre-push-review` skill: Phase 7 now invokes the shared `build_review_html.py` renderer with a JSON contract instead of hand-writing HTML; Phase 6 extracts important changes, learnings, and decision rationale (with `inferred` / `unknown` markers) for the renderer even when no spec exists; new Phase 8 publishes via the optional `pulsar` binary when present; Phase 9 (formerly 8) surfaces the archived path
- `pr-review-html` skill: Same renderer refactor as `pre-push-review`. Phase 1 now keeps PR `body`, `author`, `createdAt`, and `url` so Phase 7 can render the author's framing verbatim in a `pr_description` block; Phase 6 produces the three-level explanation plus insight material in a single pass; new Phase 8 publish step and Phase 9 summary mirror `pre-push-review`
- `scripts/README.md`: Document `build_review_html.py` — purpose, CLI usage, JSON schema pointer, rendering behaviour, and output

### Added
- `capture-knowledge` skill: Capture reusable cross-project technical knowledge as notes in the user's Obsidian vault under `03-Notes/Generated/`, with per-machine vault path cache, frontmatter conventions, collision handling, and Obsidian Flavored Markdown guidance
- `pr-review-html` skill: Fetch a GitHub PR, run parallel review agents (code reuse, quality, efficiency, spec/docs), apply local fixes, verify with tests and linters, and write a self-contained `pr-review.html` to the repo root with per-file diffs, decisions, findings, and double-check items
- `claude/statusline.sh`: Custom statusline showing directory, model (with optional effort level), context window percentage, 5h/7d rate-limit usage with reset times, and git branch with dirty marker
- `arjen-style-guide.md`: Personal iOS/iPadOS/macOS 26+ SwiftUI style guide distilled from Prism, Transit, and Flux

### Changed
- `pre-push-review` skill: Add Phase 7 to generate a self-contained HTML review page (per-file diffs with highlight.js, how-it-works explanation, key decisions, review findings, things to double-check), with a spec-aware location fallback; renumber Summary to Phase 8 and include the HTML path in the verdict
- `no-push-main` hook: Honor `git -C <path>` when detecting the current branch, so push/rebase/reset/amend/checkout/restore/clean run inside worktrees check the worktree's branch instead of the shell's cwd
  - New `extract_git_cwd()` helper pulls the last `-C` argument out of the original command
  - `get_current_branch`, `on_protected_branch`, and the push/history/destructive checks all accept an optional `cwd` and pass it through to `git rev-parse`

## [2026-04-24]

### Changed
- Starwave spec skills: Tighten brevity, scope, and granularity rules across the requirements → design → tasks workflow to curb verbose output
  - `starwave:requirements`: Add "Writing Style — Signal over Volume" block (behavior-not-implementation ACs, no speculative/future-proofing reqs, no split outcomes, concrete-or-omit NFRs, no hyperbole); require a Non-Goals / Out-of-Scope section in the document format; add matching self-review gates
  - `starwave:design`: Add "Writing Style — Signal over Volume" block (no requirement restatement, no boilerplate sections, no hyperbole, distilled research); allow omitting inapplicable sections; add "Contracts and Integration Points — Do Not Cut" block (behavioral contracts, integration points, file/module placement); add non-goals and contracts gates to self-review
  - `starwave:tasks`: Add "Task Granularity — No Inflation" block (no fragmenting coherent changes across setup/implement/wire, no decorative phases or streams, no title-restating `details` bullets); add non-goals and granularity gates to self-check
  - `starwave:smolspec`: Add fragmentation and out-of-scope rules to Task Description Guidelines; extend smolspec self-review with behavior-not-mechanism and anti-hyperbole gates; extend tasks self-review with fragmentation and out-of-scope gates

## [2026-04-22]

### Changed
- `pr-review-fixer` skill: Stop writing working files inside the repo
  - Working directory moved to `/tmp/pr-review-${PR_NUM}/`; removed the `.claude/reviews/` option
  - Review overview is assembled in-context and posted inline via `gh pr comment` (no intermediate file)
  - Rune task file now lives under the temp working directory; dropped the `--reference` to a non-existent overview file
  - Removed `tee test-output.txt` from test failure handling
  - Cleaned up stale "exclude working files" guidance in commit step and Key Behaviors
- `transit` skill: Route `chore` task type to `/starwave:smolspec` instead of asking the user to clarify

## [2026-04-14]

### Added
- `claude-code-workshop` skill: Interactive workshop that teaches Claude Code features through hands-on exploration, with version-based filtering to focus on what's new since a specific release
- `WSL-settings` agent note: Document `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` and `CLAUDE_CODE_SCRIPT_CAPS` behavior on WSL2

## [2026-04-11]

### Changed
- `blitz-merge` skill: Add local main branch update after all merges complete
  - New Phase 4 checks out and pulls the local main/master branch so it stays in sync with origin
  - Renumbered Report and Cleanup phase to Phase 5
- `starwave-design` skill: Add pattern extension audit and UI consistency reference requirements
  - New "Pattern Extension Audit" section: when extending an existing pattern to a new type, requires searching all call sites and including a parity audit in the Architecture section
  - New "UI Consistency References" section: requires referencing existing UI elements as baseline instead of describing visual properties from scratch
  - Two new self-review checklist items for pattern audit and UI consistency verification
- `starwave-requirements` skill: Add guidance for acceptance criteria to reference existing UI patterns as baseline rather than describing visual properties independently

## [2026-04-03]

### Changed
- `no-push-main` hook: Handle compound commands and git global options
  - Split compound shell commands (chained with `&&`, `||`, `;`) and check each part independently
  - Strip git global options (`-C`, `--git-dir`, `--work-tree`, etc.) before matching, so `git -C /path push` is correctly blocked

### Added
- `specs-overview` skill: Generate or regenerate `specs/OVERVIEW.md` with tabular summary, status tracking, and per-spec file listings
- `make-it-so` skill: Update `specs/OVERVIEW.md` status after committing (Done/In Progress)
- `next-task` skill: Update `specs/OVERVIEW.md` status after completing task groups
- `starwave-creating-spec` skill: Add Phase 4.5 to register new specs in `specs/OVERVIEW.md`
- `orbit-guidance-2.yaml`: Multi-variant guidance file for orbit with minimal and defensive approach variants

## [2026-03-18]

### Changed
- `no-push-main` hook: Add `gh` CLI protection and fix exit code
  - Blocks `gh repo delete`, `gh repo edit --default-branch`, `gh repo sync --force --branch main`, `gh pr merge --admin`
  - Blocks mutating `gh api` calls targeting protected branch refs, branch protection rules, and rulesets
  - Detects mutation intent via HTTP method, `-f`/`-F` field flags, `--input`, and GraphQL mutations
  - Fix exit code from 1 to 2 (required by Claude Code to block execution)

### Added
- Branch protection research report (`docs/agent-notes/branch-protection-across-agents.md`)
  - Documents protection mechanisms for Claude Code, Kiro CLI, Copilot CLI, and Codex CLI
  - Covers `gh` CLI and MCP server attack surfaces with practical recommendations

## [2026-03-15]

### Added
- `no-push-main` PreToolUse hook that protects `main`/`master` branches from accidental modification
  - Push protection: direct, force, bare, refspec targets, `--delete`, and flag combinations (`-u`, `--force-with-lease`)
  - History rewrite protection: blocks `reset --hard`, `rebase`, and `commit --amend` while on protected branches
  - Destructive operation protection: blocks `checkout .`, `restore .`, and `clean -f` while on protected branches
  - Branch manipulation protection: blocks `branch -D`/`-f` targeting protected branches
  - Hook lives in `claude/hooks/` and is synced to `~/.claude/hooks/` for global use
- `claude/hooks/` directory with README documenting available hooks, setup, and how to add new ones
- Hooks symlink in `sync-claude.sh`, GitHub Action, and remote sync for consistent availability across local, CI, and sandbox environments

## [2026-03-11]

### Changed
- `pr-pilot` skill: Replace `gh pr checks --watch` with a 10-minute wait for CI and agent reviewers, then run `/pr-review-fixer` to handle new comments on rebased code
- `pre-push-review` skill: Rewrite as parallel multi-agent review with automatic fixes
  - Launches 4 concurrent review agents: code reuse, code quality, efficiency, and spec/documentation
  - Agents fix issues directly instead of only reporting them
  - Adds verification phase to run tests and linters after fixes
  - Simplifies structure into 7 clear phases

## [2026-03-05]

### Changed
- `fix-bug` skill: Add difficulty-based branching with competing implementations for complex bugs
  - Investigation checkpoint: commit failing regression tests and report before implementing the fix (red/green TDD)
  - Difficulty assessment: classify bugs as simple (direct fix) or complex (multiple approaches)
  - Complex path spawns 3 competing agents (2 Claude subagents via Agent tool + 1 Kiro via `mcp__devtools__kiro-agent` with `agent: "kiro"`)
  - Compares solutions on correctness, minimality, code quality, safety, and maintainability
  - Produces a solution comparison report and cherry-picks the winning implementation

## [2026-03-04]

### Added
- `pr-pilot` skill for shepherding a PR from push through review to merge
  - Pushes branch, creates PR, runs `/pr-review-fixer` in a loop until no blockers/critical/major issues remain (capped at 5 iterations)
  - Rebases onto latest `origin/main`, resolves conflicts, and squash-merges
  - Optional Transit ticket tracking — moves ticket to `done` after merge
- `blitz-merge` skill for batch-fixing bugs with automated review cycles and squash-merge
  - Extends bug-blitz with a review loop that runs `/pr-review-fixer` until no blockers/critical/major issues remain (capped at 5 iterations)
  - Sequentially squash-merges each clean PR after rebasing onto latest `origin/main`
  - Updates Transit tickets to `done` after successful merge

## [2026-02-27]

### Changed
- `bug-blitz` skill: Always filter bugs by the current Transit project instead of treating project filtering as optional

## [2026-02-26]

### Changed
- `fix-bug` skill: Add automated review fix step that waits 10 minutes after PR creation then runs `/pr-review-fixer` to handle first round of CI and review feedback (Transit bugs only)

## [2026-02-23]

### Changed
- `starwave-tasks` skill: Enforce red/green TDD ordering for all implementation tasks
  - Tasks must follow red (write failing test) then green (implement to pass) pairing
  - Test and implementation tasks must be adjacent and clearly paired
  - Configuration, types/interfaces, and wiring tasks are exempt
- `starwave-tasks` skill: Add self-check section before presenting tasks to user
  - Verify red/green TDD ordering
  - Run `rune list` to validate task file renders correctly (numbering, hierarchy, streams, dependencies)
  - Confirm requirement coverage, no orphaned tasks, and no circular dependencies

## [2026-02-22]

### Changed
- `pr-review-fixer` skill: Post review reports as PR comments instead of committing them as files
  - Review overview is posted via `gh pr comment` before pushing code fixes
  - Local review/task files are working files only, never committed
  - Iteration tracking now based on existing `claude[bot]` PR comments

## [2026-02-20]

### Added
- `code-audit` skill for parallel codebase quality review
  - Spawns two subagents (code-simplifier and design-critic) to independently analyse the current directory
  - Consolidates and deduplicates findings into a prioritised report grouped by category
  - Offers to create Transit tasks for actionable items

## [2026-02-18]

### Changed
- `pr-review-fixer` skill: Namespace non-spec review output by PR number (`.claude/reviews/PR-[number]/`) to prevent file conflicts when multiple PRs are worked on simultaneously

## [2026-02-16]

### Added
- `bug-blitz` skill for batch-fixing all open bugs in parallel
  - Fetches bug-type tasks in "idea" status from Transit
  - Creates isolated git worktrees per bug based off main
  - Spawns parallel subagents each running the fix-bug workflow
  - Reports results in a summary table and offers worktree cleanup

### Changed
- Added Transit comment requirement to CLAUDE.md — status changes must include an explanatory comment
- `fix-bug` skill: Auto-create branch and PR for Transit bugs instead of prompting; added Transit comment templates for status transitions
- `fix-bug` skill: Skip branch creation when current branch already matches `T-{number}/bugfix-*` (worktree support)
- `starwave-creating-spec` skill: Added Transit comment templates for `spec` and `ready-for-implementation` status transitions

## [2026-02-14]

### Changed
- Renamed `liquid-glass-forms` skill to `swiftui-forms`
- Added Transit ticket (`T-<id>`) convention to CLAUDE.md project conventions, pointing to Transit MCP tools and `transit` skill
- Added `swiftui-forms` skill reference to Swift language rules for form layout work
- `starwave-smolspec` skill: Clarified rune integration to explicitly request file creation with smolspec.md reference and `blocked_by` dependencies via batch operations

## [2026-02-13]

### Added
- `transit` routing skill for dispatching Transit tickets (`T-[number]`) to appropriate workflows by task type
  - Routes bugs to `/fix-bug`, features to `/starwave:creating-spec`, research to plan mode
  - Asks for clarification on chore and documentation types
  - Handles edge cases: task not found, done/abandoned tickets, ambiguous types
- Transit integration in `fix-bug` skill with ticket status tracking and branch creation step
  - Moves ticket to `in-progress` at start, `ready-for-review` at completion
  - Offers `T-{number}/bugfix-{bug-name}` branch naming when ticket present
- Transit integration in `starwave-creating-spec` skill with ticket status tracking
  - Moves ticket to `spec` after scope assessment approval, `ready-for-implementation` after Phase 5
  - Offers `T-{number}/{spec-name}` as recommended branch name when ticket present
- Agent notes for Transit integration (`docs/agent-notes/transit-integration.md`)

### Changed
- `commit` skill: Broadened ticket extraction pattern from 3-5 to 1-5 character prefixes to support Transit's `T-[number]` format

## [2026-02-06]

### Changed
- `next-task` skill: Updated parallel execution to use `rune next --phase --stream N` for subagents
  - Subagents now retrieve all phase tasks for their stream in one call instead of iterative claiming
  - Simplified subagent instructions and cross-stream coordination
- `pr-review-fixer` skill: Added thread resolution, auto-commit, and push
  - New step to resolve fixed code-level review threads via GraphQL mutation
  - Final step now explicitly commits and pushes to remote
  - Added thread `id` to GraphQL query for review thread resolution

### Added
- Agent Notes workflow in CLAUDE.md for maintaining implementation notes across sessions
  - Notes stored in `docs/agent-notes/`, organised by topic or module
  - Read relevant notes before starting tasks, update after completing them
- Skills Usage section in CLAUDE.md to direct agents to check existing skills before manual approaches

## [2026-02-04]

### Added
- `explain-like` skill for explaining code changes or designs at three expertise levels (beginner, intermediate, expert)
  - Supports PR/branch change explanations and design document validation
  - Generates structured explanations with different depth for different audiences
  - Can be used as a self-review mechanism to catch gaps or logic issues
- `fix-bug` skill for systematic bug investigation, resolution, and documentation
  - Integrates with `systematic-debugger` skill for root cause analysis
  - Creates regression tests before implementing fixes
  - Generates standardized bugfix reports in `specs/bugfixes/<bug-name>/`
- `orbit-guidance.yaml` template for multi-variant implementation approaches
  - Defines three implementation styles: Minimal/Pragmatic, Defensive/Thorough, Performance-Oriented
  - For use with Orbit multi-agent parallel execution

### Changed
- `pre-push-review` skill: Added implementation explanation step using `explain-like` skill
  - Generates `specs/{feature_name}/implementation.md` for documentation
  - Uses explanation as validation mechanism to verify spec completeness
  - Adds "Completeness Assessment" section to track implementation status
- `starwave-design` skill: Added self-validation step using `explain-like` skill
  - Requires explaining design at multiple expertise levels before proceeding to reviews
  - Helps identify gaps, overcomplexity, or logic issues in design documents

## [2026-02-01]

### Added
- Multi-agent parallel execution support via work streams and task dependencies
  - `rune` skill: Added stream assignment, blocked-by dependencies, task ownership/claiming, and stream status commands
  - `next-task` skill: Added stream detection and parallel subagent spawning for multi-stream execution
  - `starwave-tasks` skill: Added guidelines for creating tasks with dependencies and work stream assignments

### Changed
- `pr-review-fixer` skill: Extended to fetch PR-level comments (reviews and issue comments) in addition to code-level comments; added CI status checking and automated fix workflow for failing tests, lint, and build
- `pre-push-review` skill: Enhanced documentation section to explicitly check README.md, CLAUDE.md/AGENTS.md, and other docs for needed updates
- `starwave-requirements` skill: Changed design-critic invocation to use Task tool with subagent_type="general-purpose" instead of direct skill call
- `starwave-design` skill: Changed design-critic invocation to use Task tool with subagent_type="general-purpose" instead of direct skill call

## [2026-01-22]

### Added
- `pr-review-fixer` skill for fetching and fixing GitHub PR review comments
  - Filters out resolved comments and keeps only last claude[bot] comment per thread
  - Validates issues against current code before creating fix tasks
  - Creates review-overview and review-fixes files with iteration tracking
  - Integrates with rune for task management
  - Supports spec-based PRs (output to specs folder) and non-spec PRs (output to .claude/reviews)

## [2026-01-21]

### Changed
- Updated skill files to replace "agent" references with "skill" terminology
  - `next-task`, `make-it-so`: Changed "sub agent" to "skill" for efficiency-optimizer and design-critic
  - `starwave-requirements`, `starwave-design`: Updated to use design-critic skill and Task tool with subagent_type="peer-review-validator"
  - `starwave-smolspec`: Changed "design-critic agent" to "design-critic skill"

## [2026-01-20]

### Added
- `pre-push-review` skill for reviewing unpushed commits before pushing to remote repository
  - Reviews code quality, spec adherence, testing, and documentation
  - Provides actionable feedback categorized by severity (Critical, Important, Minor, Suggestion)
  - Skill-based alternative to the existing `pre-push-code-reviewer` agent
- `code-simplifier` skill for reviewing and simplifying code to reduce complexity
- `ui-ux-reviewer` skill for evaluating user experience of interfaces (CLI, web, mobile)
- `efficiency-optimizer` skill for analyzing code for performance improvements
- `design-critic` skill for critical review of design documents and architecture proposals

### Changed
- Updated `peer-review-validator` agent to use `kiro-agent` instead of `q-developer-agent` for AWS/cloud-native validation

### Removed
- `code-simplifier` agent (replaced by skill)
- `ui-ux-reviewer` agent (replaced by skill)
- `efficiency-optimizer` agent (replaced by skill)
- `design-critic` agent (replaced by skill)
- `pre-push-code-reviewer` agent (replaced by `pre-push-review` skill)

## [2025-01-16]

### Changed
- Restructured CLAUDE.md with organized sections (Communication Style, Development Workflow, Project Conventions, CLI Commands, Documentation Standards)
- Added availability check for `run_silent` command before using it
- Replaced XML-style tags with standard markdown headers

## [2025-01-15]

### Changed
- Updated commit skill to conditionally run tests and linting only when code files are changed, skipping for documentation-only changes

## [2025-01-14]

### Changed
- Migrated all commands to skills - commands directory has been removed
- Reorganized spec-driven development skills under `starwave-` prefix with flat folder structure:
  - `starwave-creating-spec` - Main orchestrator for the full workflow
  - `starwave-smolspec` - Lightweight specification for small changes
  - `starwave-requirements` - Requirements gathering phase
  - `starwave-design` - Design document creation phase
  - `starwave-tasks` - Task planning phase
- Skills are now invoked as `/starwave:creating-spec`, `/starwave:requirements`, etc.
- Updated spec-workflow.md with new workflow diagram showing `/starwave:creating-spec` as the main entry point
- Updated README.md to reflect new skill organization and workflow

### Added
- Optional `prerequisites.md` file support in starwave-tasks skill for manual user setup tasks
  - Supports tasks like Xcode configuration, Apple Developer portal setup, cloud console configuration
  - Organizes prerequisites by timing: Before Starting, During Implementation, Before Testing
- Smolspec section in spec-workflow.md explaining when and how to use the lightweight specification workflow

### Removed
- `claude/commands/` directory - all commands migrated to skills
- Removed `commands` symlink from sync-claude.sh and GitHub Action

## [2025-12-31]

### Added
- `project-init` skill for setting up Claude Code project configuration
  - Adds SessionStart hook to `.claude/settings.json` for remote/sandbox environments
  - Includes `setup-project.sh` script that merges hooks without overwriting existing settings
  - Language detection for automatic permission configuration (Go, Swift, Node.js, Python, Rust, Ruby, Java, Docker, Terraform)
- `skill-creator` skill for creating effective Claude skills
  - Includes `init_skill.py` script for initializing new skill directories
  - Includes `quick_validate.py` for skill validation
  - Reference documentation for workflows and output patterns
- `systematic-debugger` skill for applying modified Fagan Inspection methodology to persistent bugs
- `permission-analyzer` skill for analyzing Claude Code permission configurations
  - Includes `analyze_permissions.py` script for permission analysis
- `starwave` commands directory with design, requirements, and tasks commands
- `make-it-so` command for implementing all tasks
- `claude-remote.sh` script for pulling user configuration in sandboxed environments (GitHub Actions, online Claude Code)
- Project-level `.claude/settings.json` with SessionStart hook for remote environment setup

### Changed
- Simplified `creating-spec` skill documentation
- Updated `rune` skill with minor improvements
- Simplified `copilot/prompts/tasks.prompt.md`
- Expanded Swift language rules with additional patterns and guidelines

## [2025-12-13]

### Added
- Scripts directory symlink to setup-claude GitHub Action and sync-claude.sh script

### Fixed
- Updated README documentation in setup-claude action to reference `rules/` instead of `language-rules/`

## [2025-12-10]

### Added
- Swift language rules (`claude/rules/language-rules/swift.md`) with patterns for:
  - SwiftData and CloudKit testing with test environment detection
  - Swift 6 concurrency and MainActor patterns
  - SwiftUI Liquid Glass guidelines for iOS 26+/macOS Tahoe
  - NavigationSplitView platform-specific patterns
  - App Intents design for Shortcuts compatibility
  - Testing with Swift Testing framework
- Sync script (`scripts/sync-claude.sh`) for creating symlinks from `~/.claude/` to repository files

### Changed
- Reorganized all Claude Code configuration files into `claude/` subdirectory structure:
  - `CLAUDE.md` → `claude/CLAUDE.md`
  - `agents/` → `claude/agents/`
  - `commands/` → `claude/commands/`
  - `skills/` → `claude/skills/`
  - `language-rules/` → `claude/rules/language-rules/`
  - `references/` → `claude/rules/references/`
- Updated GitHub Action to use new `claude/` directory structure for symlinks
- Updated example workflow to verify new directory structure
- Updated README.md with new file structure documentation
- Added YAML frontmatter with `paths` glob pattern to language rules for automatic matching

## [2025-12-02]

### Added
- Self-review checklists for requirements and design commands
  - Requirements: EARS format compliance checklist (user story format, EARS keywords, testable criteria, anchor tags, vague terms, edge cases)
  - Design: Requirements traceability checklist (design element coverage, acceptance criteria tracing, data model support, error handling, testing strategy, scope creep check)
- Added checklists to both Claude Code commands and Copilot prompt versions

## [2025-12-01]

### Added
- Copilot prompt version of smolspec command (`copilot/prompts/smolspec.prompt.md`)
- Property-based testing (PBT) guidance as optional consideration in design workflow
  - Design command evaluates acceptance criteria for PBT candidates (invariants, round-trips, idempotence)
  - Tasks command includes property test tasks when design specifies them
  - Go language rules include PBT section with `pgregory.net/rapid` recommendation
- Decision log format reference document (`references/decision-log-format.md`) with Enhanced Nygard ADR structure
- Utility scripts: `scripts/convert_formats.sh` and `scripts/fetch-tickets.py`

### Changed
- Enhanced `smolspec` command with complexity estimation, self-review checklists, outcome-focused tasks, and distributed testing requirements
- Updated CLAUDE.md with decision log format reference and fixed file path syntax
- Changed `design-critic` and `peer-review-validator` agents to use opus model
- Updated Copilot prompt frontmatter to use `agent: agent` instead of `mode: agent`
- Enhanced `pr-prep.prompt.md` to save release notes to pr_description.md

## [2025-11-14]

### Added
- `smolspec` command for lightweight specification workflow for small changes
  - Combined requirements and implementation approach in single smolspec.md file
  - Separate tasks.md file compatible with next-task command
  - Built-in scope assessment with automatic escalation to full spec workflow
  - Integration with design-critic agent for review before user presentation
  - Streamlined workflow for minor changes that don't warrant full documentation
- Go Test Fixer skill for improving Go test files
  - Converts slice-based table tests to map-based table tests
  - Splits large test files into focused test files
  - Enforces Go testing best practices from language-rules/go.md

### Changed
- Updated release-prep command to specify release notes location in docs/release_notes/
- Updated Copilot prompt files to use gpt-5.1-codex model instead of gpt-5

## [2025-11-04]

### Added
- GitHub Action for setting up Claude configuration in CI/CD pipelines
  - Composite action at `.github/actions/setup-claude/action.yml` that symlinks all configuration directories
  - Action symlinks agents, commands, language-rules, scripts, skills, and CLAUDE.md to `~/.claude/`
  - Example workflow demonstrating action usage with verification steps
  - Action documentation with basic and advanced usage examples
- Skills section in README documenting `creating-spec` and `rune` skills
- GitHub Action section in README with usage examples and workflow integration
- `creating-spec` skill for orchestrating spec-driven development workflow
  - Complete three-phase workflow: requirements, design, and task planning
  - Built-in approval gates between phases
  - Integration with design-critic and peer-review-validator agents
  - Automatic decision logging and EARS format requirements
  - Rune CLI integration for task management
- Enhanced rune skill documentation with `--reference` flag support for creating task files with top-level references

### Changed
- Updated README with Skills section explaining spec-driven workflow orchestration and task management capabilities
- Enhanced README with GitHub Action documentation including basic usage, what it does, and complete CI/CD examples
- Added example pattern for creating feature task files with references to requirements, design, and decision log

## [2025-11-03]

### Added
- Rune task management skill with instructions and capabilities
- Skill configuration files (skills/rune/prompt.md, skills/rune/skill.json)

### Changed
- Updated CLAUDE.md to instruct using rune skill for task management
- Simplified next-task.md command to delegate to rune skill for task retrieval and completion
- Simplified tasks.md command to delegate task creation to rune skill instead of requiring manual JSON construction

## [2025-11-03]

### Added
- `catchup` command for analyzing branch changes and commits to quickly understand work done
- Command documentation in commands/catchup.md with workflow for understanding branch history

### Changed
- Updated README.md to include catchup command in workflow list with attribution to Shrivu Shankar

## [2025-10-28]

### Added
- GitHub Copilot prompt files in `copilot/prompts/` directory for cross-platform support
  - requirements.prompt.md, design.prompt.md, tasks.prompt.md, next-task.prompt.md
  - commit.prompt.md, pr-prep.prompt.md, design-critic.chatmode.md
- `pre-push-code-reviewer` agent for critical review of unpushed commits
- `release-prep` command for preparing releases with quality checks and documentation updates
- `.gitignore` file with `localdocs/` exclusion
- AskUserQuestion tool requirement in requirements and design commands for better user interaction
- Rune CLI integration for task management in `next-task` command
- CLAUDE.md configuration section in README documenting AI behavior guidelines

### Changed
- Updated `peer-review-validator` agent to require consultation with at least two external AI systems (Gemini, Codex, or Q Developer)
- Changed `design-critic` agent to use Sonnet model instead of Opus for improved efficiency
- Enhanced `next-task` command to use `rune next --format json` for task retrieval and `rune complete` for tracking
- Improved `commit` command to prevent reverting code changes and exclude co-authored-by information
- Enhanced `requirements` command with better feature name proposal logic and general question prompts
- Updated spec-workflow.md with detailed documentation for commit, release-prep, and code review processes
- Refined `move_code_section.py` script to extract package name from source file
- Removed hyperbolic language from documentation (e.g., "comprehensive" → "design")
- Added guideline to CLAUDE.md about avoiding hyperbolic terms

## [Unreleased]

### Added
- CLAUDE.md file with global Claude Code instructions
- Go language rules and testing guidelines in language-rules/go.md
- Scripts directory with utility tools:
  - commit-diff-summary.sh for generating change summaries
  - copilot-pr-comments.sh for extracting PR comments
  - move_code_section.py for code manipulation
  - test-conversion directory with Go test conversion tools
- Scripts README documentation explaining usage

### Changed
- Renamed commands/commits.md to commands/commit.md for consistency
- Updated all agent documentation to use specs/ directory structure instead of agents/
- Enhanced command documentation to reflect specs/ path changes
- Improved spec-workflow.md with better structure and terminology
- Updated README.md with scripts directory usage instructions
- Modified JIRA ticket format to support 3-5 character prefixes