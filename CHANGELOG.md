# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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