#!/usr/bin/env python3
"""Tests for no-push-main.py.

Run: python3 claude/hooks/test_no_push_main.py

The module filename is hyphenated, so it is loaded via importlib. Branch
detection (get_current_branch) is monkeypatched so "while on <branch>" cases
are deterministic and need no real git repository.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "no_push_main", Path(__file__).with_name("no-push-main.py")
)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


def check(cmd: str, current_branch: str = "feature-x") -> str | None:
    """Run check_command with get_current_branch pinned to current_branch."""
    hook.get_current_branch = lambda cwd=None: current_branch
    return hook.check_command(cmd)


# (command, current_branch, should_block)
BLOCK = True
ALLOW = False

CASES = [
    # --- direct/explicit pushes to main (already covered) ---
    ("git push origin main", "feature-x", BLOCK),
    ("git push", "main", BLOCK),
    ("git push -f", "main", BLOCK),
    ("git push --force origin main", "feature-x", BLOCK),
    ("git push -u origin main", "feature-x", BLOCK),
    ("git push origin feature:main", "feature-x", BLOCK),
    ("git push --delete origin main", "feature-x", BLOCK),
    ("git push origin :main", "feature-x", BLOCK),
    # --- newly closed bypasses ---
    ("git push origin +main", "feature-x", BLOCK),                 # force via + refspec
    ("git push origin HEAD:refs/heads/main", "feature-x", BLOCK),  # fully-qualified dest
    ("git push origin refs/heads/main", "feature-x", BLOCK),
    ("git push --mirror origin", "feature-x", BLOCK),              # pushes all refs
    ("git push --all origin", "feature-x", BLOCK),                 # pushes all branches
    ("git push origin HEAD", "main", BLOCK),                       # HEAD resolves to main
    ("git push --force origin HEAD:refs/heads/main", "feature-x", BLOCK),
    ("git -C /tmp/wt push origin +master", "feature-x", BLOCK),    # global opts + master
    # --- legitimate actions that MUST still pass ---
    ("git push origin feature-x", "feature-x", ALLOW),
    ("git push --force origin feature-x", "feature-x", ALLOW),
    ("git push origin +feature-x", "feature-x", ALLOW),           # force-push a feature branch
    ("git push --force-with-lease", "feature-x", ALLOW),
    ("git push origin HEAD", "feature-x", ALLOW),                 # HEAD resolves to feature
    ("git push origin HEAD:refs/heads/feature-x", "feature-x", ALLOW),
    ("git commit -m 'main fix'", "main", ALLOW),                  # not a push
    ("git status", "main", ALLOW),
]


def main() -> int:
    failures = []
    for cmd, branch, expect_block in CASES:
        reason = check(cmd, branch)
        blocked = reason is not None
        if blocked != expect_block:
            failures.append(
                f"  {cmd!r} on {branch!r}: expected "
                f"{'BLOCK' if expect_block else 'ALLOW'}, got "
                f"{'BLOCK (' + reason + ')' if blocked else 'ALLOW'}"
            )

    if failures:
        print(f"FAILED {len(failures)}/{len(CASES)}:")
        print("\n".join(failures))
        return 1
    print(f"ok — {len(CASES)} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
