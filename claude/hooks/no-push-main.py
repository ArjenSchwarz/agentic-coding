#!/usr/bin/env python3
"""Pre-tool-use hook that protects main/master branches.

Blocks:
- Pushes: direct, force, bare (when on protected branch), refspec targets
- History rewriting: reset --hard, rebase, commit --amend
- Destructive operations: checkout ., restore ., clean -f
- Branch manipulation: branch -D/-f, push --delete, push origin :main
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

PROTECTED = {"main", "master"}


def get_current_branch():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def on_protected_branch():
    """Return the branch name if on a protected branch, else None."""
    current = get_current_branch()
    return current if current in PROTECTED else None


def check_push(cmd: str) -> str | None:
    """Check git push commands."""
    if not re.search(r"\bgit\s+push\b", cmd):
        return None

    is_force = bool(re.search(r"(?:^|\s)(-f|--force|--force-with-lease)(?:\s|$)", cmd))

    # git push --delete origin main / git push origin :main
    for branch in PROTECTED:
        if re.search(rf"(?:^|\s)--delete\s+\S+\s+{branch}\b", cmd):
            return f"Deleting remote {branch} is not allowed."
        if re.search(rf"\bgit\s+push\s+\S+\s+:{branch}\b", cmd):
            return f"Deleting remote {branch} is not allowed."

    # Strip flags to get: git push [remote] [refspec...]
    stripped = re.sub(r"\s+(-u|--set-upstream|-f|--force|--force-with-lease|--no-verify|--tags|--dry-run|--delete)(?=\s|$)", "", cmd)
    stripped = " ".join(stripped.split())

    match = re.match(r"^git push(?:\s+(\S+))?(?:\s+(\S+))?\s*$", stripped)
    if not match:
        return None

    refspec = match.group(2)

    target_branch = None
    if refspec:
        target_branch = refspec.split(":")[-1] if ":" in refspec else refspec

    if target_branch in PROTECTED:
        if is_force:
            return f"Force push to {target_branch} is not allowed."
        return f"Pushing to {target_branch} is not allowed. Use a feature branch and a PR."

    if target_branch is None:
        branch = on_protected_branch()
        if branch:
            if is_force:
                return f"Force push while on {branch} is not allowed."
            return f"Pushing while on {branch} is not allowed. Use a feature branch and a PR."

    return None


def check_history_rewrite(cmd: str) -> str | None:
    """Check commands that rewrite history: reset --hard, rebase, commit --amend."""
    # git reset --hard (while on protected branch)
    if re.search(r"\bgit\s+reset\b", cmd) and re.search(r"(?:^|\s)--hard(?:\s|$)", cmd):
        branch = on_protected_branch()
        if branch:
            return f"git reset --hard while on {branch} is not allowed."

    # git rebase (while on protected branch)
    if re.search(r"\bgit\s+rebase\b", cmd):
        branch = on_protected_branch()
        if branch:
            return f"git rebase while on {branch} is not allowed."

    # git commit --amend (while on protected branch)
    if re.search(r"\bgit\s+commit\b", cmd) and re.search(r"(?:^|\s)--amend(?:\s|$)", cmd):
        branch = on_protected_branch()
        if branch:
            return f"git commit --amend while on {branch} is not allowed."

    return None


def check_destructive(cmd: str) -> str | None:
    """Check destructive working tree operations: checkout ., restore ., clean -f."""
    # git checkout . or git checkout -- .
    if re.search(r"\bgit\s+checkout\s+(--\s+)?\.\s*$", cmd):
        branch = on_protected_branch()
        if branch:
            return f"git checkout . while on {branch} is not allowed. Uncommitted work may be lost."

    # git restore . or git restore --staged .
    if re.search(r"\bgit\s+restore\b", cmd) and re.search(r"\.\s*$", cmd):
        branch = on_protected_branch()
        if branch:
            return f"git restore . while on {branch} is not allowed. Uncommitted work may be lost."

    # git clean -f
    if re.search(r"\bgit\s+clean\b", cmd) and re.search(r"(?:^|\s)-[a-zA-Z]*f", cmd):
        branch = on_protected_branch()
        if branch:
            return f"git clean -f while on {branch} is not allowed. Untracked files may be lost."

    return None


def check_branch_manipulation(cmd: str) -> str | None:
    """Check branch deletion/force-move: branch -D main, branch -f main."""
    if not re.search(r"\bgit\s+branch\b", cmd):
        return None

    for branch in PROTECTED:
        # git branch -D main / git branch --delete --force main
        if re.search(r"(?:^|\s)(-D|--delete)(?:\s|$)", cmd) and re.search(rf"\b{branch}\b", cmd):
            return f"Deleting branch {branch} is not allowed."

        # git branch -f main <ref> / git branch --force main <ref>
        if re.search(r"(?:^|\s)(-f|--force)(?:\s|$)", cmd) and re.search(rf"\b{branch}\b", cmd):
            return f"Force-moving branch {branch} is not allowed."

    return None


def check_command(command: str) -> str | None:
    """Return a reason string if the command should be blocked, None otherwise."""
    cmd = " ".join(command.split())

    if not re.search(r"\bgit\b", cmd):
        return None

    checks = [check_push, check_history_rewrite, check_destructive, check_branch_manipulation]
    for check in checks:
        reason = check(cmd)
        if reason:
            return reason

    return None


def main():
    data = json.load(sys.stdin)
    command = data.get("tool_input", {}).get("command", "")

    reason = check_command(command)
    if reason:
        print(reason, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
