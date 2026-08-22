#!/usr/bin/env python3
"""Deterministic regression checks over the harness itself.

Fast (seconds), no network, no model calls. Runs anywhere the repo is
checked out; checks that need the installed ~/.claude or sibling project
repos skip themselves when those are absent (CI-safe).

Usage:
    python3 harness_lint.py [--repo-root PATH] [--json]

Exit code: 1 if any FAIL, 0 otherwise (warnings never fail the run).
"""

import argparse
import json
import os
import py_compile
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RESULTS = []


def record(check, status, detail):
    RESULTS.append({"check": check, "status": status, "detail": detail})


# ---------------------------------------------------------------- hook tests

def run_hook(hook_path, command, cwd=None):
    """Feed a PreToolUse payload to the hook; return (exit_code, stderr)."""
    payload = json.dumps({"tool_input": {"command": command}})
    proc = subprocess.run(
        [sys.executable, str(hook_path)],
        input=payload, capture_output=True, text=True, timeout=15, cwd=cwd,
    )
    return proc.returncode, proc.stderr.strip()


def make_temp_repo(branch):
    """Create a throwaway git repo checked out on `branch`."""
    d = tempfile.mkdtemp(prefix=f"hooktest-{branch}-")
    subprocess.run(["git", "init", "-q", "-b", branch, d], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", d, "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "--allow-empty", "-m", "init"],
        check=True, capture_output=True,
    )
    return d


def check_hook_behavior(repo_root):
    """Behavioral matrix for no-push-main.py. Every case is a past incident shape."""
    hook = repo_root / "claude" / "hooks" / "no-push-main.py"
    if not hook.exists():
        record("hook_behavior", "FAIL", f"hook missing: {hook}")
        return

    on_main = make_temp_repo("main")
    on_feature = make_temp_repo("feature-x")
    neutral = tempfile.mkdtemp(prefix="hooktest-nogit-")

    # (command, expect_block, why)
    cases = [
        ("git push origin main", True, "direct push to main"),
        ("git push --force origin main", True, "force push to main"),
        ("cd /tmp && git push origin main", True, "compound command (incident: hook missed && chains)"),
        ("git -C /somewhere push origin main", True, "git -C shape (incident: hook missed -C)"),
        ("git push --delete origin main", True, "remote main deletion"),
        ("git push origin :main", True, "refspec deletion of main"),
        ("gh pr merge --admin 123", True, "admin merge bypasses checks"),
        ("gh repo delete owner/repo", True, "repo deletion"),
        ("gh api -X DELETE repos/o/r/git/refs/heads/main", True, "ref deletion via API"),
        ("git push origin +main", True, "force via + refspec"),
        ("git push --mirror origin", True, "mirror push rewrites protected refs"),
        ("git push origin HEAD:refs/heads/main", True, "fully-qualified refspec to main"),
        ("git push origin feature-branch", False, "normal feature push"),
        ("git push origin HEAD:feature-branch", False, "refspec to feature branch"),
        ("git status", False, "read-only git"),
        ("echo hello", False, "non-git command"),
        (f"git -C {on_feature} rebase origin/main", False,
         "rebase in a feature worktree (incident: false positive blocked worktree rebases)"),
        (f"git -C {on_main} rebase origin/other", True, "rebase while on main"),
        (f"git -C {on_main} push", True, "bare push while on main"),
        (f"git -C {on_feature} push", False, "bare push while on feature branch"),
    ]

    failures = []
    for command, expect_block, why in cases:
        try:
            code, stderr = run_hook(hook, command, cwd=neutral)
        except subprocess.TimeoutExpired:
            failures.append(f"TIMEOUT: {command!r}")
            continue
        if expect_block:
            # Blocking means exit code exactly 2 with a reason on stderr —
            # the hook once shipped with a wrong exit code and blocked nothing.
            if code != 2:
                failures.append(f"NOT BLOCKED (exit {code}, want 2): {command!r} — {why}")
            elif not stderr:
                failures.append(f"blocked without a reason on stderr: {command!r}")
        else:
            if code != 0:
                failures.append(f"WRONGLY BLOCKED (exit {code}): {command!r} — {why}")

    if failures:
        record("hook_behavior", "FAIL", "; ".join(failures))
    else:
        record("hook_behavior", "PASS", f"{len(cases)} payload cases behaved correctly")


def check_hook_compile(repo_root):
    hooks_dir = repo_root / "claude" / "hooks"
    bad = []
    for py in sorted(hooks_dir.glob("*.py")):
        try:
            py_compile.compile(str(py), doraise=True)
        except py_compile.PyCompileError as exc:
            bad.append(f"{py.name}: {exc.msg}")
    if bad:
        record("hook_compile", "FAIL", "; ".join(bad))
    else:
        record("hook_compile", "PASS", f"{len(list(hooks_dir.glob('*.py')))} hook scripts compile")


def check_hook_unit_tests(repo_root):
    """Run the hooks' own unit-test files (test_*.py) if present."""
    hooks_dir = repo_root / "claude" / "hooks"
    tests = sorted(hooks_dir.glob("test_*.py"))
    if not tests:
        record("hook_unit_tests", "SKIP", "no test_*.py in claude/hooks")
        return
    bad = []
    for test in tests:
        proc = subprocess.run(
            [sys.executable, str(test)], capture_output=True, text=True, timeout=60,
        )
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout).strip().splitlines()[-1:]
            bad.append(f"{test.name}: {' '.join(tail)}")
    if bad:
        record("hook_unit_tests", "FAIL", "; ".join(bad))
    else:
        record("hook_unit_tests", "PASS", f"{len(tests)} hook test files green")


