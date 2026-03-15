#!/usr/bin/env python3
"""Pre-tool-use hook that blocks git push to main/master.

Catches:
- Explicit pushes: git push origin main, git push origin master
- Default branch pushes: git push (when on main/master)
- Force pushes to any branch: git push --force, git push -f
- Force pushes with lease: git push --force-with-lease (to main/master)
- Pushes with upstream set: git push -u origin main
"""

from __future__ import annotations

import json
import re
import subprocess
import sys


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


def check_command(command: str) -> str | None:
    """Return a reason string if the push should be blocked, None otherwise."""

    # Normalise whitespace
    cmd = " ".join(command.split())

    # Only care about git push commands
    if not re.search(r"\bgit\s+push\b", cmd):
        return None

    protected = {"main", "master"}
    is_force = bool(re.search(r"(?:^|\s)(-f|--force|--force-with-lease)(?:\s|$)", cmd))

    # Strip flags to get: git push [remote] [refspec...]
    stripped = re.sub(r"\s+(-u|--set-upstream|-f|--force|--force-with-lease|--no-verify|--tags|--dry-run)(?=\s|$)", "", cmd)
    stripped = " ".join(stripped.split())

    # Parse the stripped command into parts after "git push"
    match = re.match(r"^git push(?:\s+(\S+))?(?:\s+(\S+))?\s*$", stripped)
    if not match:
        return None

    remote = match.group(1)  # e.g. "origin" or None
    refspec = match.group(2)  # e.g. "main" or "feature:main" or None

    # Extract target branch from refspec (handles src:dst format)
    target_branch = None
    if refspec:
        target_branch = refspec.split(":")[-1] if ":" in refspec else refspec

    # 1. Explicit push to protected branch
    if target_branch in protected:
        if is_force:
            return f"Force push to {target_branch} is not allowed."
        return f"Pushing to {target_branch} is not allowed. Use a feature branch and a PR."

    # 2. No explicit branch — check current branch
    if target_branch is None:
        current = get_current_branch()
        if current in protected:
            if is_force:
                return f"Force push while on {current} is not allowed."
            return f"Pushing while on {current} is not allowed. Use a feature branch and a PR."

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
