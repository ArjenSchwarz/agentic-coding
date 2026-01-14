#!/bin/bash
# Sync claude configuration files to ~/.claude
# The real files are in this repo's claude/ directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_CLAUDE_DIR="$(cd "$SCRIPT_DIR/../claude" && pwd)"

# Create symlinks to ~/.claude
ln -sfn "$REPO_CLAUDE_DIR/CLAUDE.md" ~/.claude/CLAUDE.md
ln -sfn "$REPO_CLAUDE_DIR/agents" ~/.claude/agents
ln -sfn "$REPO_CLAUDE_DIR/skills" ~/.claude/skills
ln -sfn "$REPO_CLAUDE_DIR/../scripts" ~/.claude/scripts
ln -sfn "$REPO_CLAUDE_DIR/rules" ~/.claude/rules

echo "Symlinked to ~/.claude:"
echo "  CLAUDE.md -> $REPO_CLAUDE_DIR/CLAUDE.md"
echo "  agents/   -> $REPO_CLAUDE_DIR/agents"
echo "  skills/   -> $REPO_CLAUDE_DIR/skills"
echo "  scripts/  -> $REPO_CLAUDE_DIR/../scripts"
echo "  rules/    -> $REPO_CLAUDE_DIR/rules"