# ---------------------------------------------------------------- invariants

def check_invariants(repo_root):
    spec_path = Path(__file__).parent / "harness_invariants.json"
    spec = json.loads(spec_path.read_text())

    missing = []
    for item in spec.get("required", []):
        target = repo_root / item["file"]
        if not target.exists():
            missing.append(f"{item['file']}: file missing")
        elif not re.search(item["pattern"], target.read_text()):
            missing.append(f"{item['file']}: pattern {item['pattern']!r} gone — {item['reason']}")
    if missing:
        record("invariants", "FAIL", "; ".join(missing))
    else:
        record("invariants", "PASS", f"{len(spec.get('required', []))} pinned countermeasures present")

    still_open = []
    for item in spec.get("gaps", []):
        target = repo_root / item["file"]
        if target.exists() and re.search(item["pattern"], target.read_text()):
            record("invariant_gaps", "WARN",
                   f"{item['file']} now matches {item['pattern']!r} — move this entry from gaps to required")
        else:
            still_open.append(f"{item['file']}: {item['reason']}")
    if still_open:
        record("invariant_gaps", "WARN", f"{len(still_open)} known-missing countermeasures: " + " | ".join(still_open))


# ------------------------------------------------------- installed ~/.claude

SYNCED = ["CLAUDE.md", "agents", "hooks", "skills", "scripts", "rules"]


def check_installed_sync():
    dot = Path.home() / ".claude"
    if not dot.exists():
        record("installed_sync", "SKIP", "~/.claude not present (CI)")
        return

    problems = []
    for name in SYNCED:
        link = dot / name
        if not link.is_symlink():
            problems.append(f"{name} is not a symlink (sync-claude.sh not applied?)")
        elif not link.exists():
            problems.append(f"{name} is a dangling symlink -> {os.readlink(link)}")

    # any other dangling symlink at the top level (e.g. the stale commands/ link)
    for entry in dot.iterdir():
        if entry.is_symlink() and not entry.exists() and entry.name not in SYNCED:
            problems.append(f"dangling symlink: {entry.name} -> {os.readlink(entry)}")

    # hooks registered in settings.json must resolve to real files
    settings_path = dot / "settings.json"
    if settings_path.exists():
        settings = json.loads(settings_path.read_text())
        hook_cmds = [
            h.get("command", "")
            for group in settings.get("hooks", {}).values()
            for entry in group
            for h in entry.get("hooks", [])
        ]
        if not any("no-push-main" in c for c in hook_cmds):
            problems.append("no-push-main hook not registered in settings.json")
        for cmd in hook_cmds:
            for token in cmd.split():
                if token.startswith(("~", "/")):
                    path = Path(os.path.expanduser(token))
                    if not path.exists():
                        problems.append(f"registered hook file missing: {token}")

    if problems:
        record("installed_sync", "FAIL", "; ".join(problems))
    else:
        record("installed_sync", "PASS", "symlinks live, no dangling links, hooks registered")


def check_config_drift(repo_root):
    """Uncommitted changes to synced config = rules running in production that
    aren't in git. Normal while editing; drift when it lingers."""
    main_checkout = repo_root
    # when running from a worktree, report against the primary checkout
    git_common = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--git-common-dir"],
        capture_output=True, text=True,
    ).stdout.strip()
    if git_common:
        main_checkout = Path(git_common).resolve().parent

    out = subprocess.run(
        ["git", "-C", str(main_checkout), "status", "--porcelain", "--", "claude/", "scripts/"],
        capture_output=True, text=True,
    ).stdout.strip()
    if out:
        files = [line[2:].lstrip() for line in out.splitlines()]
        record("config_drift", "WARN",
               f"live config has uncommitted changes in {main_checkout}: {', '.join(files)}")
    else:
        record("config_drift", "PASS", "live config matches committed state")


# ------------------------------------------------------------- project scans

def check_pipe_exit_codes():
    """Makefiles that pipe build/test output must not mask exit codes
    (incident: make test-quick returned 0 on ~2930 failures via xcbeautify)."""
    base = Path(os.environ.get("PERSONAL_PROJECTS", Path.home() / "projects" / "personal"))
    if not base.exists():
        record("pipe_exit_codes", "SKIP", f"{base} not present")
        return
    problems, scanned = [], 0
    for makefile in base.glob("*/Makefile"):
        text = makefile.read_text(errors="replace")
        if "| xcbeautify" not in text and "PIPE_PRETTY" not in text:
            continue
        scanned += 1
        if "pipefail" not in text:
            problems.append(f"{makefile}: pipes through xcbeautify without pipefail")
    if problems:
        record("pipe_exit_codes", "FAIL", "; ".join(problems))
    else:
        record("pipe_exit_codes", "PASS", f"{scanned} xcbeautify-piping Makefiles all set pipefail")


# ----------------------------------------------------------------------- run

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    repo_root = Path(args.repo_root)

    check_hook_behavior(repo_root)
    check_hook_compile(repo_root)
    check_hook_unit_tests(repo_root)
    check_invariants(repo_root)
    check_installed_sync()
    check_config_drift(repo_root)
    check_pipe_exit_codes()

    if args.json:
        json.dump(RESULTS, sys.stdout, indent=2)
        print()
    else:
        width = max(len(r["check"]) for r in RESULTS)
        for r in RESULTS:
            print(f"{r['status']:4}  {r['check']:{width}}  {r['detail']}")

    sys.exit(1 if any(r["status"] == "FAIL" for r in RESULTS) else 0)


if __name__ == "__main__":
    main()
