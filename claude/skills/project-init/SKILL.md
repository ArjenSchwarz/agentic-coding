---
name: project-init
description: Initialize Claude Code project settings with standard hooks and configuration. Use when setting up a new project for Claude Code or adding standard configuration to an existing project.
---

# Project Init

Initialize a project with standard Claude Code configuration.

## What It Does

Adds a SessionStart hook to `.claude/settings.json` that pulls in user-level configuration when running in sandboxed environments (GitHub Actions, online Claude Code).

The hook runs `claude-remote.sh` via curl to set up the environment.

## Usage

Run the setup script:

```bash
~/.claude/skills/project-init/scripts/setup-project.sh
```

The script:
- Creates `.claude/settings.json` if it doesn't exist
- Merges the hook into existing settings without overwriting
- Is idempotent (safe to run multiple times)
- Requires `jq` for JSON manipulation

## Batch Setup

To add the hook to multiple existing projects:

```bash
for dir in ~/projects/*; do
  (cd "$dir" && ~/.claude/skills/project-init/scripts/setup-project.sh)
done
```
