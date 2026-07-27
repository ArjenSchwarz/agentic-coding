# Agentic Coding process

This repository contains my current process for working with agentic coding assistants. It's focused around spec-driven development and has a number of helpful tools and commands. Feel free to use what you see here and/or propose improvements.

The framework now includes cross-platform support with GitHub Copilot prompt files, forge-aware review tooling that runs on both GitHub and GitLab, peer review that adapts to whether you're on a personal or a work machine, and improved workflow management with the rune CLI integration.

## Agents

The framework provides specialized AI agents for different aspects of development. These are defined for use in Claude Code, and not every tool supports sub-agents like this. Some agents lean on external AI systems when available — `peer-review-validator` consults the Codex/Kiro MCP agents, but only on personal machines (see [Personal vs. work projects](#personal-vs-work-projects-personal_projects)); elsewhere it falls back to Claude subagents so no code leaves the machine.

- **`code-simplifier`** - Reviews code for complexity reduction and maintainability improvements
- **`design-critic`** - Provides critical review of design documents and architecture proposals (now using Sonnet model for improved efficiency)
- **`efficiency-optimizer`** - Analyzes code for performance optimization opportunities
- **`local-review`** - Sonnet-powered local replacement for an automated CI review step. Forge-aware: it detects GitHub or GitLab from the git remote and reviews the open change request (code quality, bugs, performance, security, test coverage, plus whatever the project's `CLAUDE.md` mandates), posting a single review comment instead of consuming private CI/Actions minutes. See [Forge support](#forge-support-github--gitlab)
- **`peer-review-validator`** - Validates decisions by obtaining at least two independent peer perspectives. On personal machines (`PERSONAL_PROJECTS=1`) it consults external AI systems (Codex, Kiro); otherwise it spawns Claude subagents with distinct lenses so the same balanced review runs without sending code off-machine. See [Personal vs. work projects](#personal-vs-work-projects-personal_projects)
- **`pre-push-code-reviewer`** - Critically reviews unpushed commits before pushing to ensure code quality and spec adherence
- **`research-agent`** - Conducts research and generates structured reports (stolen from @sammcj)
- **`ui-ux-reviewer`** - Evaluates user interfaces for usability and accessibility improvements

## Skills

The framework includes Claude Code skills for the complete feature development workflow (detailed in [spec-workflow](spec-workflow.md)):

**Starwave Skills (Spec-Driven Development):**
- **`starwave:creating-spec`** - Main entry point that orchestrates the complete spec-driven workflow. Assesses scope, routes to appropriate workflow, and guides through all phases with built-in review gates.
- **`starwave:smolspec`** - Lightweight specification for minor changes (<80 LOC, 1-3 files)
- **`starwave:requirements`** - Generate and refine feature requirements in EARS format
- **`starwave:design`** - Create design documents based on approved requirements
- **`starwave:tasks`** - Convert designs into actionable implementation task lists

**Implementation Skills:**
- **`next-task`** - Execute the next group of tasks from the implementation plan
- **`make-it-so`** - Implement all remaining tasks from the spec automatically

**Utility Skills:**
- **`catchup`** - Get up to speed on branch changes by analyzing commits and modified files (inspired by [Shrivu Shankar](https://blog.sshh.io/p/how-i-use-every-claude-code-feature))
- **`commit`** - Format, stage, and commit changes with proper changelog management
- **`release-prep`** - Prepare the project for a new release with quality checks and documentation updates
- **`rune`** - Manages hierarchical task lists using the rune CLI tool. Provides efficient task creation, status tracking, phase organization, and batch operations for atomic updates.

Skills are invoked using slash commands (e.g., `/starwave:creating-spec`, `/commit`) and provide structured workflows with built-in approval gates.

## Workflow

The recommended way to start a new feature is with `/starwave:creating-spec`, which will:

1. Assess the scope of your feature
2. Route to either smolspec (small changes) or full spec workflow
3. Guide you through requirements → design → tasks phases
4. Offer to create a feature branch when planning is complete

Then implement using `/next-task` and commit with `/commit`.

Each phase requires explicit user approval before proceeding to ensure quality and alignment.

## Forge support (GitHub & GitLab)

The review tooling — the `local-review` agent and the `pr-pilot` / `pr-review-fixer` skills — works on both GitHub (via `gh`) and GitLab (via `glab`). You don't pick a forge: each workflow detects it from `git remote get-url origin` and adapts.

This is kept maintainable with a small adapter layer in `claude/forge-adapters/`:

- **`CONTRACT.md`** - Defines the work in *forge-neutral* terms. It establishes a shared vocabulary (a **CR** is a pull request on GitHub and a merge request on GitLab; a **thread** is a review thread or a discussion; the **CLI** is `gh` or `glab`) and a fixed set of named operations — `PREFLIGHT`, `CR_VIEW`, `CR_DIFF`, `THREADS_FETCH`, `CR_COMMENT`, `CR_MERGE`, and so on. The workflow files describe *what* to do using these operation names and never hard-code a CLI command.
- **`github.md`** / **`gitlab.md`** - Each adapter implements those same operation names with the concrete `gh` / `glab` commands for that forge.

A workflow runs `PREFLIGHT` to resolve the forge, reads the matching adapter, and then, wherever it needs to (say) post a comment, runs that adapter's `CR_COMMENT` command. The rule is strict: **never improvise a `gh`/`glab` command** — if an operation isn't in the adapter, the workflow stops and reports it rather than guessing.

**Why it's built this way:** GitHub and GitLab differ only in a small, bounded set of operations (mostly comment/discussion surfaces and id formats — `#123` vs `!1`). Keeping the workflow logic in one place and the per-forge commands in adapters avoids maintaining two near-identical copies that drift apart. Adding a third forge later means writing one new adapter, not editing every workflow.

## Personal vs. work projects (`PERSONAL_PROJECTS`)

Some agents are more useful when they can consult external AI systems (Codex, Kiro) for a genuinely independent second opinion. On a work machine that's often not acceptable — sending source code to a third-party model can breach client or employer policy. The `PERSONAL_PROJECTS` environment variable is the switch that resolves this.

- **`PERSONAL_PROJECTS=1`** (set this only on your own machines) - external-model mode. Agents may send the work to external AI systems.
- **unset, empty, or any other value** (the default) - safe mode. No code leaves the machine; agents that wanted an external opinion fall back to spawning Claude subagents with distinct review lenses instead.

The default is the safe one on purpose: a machine that hasn't opted in never sends code out, so forgetting to configure it fails closed rather than open. `peer-review-validator` is the agent that uses this today — it states in its output which mode it ran in, so a reader knows whether the extra perspectives came from distinct external models or from Claude subagents.

Set it in your shell profile on personal machines:

```bash
export PERSONAL_PROJECTS=1
```

If your machine holds both personal and work repos, you usually don't want it set globally. Scope it to a directory tree instead — for example, when all personal work lives under `~/projects/personal/`, add this to your `.zshrc`:

```bash
case "$PWD/" in
  "$HOME/projects/personal/"*) export PERSONAL_PROJECTS=1 ;;
esac
```

This evaluates at shell startup against the directory the shell opened in, which suits opening a terminal (or an editor's integrated terminal) directly in a project. If you want it to follow `cd` between trees within an existing shell, wrap the same check in a `chpwd` hook so it re-runs on every directory change:

```bash
# In .zshrc
personal_projects_guard() {
  case "$PWD/" in
    "$HOME/projects/personal/"*) export PERSONAL_PROJECTS=1 ;;
    *) unset PERSONAL_PROJECTS ;;
  esac
}
autoload -Uz add-zsh-hook
add-zsh-hook chpwd personal_projects_guard   # run on every directory change
personal_projects_guard                      # and once now, for the shell's starting directory
```

The `*)` branch matters: it `unset`s the flag when you leave the personal tree, so the setting follows `cd` in both directions instead of staying on for the rest of the session. The final call applies the rule to the directory the shell started in, since `chpwd` only fires on subsequent changes.

## File Structure

All Claude Code configuration files are organized under the `claude/` directory:

- `claude/CLAUDE.md` - User-level instructions that guide AI behavior
- `claude/agents/` - Specialized AI agents for different development tasks
- `claude/skills/` - Skills for the development workflow (invoked via slash commands)
- `claude/forge-adapters/` - Forge-neutral operation contract (`CONTRACT.md`) and per-forge command implementations (`github.md`, `gitlab.md`) shared by the review tooling (see [Forge support](#forge-support-github--gitlab))
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