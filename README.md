# Agentic Coding process

This repository contains my current process for working with agentic coding assistants. It's focused around spec-driven development and has a number of helpful tools and commands. Feel free to use what you see here and/or propose improvements.

The framework now includes cross-platform support with GitHub Copilot prompt files, enhanced peer review capabilities with multiple AI system consultation, and improved workflow management with the rune CLI integration.

## Commands

The framework includes commands for a complete feature development workflow (detailed in [spec-workflow](spec-workflow.md)):

- **`catchup`** - Get up to speed on branch changes by analyzing commits and modified files (inspired by [Shrivu Shankar](https://blog.sshh.io/p/how-i-use-every-claude-code-feature))
- **`requirements`** - Generate and refine feature requirements in EARS format
- **`design`** - Create design documents based on approved requirements
- **`tasks`** - Convert designs into actionable implementation task lists
- **`next-task`** - Execute the next group of tasks from the implementation plan
- **`commit`** - Format, stage, and commit changes with proper changelog management
- **`release-prep`** - Prepare the project for a new release with quality checks and documentation updates

## Agents

The framework provides specialized AI agents for different aspects of development. These are defined for use in Claude Code, and not every tool supports sub-agents like this. Some agents have dependencies on external CLI tools (e.g., peer-review-validator requires Gemini CLI, Codex CLI, or Q Developer CLI for consulting external AI systems).

- **`code-simplifier`** - Reviews code for complexity reduction and maintainability improvements
- **`design-critic`** - Provides critical review of design documents and architecture proposals (now using Sonnet model for improved efficiency)
- **`efficiency-optimizer`** - Analyzes code for performance optimization opportunities
- **`peer-review-validator`** - Validates decisions by consulting with at least two external AI systems (Gemini, Codex, or Q Developer) to ensure balanced perspective
- **`pre-push-code-reviewer`** - Critically reviews unpushed commits before pushing to ensure code quality and spec adherence
- **`research-agent`** - Conducts research and generates structured reports (stolen from @sammcj)
- **`ui-ux-reviewer`** - Evaluates user interfaces for usability and accessibility improvements

## Skills

The framework includes Claude Code skills that provide specialized workflows:

- **`creating-spec`** - Orchestrates the complete spec-driven workflow from initial feature idea through requirements, design, and task planning. This skill guides you through all three phases with built-in review gates and decision logging.
- **`rune`** - Manages hierarchical task lists using the rune CLI tool. Provides efficient task creation, status tracking, phase organization, and batch operations for atomic updates.

Skills provide more structured, multi-step workflows compared to individual commands, with built-in approval gates and validation steps.

## Workflow

1. Start with `requirements` to define what needs to be built
2. Use `design` to plan the architecture and approach
3. Generate implementation steps with `tasks`
4. Execute incrementally using `next-task`
5. Commit progress using `commit`

Each phase requires explicit user approval before proceeding to ensure quality and alignment.

## File Structure

All Claude Code configuration files are organized under the `claude/` directory:

- `claude/CLAUDE.md` - User-level instructions that guide AI behavior
- `claude/agents/` - Specialized AI agents for different development tasks
- `claude/commands/` - Slash commands for the development workflow
- `claude/skills/` - Multi-step workflow skills with approval gates
- `claude/rules/` - Additional rules and references:
  - `claude/rules/language-rules/` - Language-specific coding guidelines (e.g., Go patterns)
  - `claude/rules/references/` - Reference documentation formats

Feature work is organized in `specs/{feature_name}/` directories containing:
- `requirements.md` - Feature requirements in EARS format
- `design.md` - Design document
- `tasks.md` - Implementation task checklist
- `decision_log.md` - Decisions and rationales

## GitHub Copilot Integration

The `copilot/prompts/` directory contains prompt files for GitHub Copilot users. These prompts mirror the command functionality and can be used directly in GitHub Copilot:

- **`requirements.prompt.md`** - Requirements gathering prompt
- **`design.prompt.md`** - Design document creation prompt
- **`tasks.prompt.md`** - Task planning prompt
- **`next-task.prompt.md`** - Next task execution prompt
- **`commit.prompt.md`** - Commit formatting and changelog management prompt
- **`pr-prep.prompt.md`** - Pull request preparation prompt
- **`design-critic.chatmode.md`** - Design critique chat mode prompt

## Scripts Directory

The `scripts/` directory contains helper scripts for AI-assisted development:

- **`sync-claude.sh`** - Syncs all configuration files from `claude/` to `~/.claude/` by creating symlinks

To set up your global Claude Code configuration, run:
```bash
./scripts/sync-claude.sh
```

This creates symlinks from `~/.claude/` pointing to the files in this repository's `claude/` directory, keeping your configuration centralized and version-controlled.

This framework is designed to work with various AI coding tools including Claude Code, GitHub Copilot, and Cline.

## GitHub Action

For CI/CD pipelines and automated workflows, you can use the included GitHub Action to set up Claude configuration in your workflows. This action symlinks all configuration directories to `~/.claude/` so Claude Code can access your custom agents, commands, language rules, scripts, and skills.

### Basic Usage

```yaml
steps:
  - name: Setup Claude Configuration
    uses: ArjenSchwarz/agentic-coding/.github/actions/setup-claude@main
```

### What It Does

The action automatically:
1. Checks out the `agentic-coding` repository
2. Creates symlinks from the repository's `claude/` directory to `~/.claude/`:
   - `claude/agents/` → `~/.claude/agents`
   - `claude/commands/` → `~/.claude/commands`
   - `claude/skills/` → `~/.claude/skills`
   - `claude/rules/` → `~/.claude/rules`
   - `claude/CLAUDE.md` → `~/.claude/CLAUDE.md`

### Advanced Usage

You can customize the action behavior with inputs:

```yaml
steps:
  - name: Setup Claude Configuration
    uses: ArjenSchwarz/agentic-coding/.github/actions/setup-claude@main
    with:
      ref: 'develop'  # Use a different branch or tag
      checkout-path: '.my-claude-config'  # Custom checkout path
```

### Complete Example

```yaml
name: CI with Claude Code

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Claude Configuration
        uses: ArjenSchwarz/agentic-coding/.github/actions/setup-claude@main

      - name: Run Claude Code
        run: |
          # Your Claude Code commands here
          # All custom agents, commands, etc. are now available
          claude --print "Analyze this codebase"
```

See [.github/actions/setup-claude/README.md](.github/actions/setup-claude/README.md) for complete documentation.

## CLAUDE.md Configuration

The `claude/CLAUDE.md` file contains user-level instructions that guide AI behavior when working with this framework. Key guidelines include:

- Emphasis on simplicity and understandable code
- Avoiding hyperbolic language and sycophantic responses
- Feature-based development using the specs directory structure
- Language-specific rules (e.g., Go development patterns in `claude/rules/language-rules/go.md`)
- Mandatory use of linters and validators after writing code

Run `./scripts/sync-claude.sh` to symlink these configurations to your global `~/.claude/` directory, or copy them to a project-specific `.claude/` directory.