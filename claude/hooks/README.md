# Hooks

Claude Code [hooks](https://docs.anthropic.com/en/docs/claude-code/hooks) that run automatically during tool use. These are synced to `~/.claude/hooks/` by `scripts/sync-claude.sh` so they apply globally across all projects.

## Setup

Hooks are registered in each project's `.claude/settings.json` under the `hooks` key. The hook commands reference `~/.claude/hooks/` (the symlinked location) so they work in any project directory.

Example `.claude/settings.json` entry:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/no-push-main.py"
          }
        ]
      }
    ]
  }
}
```

## Available Hooks

### no-push-main.py

A `PreToolUse` hook that prevents Claude from pushing to protected branches (`main`/`master`).

**Blocked actions:**

| Command | Reason |
|---|---|
| `git push origin main` | Direct push to protected branch |
| `git push origin master` | Direct push to protected branch |
| `git push` (while on main) | Implicit push to protected branch |
| `git push --force origin main` | Force push to protected branch |
| `git push -f` (while on main) | Force push while on protected branch |
| `git push --force-with-lease origin main` | Force-with-lease to protected branch |
| `git push -u origin main` | Push with upstream set to protected branch |
| `git push origin feature:main` | Refspec targeting protected branch |

**Allowed actions:**

- `git push origin feature-branch` — pushes to non-protected branches
- `git push --force origin feature-x` — force pushes to non-protected branches
- Any non-git command

**How it works:**

The hook receives tool input as JSON on stdin. It strips flags from the `git push` command to extract the remote and refspec, then checks whether the target branch (explicit or current) is protected. If blocked, it exits non-zero with a message on stderr, which Claude sees and respects.

## Adding New Hooks

1. Add the hook script to this directory
2. Make it executable: `chmod +x your-hook.py`
3. Register it in `.claude/settings.json` with the appropriate event (`PreToolUse`, `PostToolUse`, etc.)
4. Document it in this README
