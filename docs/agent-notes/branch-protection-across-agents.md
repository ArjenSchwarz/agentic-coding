# Branch Protection Across AI Coding Agents

How to prevent AI coding agents from accidentally modifying protected branches (`main`/`master`). Covers Claude Code, Kiro CLI, GitHub Copilot CLI, and OpenAI Codex CLI.

Research date: 2026-03-16.

## Operations to protect against

| Category | Commands |
|---|---|
| Push | `git push origin main`, `git push` (on main), force push, `--delete`, refspec `:main` |
| History rewrite | `git reset --hard`, `git rebase`, `git commit --amend` |
| Destructive | `git checkout .`, `git restore .`, `git clean -f` |
| Branch manipulation | `git branch -D main`, `git branch -f main` |
| gh CLI | `gh repo delete`, `gh repo edit --default-branch`, `gh pr merge --admin` |
| gh API | `gh api -X DELETE/PATCH .../refs/heads/main`, branch protection, rulesets |
| MCP servers | `mcp__github__push_files`, `mcp__git__git_push` (tool-specific, not command-based) |

---

## Claude Code

**Status**: Implemented in this repo (`claude/hooks/no-push-main.py`).

**Mechanism**: `PreToolUse` hooks defined in `.claude/settings.json`. A hook script receives tool input as JSON on stdin and exits non-zero to block execution.

**Configuration** (`.claude/settings.json`):
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

**Capabilities**:
- Full branch-aware logic (can check current branch via `git rev-parse`)
- Parses flags, refspecs, and complex command variants
- Covers both `git` and `gh` CLI commands in a single hook
- `gh api` mutation detection: HTTP method, `-f`/`-F` field flags, `--input`, GraphQL mutations
- Hard block — non-zero exit prevents the command from running
- Global via symlink to `~/.claude/hooks/`

---

## Kiro CLI (AWS)

**Mechanism 1: `deniedCommands`** — regex patterns in agent config that hard-block matching commands. Simple but no branch awareness (can't check which branch you're on).

**Configuration** (`.kiro/agents/<name>.json`):
```json
{
  "toolsSettings": {
    "shell": {
      "deniedCommands": [
        "git\\s+push\\s+.*\\b(main|master)\\b",
        "git\\s+push\\s+--force",
        "git\\s+push\\s+-f",
        "git\\s+push\\s+--delete\\s+\\S+\\s+(main|master)",
        "git\\s+reset\\s+--hard",
        "git\\s+rebase",
        "git\\s+commit\\s+.*--amend",
        "git\\s+checkout\\s+(--\\s+)?\\.",
        "git\\s+restore\\s+.*\\.",
        "git\\s+clean\\s+.*-[a-zA-Z]*f",
        "git\\s+branch\\s+-D\\s+(main|master)",
        "git\\s+branch\\s+(-f|--force)\\s+(main|master)"
      ]
    }
  }
}
```

**Mechanism 2: `preToolUse` hook** — similar to Claude Code but exit code **2** blocks (not 1). Receives tool invocation JSON on stdin. Configured in the same agent JSON file under `hooks.preToolUse`.

```json
{
  "hooks": {
    "preToolUse": [
      {
        "command": "python3 ~/.kiro/hooks/no-push-main.py"
      }
    ]
  }
}
```

To reuse the Claude Code script, adapt the exit code:
```python
sys.exit(2)  # Kiro uses exit code 2 to block, not 1
```

**Capabilities**:
- `deniedCommands`: regex matching, no branch awareness, evaluated before hooks
- `preToolUse`: full arbitrary logic, branch-aware
- Permission model also has `allowedCommands`, `denyByDefault`, `autoAllowReadonly`

