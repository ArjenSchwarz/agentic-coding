#!/usr/bin/env python3
"""Render a pre-push review HTML page from a JSON description.

Used by the pre-push-review skill. The skill writes the structured review
content to a JSON file, optionally drops per-file diff fragments next to it,
then invokes this script to produce a self-contained HTML page styled with
the Prism Dark palette.

Usage:
    python3 build_review_html.py --data review.json --output review.html
                                 [--diff-dir /path/to/diff/fragments]

JSON schema (see SKILL.md "Phase 7" for the contract):

    {
      "repo":            {"name", "path", "branch", "remote"},
      "title":           "Pre-push review: <repo>",
      "subtitle":        "<html string>",
      "metrics":         [{"label", "value"}, ...],
      "verdict":         {"label", "tone": "success|warning|error", "detail"},
      "at_a_glance":     ["<html string>", ...],
      "pr_description":  {"author"?, "url"?, "created_at"?, "body": "verbatim markdown"},
      "explanation":     {"beginner": "<html>", "intermediate": "<html>", "expert": "<html>"},
      "commits":         [{"sha", "subject", "author", "date", "meta"?}, ...],
      "important_changes": [
        {"title", "file", "why", "what",
         "takeaway"?, "rationale"?,
         "rationale_inferred"?, "rationale_unknown"?}, ...
      ],
      "decisions":       [{"title", "body": "<html>", "inferred"?: bool}, ...],
      "findings":        [{"severity", "area", "finding", "resolution",
                            "status": "fixed|skipped"}, ...],
      "unresolved_comments": [
        {"author", "type": "code|review|discussion",
         "path"?, "line"?, "body": "verbatim markdown",
         "url"?, "created_at"?,
         "replies"?: [{"author", "body", "created_at"?}, ...]}, ...
      ],
      "double_check":    [{"title", "body": "<html>"}, ...],
      "files":           [{"path", "badge", "stat",
                            "kind"?: "code|docs|other",   // derived from path when absent
                            "diff"?: "<text>", "diff_file"?: "name.txt"}, ...],
      "tests":           {...},              // optional; the Tests card and section, see
                                             // specs/review-html-tests-diagram/design.md
      "diagram_file":    "diagram.json",     // optional; written by blast_radius.py, read
                                             // relative to --diff-dir (Blast radius section)
      "change_classification": "docs-only",  // optional override; derived from files[] kinds
                                             // when absent. docs-only suppresses Tests and
                                             // Blast radius
      "publish_metadata": {                  // optional; emits a <script id="review-meta">
        "title":    "...",                   // block in <head> consumable by `pulsar publish`
        "repoUrl":  "https://...",
        "pr":       42,                      // exactly one of pr or branch
        "branch":   "feature/x",
        "severity": "lgtm|suggestions|needs-changes|blocking",
        "summary":  "1-3 sentence headline finding"
      }
    }

Rendering contract:
  * HTML pass-through fields: subtitle, at_a_glance items, verdict.detail,
    explanation panels, decisions[].body, double_check[].body.
  * Everything else is treated as plain text and HTML-escaped.
  * Empty sections are omitted from both the body and the table of contents.
  * Per-file diffs are grouped Code, Docs, Other (review_html/classify.py)
    with a composition line; a change with a single kind has no group headings.

The rendering itself lives in the ``review_html`` package next to this file;
this script only owns the command line.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ~/.claude/scripts is a symlink into the repository; resolve the real
# location so the package is found under -P or when invoked via the link.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import review_html  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render a pre-push review HTML page from a JSON description.")
    parser.add_argument("--data", required=True, type=Path,
                        help="Path to the JSON file describing the review.")
    parser.add_argument("--output", required=True, type=Path,
                        help="Path to write the generated HTML page.")
    parser.add_argument("--diff-dir", type=Path, default=None,
                        help="Directory containing diff fragments referenced by "
                             "files[].diff_file. Defaults to the JSON file's directory.")
    args = parser.parse_args()

    if not args.data.exists():
        print(f"error: data file not found: {args.data}", file=sys.stderr)
        return 1

    diff_dir = args.diff_dir if args.diff_dir is not None else args.data.parent
    try:
        data = json.loads(args.data.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        print(f"error: {args.data}: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(review_html.render(data, diff_dir), encoding="utf-8")
    print(str(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
