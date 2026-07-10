#!/usr/bin/env python3
"""Harness eval runner: lint + outcome metrics + baseline regression check.

    python3 evals/run.py                    # run everything, compare to baseline
    python3 evals/run.py --update-baseline  # accept current values as the new baseline
    python3 evals/run.py --lint-only        # just the deterministic checks (fast)

Every run appends to evals/history.jsonl. Exit 1 on lint FAIL or metric
regression; regression rules are in REGRESSION_RULES below and explained
in evals/README.md.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINE = HERE / "baseline.json"
HISTORY = HERE / "history.jsonl"


def run_module(name, *args):
    proc = subprocess.run(
        [sys.executable, str(HERE / name), *args],
        capture_output=True, text=True, timeout=600,
    )
    return proc


def flatten(metrics):
    """Pull the comparable numbers out of the two metric payloads."""
    t = metrics.get("transcript") or {}
    g = metrics.get("git") or {}
    sessions = t.get("sessions") or 0

    def per_session(n):
        return round(n / sessions, 3) if sessions else None

    flat = {
        "tool_error_rate": t.get("tool_error_rate"),
        "interruptions_per_session": per_session(t.get("interruptions", 0)),
        "retry_loops_per_session": per_session(t.get("retry_loops", 0)),
        "masked_test_pipes_per_session": per_session(t.get("masked_test_pipes", 0)),
        "corrections": t.get("corrections"),
        "classifier_denials_per_session": per_session((t.get("denials") or {}).get("classifier", 0)),
        "hook_blocks": (t.get("denials") or {}).get("hook_block"),
    }
    push = (t.get("gate_actions") or {}).get("git_push") or {}
    if push.get("count"):
        flat["unapproved_push_share"] = round(1 - push["approved"] / push["count"], 3)

    reverts = refix = unreviewed = review_sample = 0
    for repo in (g.get("repos") or {}).values():
        if "error" in repo:
            continue
        reverts += repo.get("reverts", 0)
        refix += len(repo.get("refix_tickets", []))
        churn = repo.get("review_churn") or {}
        unreviewed += churn.get("unreviewed_merged", 0)
        review_sample += churn.get("review_sample", 0)
    flat["reverts"] = reverts
    flat["refix_tickets"] = refix
    if review_sample:
        flat["unreviewed_merged_share"] = round(unreviewed / review_sample, 3)
    return flat


# metric -> (kind, params). All rules fire only when the value got WORSE.
#   ratio:    alarm if now > base * factor AND now > base + floor (guards tiny bases)
#   absolute: alarm if now > base (rare events that should stay at ~zero)
#   warn_gap: warn if now > base + gap (heuristic metrics, never fail the run)
REGRESSION_RULES = {
    "tool_error_rate": ("ratio", {"factor": 1.5, "floor": 0.01}),
    "interruptions_per_session": ("ratio", {"factor": 2.0, "floor": 0.1}),
    "retry_loops_per_session": ("ratio", {"factor": 2.0, "floor": 0.1}),
    "masked_test_pipes_per_session": ("ratio", {"factor": 2.0, "floor": 0.1}),
    "reverts": ("absolute", {}),
    "refix_tickets": ("absolute", {}),
    "unreviewed_merged_share": ("ratio", {"factor": 1.5, "floor": 0.1}),
    "unapproved_push_share": ("warn_gap", {"gap": 0.15}),
    "classifier_denials_per_session": ("warn_gap", {"gap": 0.3}),
}


def compare(current, baseline):
    alarms, warnings = [], []
    for key, (kind, p) in REGRESSION_RULES.items():
        now, base = current.get(key), baseline.get(key)
        if now is None or base is None:
            continue
        if kind == "ratio" and now > base * p["factor"] and now > base + p["floor"]:
            alarms.append(f"{key}: {base} -> {now}")
        elif kind == "absolute" and now > base:
            alarms.append(f"{key}: {base} -> {now}")
        elif kind == "warn_gap" and now > base + p["gap"]:
            warnings.append(f"{key}: {base} -> {now}")
    return alarms, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--lint-only", action="store_true")
    ap.add_argument("--days-transcript", type=int, default=30)
    ap.add_argument("--days-git", type=int, default=90)
    ap.add_argument("--no-gh", action="store_true",
                    help="skip gh-based review-churn metrics (offline mode)")
    args = ap.parse_args()

    # 1. deterministic lint
    lint = run_module("harness_lint.py", "--json")
    lint_results = json.loads(lint.stdout) if lint.stdout.strip() else []
    lint_failed = lint.returncode != 0
    for r in lint_results:
        print(f"{r['status']:4}  {r['check']:16}  {r['detail']}")

    if args.lint_only:
        sys.exit(1 if lint_failed else 0)

    # 2. outcome metrics
    print("\nmeasuring transcripts and git history...", file=sys.stderr)
    t = run_module("transcript_metrics.py", "--days", str(args.days_transcript))
    git_args = ["--days", str(args.days_git)]
    if not args.no_gh:
        git_args.append("--with-gh")
    g = run_module("git_metrics.py", *git_args)
    metrics = {
        "transcript": json.loads(t.stdout) if t.returncode == 0 else {"error": t.stderr.strip()},
        "git": json.loads(g.stdout) if g.returncode == 0 else {"error": g.stderr.strip()},
    }
    current = flatten(metrics)

    print()
    for key, value in current.items():
        print(f"      {key:32} {value}")

    # 3. history + baseline comparison
    snapshot = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "flat": current,
        "lint": {r["check"]: r["status"] for r in lint_results},
    }
    with open(HISTORY, "a") as f:
        f.write(json.dumps(snapshot) + "\n")

    regressed = False
    if args.update_baseline or not BASELINE.exists():
        BASELINE.write_text(json.dumps(
            {"at": snapshot["at"], **current}, indent=2) + "\n")
        print(f"\nbaseline {'updated' if args.update_baseline else 'created'}: {BASELINE}")
    else:
        baseline = json.loads(BASELINE.read_text())
        alarms, warnings = compare(current, baseline)
        print(f"\nbaseline from {baseline.get('at', '?')}:")
        for w in warnings:
            print(f"WARN  {w}")
        for a in alarms:
            print(f"REGRESSION  {a}")
        if not alarms and not warnings:
            print("      no regressions against baseline")
        regressed = bool(alarms)

    sys.exit(1 if (lint_failed or regressed) else 0)


if __name__ == "__main__":
    main()
