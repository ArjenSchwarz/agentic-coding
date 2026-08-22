#!/usr/bin/env python3
"""Shipped-outcome metrics mined from git history of harness-built repos.

Core metrics are git-only (work offline); review-churn metrics need an
authenticated `gh` and are skipped gracefully without one.

Usage:
    python3 git_metrics.py [--days 90] [--repos prism,flux,orbit] [--with-gh]

Repos are resolved under $PERSONAL_PROJECTS (default ~/projects/personal).
Outputs a JSON object on stdout. Interpretation in evals/README.md.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

SQUASH_RE = re.compile(r"\(#\d+\)$")
TICKET_RE = re.compile(r"\bT-\d+\b")
FIX_RE = re.compile(r"^fix\b", re.IGNORECASE)


def git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}: {result.stderr.strip()}")
    return result.stdout


def repo_metrics(repo, days):
    ref = "origin/main"
    try:
        git(repo, "rev-parse", "--verify", ref)
    except RuntimeError:
        ref = "main"
    log = git(
        repo, "log", ref, f"--since={days} days ago",
        "--date=short", "--format=%ad\t%s",
    )
    squash = []  # (date, subject) for squash-merge commits
    reverts = 0
    for line in log.splitlines():
        date, _, subject = line.partition("\t")
        if subject.startswith("Revert"):
            reverts += 1
        if SQUASH_RE.search(subject):
            squash.append((date, subject))

    fix_titled = sum(1 for _, s in squash if FIX_RE.match(s))

    # Same-ticket re-fix: a T-id in >=2 Fix-titled squash commits <=7 days apart.
    by_ticket = {}
    for date, subject in squash:
        if not FIX_RE.match(subject):
            continue
        for tid in TICKET_RE.findall(subject):
            by_ticket.setdefault(tid, []).append(date)
    refix_pairs = []
    for tid, dates in by_ticket.items():
        if len(dates) < 2:
            continue
        ds = sorted(datetime.strptime(d, "%Y-%m-%d") for d in dates)
        if any((b - a) <= timedelta(days=7) for a, b in zip(ds, ds[1:])):
            refix_pairs.append(tid)

    return {
        "merged_prs": len(squash),
        "reverts": reverts,
        "fix_titled": fix_titled,
        "fix_titled_share": round(fix_titled / len(squash), 3) if squash else None,
        "refix_tickets": sorted(refix_pairs),
    }


def gh_metrics(repo_name, owner, days, sample=15):
    """Review-churn metrics via gh; returns None if gh is unavailable."""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        query = (
            'query { search(query: "repo:%s/%s is:pr is:merged merged:>=%s", '
            "type: ISSUE, first: 100) { issueCount nodes { ... on PullRequest "
            "{ number commits { totalCount } } } } }" % (owner, repo_name, since)
        )
        out = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            capture_output=True, text=True, check=True, timeout=60,
        ).stdout
        data = json.loads(out)["data"]["search"]
        counts = [n["commits"]["totalCount"] for n in data["nodes"]]
        commits_per_pr = round(sum(counts) / len(counts), 2) if counts else None

        # Review rounds: Verdict-comment count on the most recent merged PRs.
        prs = json.loads(subprocess.run(
            ["gh", "pr", "list", "--repo", f"{owner}/{repo_name}", "--state", "merged",
             "--limit", str(sample), "--json", "number"],
            capture_output=True, text=True, check=True, timeout=60,
        ).stdout)
        multi_round = unreviewed = 0
        for pr in prs:
            body = subprocess.run(
                ["gh", "pr", "view", str(pr["number"]), "--repo", f"{owner}/{repo_name}",
                 "--json", "comments",
                 # review signature has drifted over time: **Verdict** (current),
                 # ## Code Review (older), claude-local-review sentinel
                 "--jq", '[.comments[].body | select(test("\\\\*\\\\*Verdict|## Code Review|claude-local-review"))] | length'],
                capture_output=True, text=True, check=True, timeout=60,
            ).stdout.strip()
            rounds = int(body) if body else 0
            if rounds >= 2:
                multi_round += 1
            elif rounds == 0:
                # merged with no review verdict at all: the CLEAN-without-review hole
                unreviewed += 1
        return {
            "sampled_prs": data["issueCount"],
            "commits_per_pr": commits_per_pr,
            "commits_per_pr_note": "first 100 PRs in window",
            "multi_round_reviews": multi_round,
            "unreviewed_merged": unreviewed,
            "review_sample": len(prs),
        }
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            FileNotFoundError, KeyError, json.JSONDecodeError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--repos", default="prism,flux,orbit")
    ap.add_argument("--owner", default="ArjenSchwarz")
    ap.add_argument("--with-gh", action="store_true",
                    help="also fetch review-churn metrics via gh (slower)")
    args = ap.parse_args()

    base = Path(os.environ.get("PERSONAL_PROJECTS", Path.home() / "projects" / "personal"))
    out = {
        "window_days": args.days,
        "computed_at": datetime.now().isoformat(timespec="seconds"),
        "repos": {},
    }
    for name in args.repos.split(","):
        name = name.strip()
        repo = base / name
        if not (repo / ".git").exists():
            out["repos"][name] = {"error": f"not a git repo: {repo}"}
            continue
        try:
            metrics = repo_metrics(repo, args.days)
        except RuntimeError as exc:
            out["repos"][name] = {"error": str(exc)}
            continue
        if args.with_gh:
            gh = gh_metrics(name, args.owner, args.days)
            if gh:
                metrics["review_churn"] = gh
        out["repos"][name] = metrics

    json.dump(out, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
