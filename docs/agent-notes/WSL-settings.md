# WSL2 Sandbox Settings

## CLAUDE_CODE_SUBPROCESS_ENV_SCRUB

Set `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` to strip Anthropic and cloud provider credentials from all child process environments (Bash tool, hooks, MCP stdio servers). The parent Claude process retains credentials for API calls; subprocesses cannot read them.

On Linux/WSL2 this also runs Bash subprocesses in an isolated PID namespace. Side effect: `ps`, `pgrep`, and `kill` inside sandboxed commands cannot see or signal host processes.

macOS only does the env scrubbing — no PID namespace isolation.

### Prerequisites (WSL2 only, WSL1 not supported)

```bash
sudo apt-get install bubblewrap socat
```

## CLAUDE_CODE_SCRIPT_CAPS

Limits how many times a script can be invoked per session when `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` is set. Value is a JSON object with substring keys and integer call limits:

```
CLAUDE_CODE_SCRIPT_CAPS='{"deploy.sh": 2}'
```

Matching is substring-based against command text, so shell-expansion tricks still count against the cap. Runtime fan-out via `xargs` or `find -exec` is not detected.

## When to use

Enable for environments with sensitive credentials in the shell environment, particularly client work where API keys or cloud provider tokens are present.
