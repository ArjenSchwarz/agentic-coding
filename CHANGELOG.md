# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2026-04-11]

### Changed
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