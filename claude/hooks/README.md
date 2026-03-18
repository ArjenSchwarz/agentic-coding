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

A `PreToolUse` hook that protects `main`/`master` branches from accidental modification. Covers pushes, history rewrites, destructive operations, and branch manipulation.

**Push protection:**

| Command | Reason |
|---|---|
| `git push origin main` | Direct push to protected branch |
| `git push` (while on main) | Implicit push to protected branch |
| `git push --force origin main` | Force push to protected branch |
| `git push -f` (while on main) | Force push while on protected branch |
| `git push --force-with-lease origin main` | Force-with-lease to protected branch |
| `git push -u origin main` | Push with upstream set to protected branch |
| `git push origin feature:main` | Refspec targeting protected branch |
| `git push --delete origin main` | Deleting remote protected branch |
| `git push origin :main` | Deleting remote protected branch (refspec) |

**History rewrite protection** (while on main/master):

| Command | Reason |
|---|---|
| `git reset --hard` | Moves branch pointer back, loses commits |
| `git rebase` | Rewrites commit history |
| `git commit --amend` | Rewrites the last commit |

**Destructive operation protection** (while on main/master):

| Command | Reason |
|---|---|
| `git checkout .` / `git checkout -- .` | Discards uncommitted changes |
| `git restore .` / `git restore --staged .` | Discards uncommitted changes |
| `git clean -f` | Deletes untracked files permanently |

**Branch manipulation protection:**

| Command | Reason |
|---|---|
| `git branch -D main` | Deletes the local protected branch |
| `git branch -f main <ref>` | Force-moves the protected branch pointer |

**GitHub CLI (`gh`) protection:**

| Command | Reason |
|---|---|
| `gh repo delete` | Deletes the repository |
| `gh repo edit --default-branch` | Changes the default branch |
| `gh repo sync --force --branch main` | Force-syncs protected branch |
| `gh pr merge --admin` | Merges PR bypassing required checks |
| `gh api -X DELETE .../git/refs/heads/main` | Deletes protected branch via API |
| `gh api -X PATCH .../git/refs/heads/main` | Force-updates protected ref via API |
| `gh api -X DELETE .../branches/main/protection` | Removes branch protection rules |
| `gh api -X DELETE .../rulesets/<id>` | Deletes repository rulesets |
| `gh api .../refs/heads/main -f sha=...` | Implicit POST updating protected ref |
| `gh api --input file .../refs/heads/main` | Mutating call via input file |
| `gh api graphql -f query='mutation...' .../refs/heads/main` | GraphQL mutation targeting protected ref |

**Allowed actions:**

- `git push origin feature-branch` — pushes to non-protected branches
- `git push --force origin feature-x` — force pushes to non-protected branches
- `git reset --soft` — safe resets on any branch
- `git commit -m "message"` — normal commits (only `--amend` is blocked)
- `git branch -D feature-x` — deleting non-protected branches
- `git clean -n` — dry-run clean (only `-f` is blocked)
- `gh pr merge 42 --squash` — normal PR merges (only `--admin` is blocked)
- `gh pr list`, `gh pr view` — read-only gh commands
- `gh api -X GET .../refs/heads/main` — read-only API calls
- Any non-git/gh command

**How it works:**

The hook receives tool input as JSON on stdin. It checks the command against five categories: git pushes, history rewrites, destructive operations, branch manipulation, and gh CLI commands. For git commands that don't name a branch explicitly, it checks the current branch via `git rev-parse`. For `gh api` calls, it detects mutating intent via HTTP method (`-X DELETE/PATCH/PUT/POST`), field flags (`-f`/`-F`), `--input`, or GraphQL mutations, and blocks those targeting protected branch refs. If blocked, it exits non-zero with a message on stderr, which Claude sees and respects.

## Adding New Hooks

1. Add the hook script to this directory
2. Make it executable: `chmod +x your-hook.py`
3. Register it in `.claude/settings.json` with the appropriate event (`PreToolUse`, `PostToolUse`, etc.)
4. Document it in this README