**Limitations**:
- Config is per-agent (`.kiro/agents/<name>.json`), not project-level
- No global `~/.kiro/settings.json` for command restrictions (open feature request #5480)
- Steering files (`.kiro/steering/*.md`) are advisory only, not enforced

---

## GitHub Copilot CLI

**Mechanism 1: `--deny-tool` flags** — pattern-based blocking at launch. Deny rules always take precedence, even with `--allow-all`.

```bash
copilot-cli \
  --deny-tool='shell(git push)' \
  --deny-tool='shell(git reset --hard)' \
  --deny-tool='shell(git rebase)' \
  --deny-tool='shell(git commit --amend)' \
  --deny-tool='shell(git checkout .)' \
  --deny-tool='shell(git restore .)' \
  --deny-tool='shell(git clean -f)' \
  --deny-tool='shell(git branch -D)' \
  --deny-tool='shell(git branch -f)'
```

This is broad (blocks `git push` entirely, not just to main). For branch-aware logic, use hooks.

**Mechanism 2: `preToolUse` hooks** (`.github/hooks/*.json`) — runs a script that returns JSON with a permission decision.

Hook definition (`.github/hooks/protect-main.json`):
```json
{
  "event": "preToolUse",
  "matcher": "shell",
  "command": "python3 .github/hooks/no-push-main.py"
}
```

The script reads JSON from stdin and writes JSON to stdout:
```python
# To block:
print(json.dumps({"permissionDecision": "deny", "reason": "Pushing to main is not allowed."}))

# To allow:
print(json.dumps({"permissionDecision": "allow"}))
```

**Capabilities**:
- `--deny-tool`: reliable hard block, pattern matching only, no branch awareness
- `preToolUse` hooks: full logic, branch-aware, committed to repo for team use
- Also has `--available-tools` (whitelist) and `--excluded-tools` (blacklist) for tool-level filtering

**Limitations**:
- Hook failures (crashes, timeouts) are logged and **skipped**, never blocking — hooks are not a hard security boundary
- `--deny-tool` rules are CLI flags only, not configurable in settings JSON files (as of March 2026)
- Different JSON protocol than Claude Code (returns JSON on stdout instead of using exit codes)

---

## OpenAI Codex CLI

**Mechanism 1: Execpolicy rules** (`~/.codex/rules/default.rules`) — Starlark-based prefix matching. The primary enforcement mechanism.

```python
# Branch protection rules
prefix_rule("git push", decision="forbidden")
prefix_rule("git reset --hard", decision="forbidden")
prefix_rule("git rebase", decision="forbidden")
prefix_rule("git commit --amend", decision="forbidden")
prefix_rule("git checkout .", decision="forbidden")
prefix_rule("git checkout -- .", decision="forbidden")
prefix_rule("git restore .", decision="forbidden")
prefix_rule("git clean -f", decision="forbidden")
prefix_rule("git branch -D", decision="forbidden")
prefix_rule("git branch -f", decision="forbidden")
```

Test rules with: `codex execpolicy check --rules <file> -- <command>`

**Mechanism 2: Sandbox** — the default `workspace-write` mode already provides strong implicit protection:
- `.git/` directory is read-only (blocks `git commit`, `git rebase`, etc.)
- Network access is disabled (blocks `git push`)
- Enforced at OS level (Seatbelt on macOS, Landlock on Linux)

**Mechanism 3: `AGENTS.md`** — soft guidance like "never push to main". Not enforced.

**Capabilities**:
- Execpolicy: reliable, prefix-matching, strictest matching rule wins
- Sandbox: strongest default protection of all four tools
- `requirements.toml` for admin-enforced policies that users can't override

**Limitations**:
- No `PreToolUse` hook yet (requested in issue #13014, experimental hooks only cover session lifecycle)
- Execpolicy is prefix-matching only — no branch awareness, can't check current branch
- Rules like `prefix_rule("git push", decision="forbidden")` block all pushes, not just to main
- `AGENTS.md` is advisory, not enforced

---

## Comparison

| Feature | Claude Code | Kiro | Copilot CLI | Codex CLI |
|---|---|---|---|---|
| Hook system | PreToolUse (exit 1) | preToolUse (exit 2) | preToolUse (JSON stdout) | Not yet (session-level only) |
| Pattern blocking | No | `deniedCommands` (regex) | `--deny-tool` (pattern) | Execpolicy (prefix) |
| Branch-aware logic | Yes (via hook) | Yes (via hook) | Yes (via hook) | No |
| Hard enforcement | Yes | Yes | No (hook failures skip) | Yes (execpolicy + sandbox) |
| Global config | `~/.claude/settings.json` | Per-agent only | CLI flags only | `~/.codex/rules/` |
| Sandbox | No | No | No | Yes (strongest default) |
| `gh` CLI coverage | Yes (in hook) | Via hook (needs adaptation) | Via hook (needs adaptation) | Via execpolicy (broad) |
| MCP tool coverage | Possible (per-tool matcher) | N/A | N/A | N/A |

## Recommendations

1. **Claude Code**: Covered by `no-push-main.py` for both `git` and `gh` commands. MCP servers can be added per-tool if needed, but the official GitHub MCP server already omits the most dangerous operations.

2. **Kiro**: Use `deniedCommands` for broad protection plus a `preToolUse` hook (adapted from the Claude Code script) for branch-aware logic. Add `gh` patterns to `deniedCommands` as well. Main gap is per-agent config — you'd need to add it to each agent definition.

3. **Copilot CLI**: Use `--deny-tool` flags as the reliable baseline (consider a shell alias or wrapper). Add `.github/hooks/` for branch-aware logic, but be aware hook failures don't block. The `--deny-tool` flags are the real safety net. Include `gh` patterns in deny rules.

4. **Codex CLI**: The sandbox already prevents most damage in default mode. Add execpolicy rules for explicit protection. Accept that rules are broad (all pushes blocked, not just main) until `PreToolUse` hooks ship. Add `gh` rules too: `prefix_rule("gh repo delete", decision="forbidden")` etc.

5. **Git hooks**: A standard git `pre-push` hook works across all tools as a fallback. It won't catch `reset --hard`, `rebase`, or `gh` commands, but it's the universal safety net for git pushes:

```bash
#!/bin/bash
# .git/hooks/pre-push
while read local_ref local_sha remote_ref remote_sha; do
  if echo "$remote_ref" | grep -qE "refs/heads/(main|master)$"; then
    echo "Pushing to main/master is blocked by pre-push hook."
    exit 1
  fi
done
```

This can also be installed globally via `git config --global core.hooksPath`.

---

## `gh` CLI and `gh api` — now covered for Claude Code

**Status**: Implemented in `no-push-main.py` as of 2026-03-16.

The `gh` CLI operates over HTTP, bypassing all local git hooks. The Claude Code hook now also inspects `gh` commands.

### What's blocked

| Category | Commands blocked |
|---|---|
| Repo destruction | `gh repo delete` |
| Settings changes | `gh repo edit --default-branch` |
| Force sync | `gh repo sync --force --branch main/master` |
| Admin merge | `gh pr merge --admin` (bypasses required checks) |
| API ref mutation | `gh api -X DELETE/PATCH/PUT/POST .../refs/heads/main` |
| Branch protection | `gh api -X DELETE .../branches/main/protection` |
| Ruleset deletion | `gh api -X DELETE .../rulesets/<id>` |
| Implicit POST | `gh api .../refs/heads/main -f sha=...` (field flags imply mutation) |
| Input file | `gh api --input file .../refs/heads/main` |
| GraphQL mutation | `gh api graphql -f query='mutation...' .../refs/heads/main` |

### What's allowed

- `gh pr merge 42 --squash` — normal PR merges
- `gh pr list`, `gh pr view`, `gh issue list` — read-only commands
- `gh api -X GET .../refs/heads/main` — read-only API calls
- `gh api .../refs/heads/feature-x -X DELETE` — mutating non-protected branches

### Mutation detection for `gh api`

The hook detects mutating intent via:
1. Explicit HTTP method: `-X DELETE`, `-X PATCH`, `-X PUT`, `-X POST`
2. Field flags: `-f` or `-F` without `-X GET` (implies POST)
3. Input file: `--input` flag
4. GraphQL: `graphql` endpoint + `mutation` keyword in query

Only mutating calls that target protected branch refs (`refs/heads/main`, `branches/main/protection`) or rulesets are blocked. Read-only calls always pass.

### Remaining gap: `gh api` with indirect payloads

A `gh api` call where the branch name is only in a JSON file (`--input payload.json`) and not in the URL cannot be detected by command-line inspection alone. This is a theoretical risk — in practice, agents construct commands inline rather than using separate payload files.

---

## Remaining gap: MCP servers

MCP tools bypass the `Bash` tool entirely, so the current hook (which matches `Bash`) cannot see them. This affects:

- **GitHub's official MCP server** (`github/github-mcp-server`): has `push_files`, `merge_pull_request`, `create_or_update_file`. Deliberately omits `delete_branch`, force push, and ref manipulation. The `--read-only` flag disables all writes.
- **Anthropic's `mcp-server-git`**: 12 read-only tools. No push/pull/merge. Safe by design.
- **`cyanheads/git-mcp-server`**: 28 tools including `git_push`, `git_reset`, `git_rebase`. Shells out to git, so local git hooks still apply.

### How to protect against MCP tools in Claude Code

Claude Code's `PreToolUse` matcher supports regex, so you can match MCP tools:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__github__push_files",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/check-mcp-github.py"
          }
        ]
      }
    ]
  }
}
```

The hook script would need to inspect `tool_input` JSON (structured parameters like `branch`, `ref`) instead of parsing a command string. Each MCP server has its own parameter schema.

### Practical assessment

For most setups, MCP server risk is low:
- The official GitHub MCP server already omits the most dangerous operations
- `mcp-server-git` is read-only
- Community servers that shell out to git still hit local git hooks
- The real risk surface is `gh` commands via `Bash` (now covered)
