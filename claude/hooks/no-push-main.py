#!/usr/bin/env python3
"""Pre-tool-use hook that protects main/master branches.

Blocks:
- git push: direct, force, bare (when on protected branch), refspec targets
- git history rewriting: reset --hard, rebase, commit --amend
- git destructive operations: checkout ., restore ., clean -f
- git branch manipulation: branch -D/-f, push --delete, push origin :main
- gh CLI: API calls that modify refs/branches/protection, repo deletion,
  admin merges, force syncs, and mutating gh api calls targeting protected branches
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

PROTECTED = {"main", "master"}

# Regex matching git global options that take an argument (flag + value).
# These appear between `git` and the subcommand and must be stripped
# so that patterns like `\bgit\s+push\b` still match.
_GIT_GLOBAL_OPT_WITH_ARG = re.compile(
    r"(?:^|\s)(?:-C|-c|--git-dir|--work-tree|--namespace|--super-prefix"
    r"|--config-env|--literal-pathspecs|--glob-pathspecs"
    r"|--noglob-pathspecs|--icase-pathspecs)\s+\S+"
)

# Regex matching git global flags that are standalone (no argument).
_GIT_GLOBAL_FLAG = re.compile(
    r"(?:^|\s)(?:--bare|--no-replace-objects|--no-lazy-fetch"
    r"|--no-optional-locks|--no-pager|--paginate|-p|--html-path"
    r"|--man-path|--info-path|--version)(?=\s|$)"
)


def strip_git_global_opts(cmd: str) -> str:
    """Remove git global options so `git -C /path push` becomes `git push`."""
    result = _GIT_GLOBAL_OPT_WITH_ARG.sub("", cmd)
    result = _GIT_GLOBAL_FLAG.sub("", result)
    return " ".join(result.split())


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


def check_gh_api(cmd: str) -> str | None:
    """Check gh api calls that could modify protected branches or repo settings."""
    if not re.search(r"\bgh\s+api\b", cmd):
        return None

    is_mutating = bool(re.search(r"(?:^|\s)-X\s+(DELETE|PATCH|PUT|POST)\b", cmd))

    # gh api without -X defaults to GET for reads, but POST for graphql
    if not is_mutating:
        # Check for graphql mutations
        if re.search(r"\bgraphql\b", cmd) and re.search(r"mutation\s*\{|mutation\b", cmd):
            is_mutating = True
        # Check for --input (sends data, implies POST)
        if re.search(r"(?:^|\s)--input(?:\s|$)", cmd):
            is_mutating = True
        # Check for -f/-F (field flags imply POST when no -X is set)
        if re.search(r"(?:^|\s)-[fF]\s+", cmd) and not re.search(r"(?:^|\s)-X\s+GET\b", cmd):
            is_mutating = True

    if not is_mutating:
        return None

    # Block mutating API calls that target protected branch refs
    for branch in PROTECTED:
        if re.search(rf"refs/heads/{branch}\b", cmd):
            return f"Mutating gh api call targeting refs/heads/{branch} is not allowed."
        if re.search(rf"branches/{branch}/protection", cmd):
            return f"gh api call modifying {branch} branch protection is not allowed."

    # Block deletion of rulesets
    if re.search(r"rulesets/\d+", cmd) and re.search(r"(?:^|\s)-X\s+DELETE\b", cmd):
        return "Deleting repository rulesets via gh api is not allowed."

    return None


def check_gh_commands(cmd: str) -> str | None:
    """Check gh subcommands that could damage protected branches."""
    if not re.search(r"\bgh\b", cmd):
        return None

    # gh repo delete
    if re.search(r"\bgh\s+repo\s+delete\b", cmd):
        return "gh repo delete is not allowed."

    # gh repo sync --force --branch main
    if re.search(r"\bgh\s+repo\s+sync\b", cmd):
        is_force = bool(re.search(r"(?:^|\s)--force(?:\s|$)", cmd))
        for branch in PROTECTED:
            if re.search(rf"(?:^|\s)--branch\s+{branch}\b", cmd):
                if is_force:
                    return f"gh repo sync --force --branch {branch} is not allowed."

    # gh repo edit --default-branch (changing default branch)
    if re.search(r"\bgh\s+repo\s+edit\b", cmd) and re.search(r"(?:^|\s)--default-branch(?:\s|$)", cmd):
        return "Changing the default branch via gh repo edit is not allowed."

    # gh pr merge --admin (bypassing required checks)
    if re.search(r"\bgh\s+pr\s+merge\b", cmd) and re.search(r"(?:^|\s)--admin(?:\s|$)", cmd):
        return "gh pr merge --admin is not allowed. Merge without bypassing required checks."

    # gh api (delegate to detailed check)
    reason = check_gh_api(cmd)
    if reason:
        return reason

    return None


def _split_compound_command(command: str) -> list[str]:
    """Split a compound shell command on &&, ||, and ; into individual commands.

    Uses a simple split that handles the common case of chained commands.
    Does not attempt to parse full shell syntax (subshells, pipes, etc.)
    since those are rare in the tool-use context.
    """
    # Split on && || ; but not inside quoted strings.
    # For robustness, split on the operators and strip each part.
    parts = re.split(r"\s*(?:&&|\|\||;)\s*", command)
    return [p.strip() for p in parts if p.strip()]


def check_command(command: str) -> str | None:
    """Return a reason string if the command should be blocked, None otherwise."""
    git_checks = [check_push, check_history_rewrite, check_destructive, check_branch_manipulation]
    gh_checks = [check_gh_commands]

    for part in _split_compound_command(command):
        cmd = " ".join(part.split())

        if re.search(r"\bgit\b", cmd):
            # Normalize away global git options like -C, --git-dir, -c so that
            # `git -C /some/path push` is checked the same as `git push`.
            normalized = strip_git_global_opts(cmd)
            for check in git_checks:
                reason = check(normalized)
                if reason:
                    return reason

        if re.search(r"\bgh\b", cmd):
            for check in gh_checks:
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
        sys.exit(2)


if __name__ == "__main__":
    main()
