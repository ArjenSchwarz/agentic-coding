#!/usr/bin/env python3
"""
Analyze Claude Code session logs to generate permissions configuration.
"""

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path


def slugify_path(path: str) -> str:
    """Convert absolute path to Claude's slugified format."""
    return path.replace("/", "-")


def get_sessions_dir(project_path: str) -> Path:
    """Get session logs directory for a project."""
    abs_path = os.path.abspath(project_path)
    return Path.home() / ".claude" / "projects" / slugify_path(abs_path)


def extract_command_prefixes(command: str) -> set:
    """Extract base commands from a bash command string."""
    if not command:
        return set()

    command = command.strip()
    parts = re.split(r'\s*(?:&&|\|\|)\s*', command)
    prefixes = set()

    skip = {'if', 'then', 'else', 'fi', 'for', 'do', 'done', 'while', 'case',
            'esac', '[', '[[', 'true', 'false', 'echo', 'printf', 'cd',
            'export', 'source', '.', 'EOF', '}', '{'}

    for part in parts:
        part = part.strip()
        if not part or part[0] in '{[("\'':
            continue
        words = part.split()
        if words and words[0] not in skip:
            prefixes.add(words[0])

    return prefixes


def analyze_sessions(project_path: str) -> dict:
    """Analyze all session logs for a project."""
    sessions_dir = get_sessions_dir(project_path)

    if not sessions_dir.exists():
        return {'bash_commands': {}, 'mcp_tools': set(), 'session_count': 0}

    bash_commands = defaultdict(int)
    mcp_tools = set()
    session_count = 0

    for session_file in sessions_dir.glob('*.jsonl'):
        session_count += 1
        try:
            with open(session_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        content = entry.get('message', {}).get('content', [])
                        if not isinstance(content, list):
                            continue

                        for item in content:
                            if not isinstance(item, dict) or item.get('type') != 'tool_use':
                                continue

                            tool_name = item.get('name', '')

                            if tool_name.startswith('mcp__'):
                                mcp_tools.add(tool_name)

                            if tool_name == 'Bash':
                                cmd = item.get('input', {}).get('command', '')
                                for prefix in extract_command_prefixes(cmd):
                                    bash_commands[prefix] += 1
                    except json.JSONDecodeError:
                        continue
        except Exception:
            continue

    return {
        'bash_commands': dict(bash_commands),
        'mcp_tools': mcp_tools,
        'session_count': session_count
    }


# Known development commands mapped to permission patterns
DEV_COMMANDS = {
    # Build & package managers
    'make', 'go', 'npm', 'npx', 'yarn', 'pnpm', 'pip', 'pip3', 'python', 'python3',
    'cargo', 'rustc', 'swift', 'swiftc', 'gradle', 'mvn', 'bundle', 'gem',
    'composer', 'mix', 'stack', 'cabal', 'dotnet', 'uv',
    # Version control
    'git', 'gh',
    # Linting & formatting
    'eslint', 'prettier', 'golangci-lint', 'gofmt', 'black', 'flake8', 'pylint',
    'mypy', 'rubocop', 'rustfmt', 'clippy', 'swiftlint', 'swiftformat',
    # Testing
    'pytest', 'jest', 'mocha', 'vitest', 'rspec',
    # Build tools
    'cmake', 'ninja', 'bazel',
    # Container & cloud
    'docker', 'docker-compose', 'kubectl', 'helm', 'terraform', 'aws', 'gcloud', 'az',
    # Utilities
    'jq', 'yq', 'curl', 'wget', 'rune',
}

FILESYSTEM_COMMANDS = {'ls', 'pwd', 'tree', 'wc', 'stat', 'file', 'realpath',
                       'basename', 'dirname', 'head', 'tail', 'grep', 'find',
                       'mkdir', 'touch', 'cat'}

DANGEROUS_DENY = [
    "Bash(gh pr merge:*)", "Bash(gh pr merge)",
    "Bash(gh pr close:*)", "Bash(gh pr close)",
    "Bash(gh repo delete:*)", "Bash(gh repo delete)",
    "Bash(gh repo archive:*)", "Bash(gh repo archive)",
    "Bash(gh secret:*)", "Bash(gh secret)",
    "Bash(gh auth logout:*)", "Bash(gh auth logout)",
    "Bash(gh auth token:*)", "Bash(gh auth token)",
    "Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)",
    "Read(./**/secrets/**)", "Read(./**/*.pem)", "Read(./**/*.key)",
    "Edit(./.env)", "Edit(./.env.*)", "Edit(./secrets/**)",
    "Bash(rm -rf:*)", "Bash(sudo:*)", "Bash(chmod 777:*)",
]


def generate_permissions(analysis: dict) -> dict:
    """Generate permissions config from analysis."""
    allow = []
    bash_cmds = analysis['bash_commands']

    # Add dev commands that were used
    for cmd in sorted(bash_cmds.keys()):
        if cmd in DEV_COMMANDS:
            allow.append(f"Bash({cmd}:*)")

    # Add filesystem commands that were used
    for cmd in sorted(bash_cmds.keys()):
        if cmd in FILESYSTEM_COMMANDS:
            allow.append(f"Bash({cmd}:*)")

    # Add MCP server permissions
    mcp_servers = set()
    for tool in analysis['mcp_tools']:
        parts = tool.split('__')
        if len(parts) >= 2:
            mcp_servers.add(parts[1])

    for server in sorted(mcp_servers):
        allow.append(f"mcp__{server}__*")

    return {
        "allow": allow,
        "deny": DANGEROUS_DENY,
        "defaultMode": "acceptEdits"
    }


def main():
    project_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

    print(f"Analyzing: {project_path}", file=sys.stderr)
    analysis = analyze_sessions(project_path)
    print(f"Sessions analyzed: {analysis['session_count']}", file=sys.stderr)

    if analysis['bash_commands']:
        print("\nBash commands found:", file=sys.stderr)
        for cmd, count in sorted(analysis['bash_commands'].items(), key=lambda x: -x[1])[:15]:
            print(f"  {cmd}: {count}", file=sys.stderr)

    if analysis['mcp_tools']:
        print("\nMCP tools found:", file=sys.stderr)
        for tool in sorted(analysis['mcp_tools']):
            print(f"  {tool}", file=sys.stderr)

    permissions = generate_permissions(analysis)
    print("\n" + json.dumps({"permissions": permissions}, indent=2))


if __name__ == '__main__':
    main()
