# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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