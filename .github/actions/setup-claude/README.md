# Setup Claude Configuration Action

This GitHub Action symlinks Claude Code configuration directories from the `agentic-coding` repository to `~/.claude/`.

## What it does

1. Checks out the `agentic-coding` repository (main branch by default)
2. Creates symlinks from the repository to `~/.claude/` for:
   - `agents/` → `~/.claude/agents`
   - `commands/` → `~/.claude/commands`
   - `rules/` → `~/.claude/rules`
   - `scripts/` → `~/.claude/scripts`
   - `skills/` → `~/.claude/skills`
   - `CLAUDE.md` → `~/.claude/CLAUDE.md`

## Usage

### Basic usage

```yaml
- name: Setup Claude Configuration
  uses: ArjenSchwarz/agentic-coding/.github/actions/setup-claude@main
```

### With custom inputs

```yaml
- name: Setup Claude Configuration
  uses: ArjenSchwarz/agentic-coding/.github/actions/setup-claude@main
  with:
    ref: 'develop'  # Use a different branch
    checkout-path: '.my-claude-config'  # Use a custom checkout path
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `repository` | Repository to checkout | No | `ArjenSchwarz/agentic-coding` |
| `ref` | Branch, tag, or SHA to checkout | No | `main` |
| `checkout-path` | Path where the repository will be checked out | No | `.agentic-coding-setup` |

## Example workflow

```yaml
name: My Workflow with Claude

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout my repository
        uses: actions/checkout@v4

      - name: Setup Claude Configuration
        uses: ArjenSchwarz/agentic-coding/.github/actions/setup-claude@main

      - name: Run Claude Code
        run: |
          # Your Claude Code commands here
          # Claude will now have access to your custom agents, commands, etc.
          claude --print "Your prompt here"
```

## Notes

- The action creates symlinks, so the original repository checkout remains in the workspace at the specified `checkout-path`
- If you need to use a different branch or tag, use the `ref` input
- The symlinks point to absolute paths, so they remain valid throughout the workflow
