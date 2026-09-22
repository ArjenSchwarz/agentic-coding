"""Page orchestration: turn a review JSON document into the final HTML."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from .classify import is_docs_only
from .common import escape
from .css import CSS
from .diagram import render_diagram
from .diffs import load_fragments
from .inputs import read_json
from .junit import OUTCOMES
from .sections import (
    build_toc,
    render_at_a_glance,
    render_commits,
    render_decisions,
    render_double_check,
    render_explanation,
    render_files,
    render_findings_summary_card,
    render_findings_table,
    render_important_changes,
    render_important_links,
    render_metrics,
    render_pr_description,
    render_publish_metadata,
    render_unresolved_comments,
    render_verdict_card,
)
from .template import PAGE_TEMPLATE
from .tests_section import TestsResult, build_tests
from .warnings import Warnings


def docs_only(data: dict) -> bool:
    """Whether the change is docs-only.

    An explicit ``change_classification`` wins; otherwise the change is
    docs-only when no ``files[]`` entry classifies as code.
    """
    explicit = data.get("change_classification")
    if explicit is not None:
        return explicit == "docs-only"
    return is_docs_only(data.get("files", []))


def build_diagram(data: dict, diff_dir: Path | None, warnings: Warnings) -> str:
    """Section HTML for ``diagram_file``, or ``""``.

    A docs-only change suppresses the section silently; an absent, unreadable,
    or invalid description warns (naming the file) and omits it.
    """
    if docs_only(data):
        return ""
    name = data.get("diagram_file")
    if not name:
        return ""
    if diff_dir is None:
        warnings.add(f"{name}: diagram_file given but no diff directory to read it from")
        return ""
    desc = read_json(diff_dir / name, warnings, "diagram description")
    if desc is None:
        return ""
    return render_diagram(desc, warnings)


def render(data: dict, diff_dir: Path | None) -> str:
    warnings = Warnings()
    repo = data.get("repo", {})
    repo_name = escape(repo.get("name", "(repo)"))
    repo_path = escape(repo.get("path", ""))

    title = data.get("title") or f"Pre-push review: {repo.get('name', '')}"

    important_changes = data.get("important_changes", [])
    findings = data.get("findings", [])
    files = data.get("files", [])

    # Fragments are read once; the Tests section and the per-file diff blocks
    # both consume this dict. The Tests section supplies the uncovered line
    # marks the diff blocks draw, so it is built first.
    fragments = load_fragments(files, diff_dir, warnings)
    tests: TestsResult | None = None
    if data.get("tests") is not None and not docs_only(data):
        tests = build_tests(data["tests"], files, fragments, diff_dir, warnings)
    uncovered = tests.uncovered if tests else {}

    sections = {
        "pr-description": render_pr_description(data.get("pr_description", {})),
        "commits": render_commits(data.get("commits", [])),
        "explanation": render_explanation(data.get("explanation", {})),
        "important-changes": render_important_changes(important_changes),
        "decisions": render_decisions(data.get("decisions", [])),
        "findings": render_findings_table(findings),
        "tests": tests.section_html if tests else "",
        "unresolved-comments": render_unresolved_comments(data.get("unresolved_comments", [])),
        "diagram": build_diagram(data, diff_dir, warnings),
        "diffs": render_files(files, fragments, uncovered),
        "double-check": render_double_check(data.get("double_check", [])),
    }

    toc_labels = {
        "pr-description": "Author's description",
        "commits": "Commits",
        "explanation": "Three-level explanation",
        "important-changes": "Important changes (detailed)",
        "decisions": "Key decisions",
        "findings": "Review findings",
        "tests": "Tests",
        "unresolved-comments": "Unresolved comments",
        "diagram": "Blast radius",
        "diffs": "Per-file diffs",
        "double-check": "Things to double-check",
    }
    toc_entries = [(sid, toc_labels[sid]) for sid in sections if sections[sid]]

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    page = PAGE_TEMPLATE.substitute(
        title_plain=escape(title),
        title_html=escape(title),
        css=CSS,
        publish_metadata=render_publish_metadata(data.get("publish_metadata", {})),
        repo_name=repo_name,
        repo_path=repo_path,
        subtitle=data.get("subtitle", ""),
        metrics_chips=render_metrics(data.get("metrics", [])),
        at_a_glance=render_at_a_glance(data.get("at_a_glance", [])),
        important_links=render_important_links(important_changes),
        verdict_card=render_verdict_card(data.get("verdict", {})),
        findings_summary=render_findings_summary_card(findings),
        tests_card=tests.card_html if tests else "",
        toc=build_toc(toc_entries),
        pr_description_section=sections["pr-description"],
        commits_section=sections["commits"],
        explanation_section=sections["explanation"],
        important_changes_section=sections["important-changes"],
        decisions_section=sections["decisions"],
        findings_section=sections["findings"],
        tests_section=sections["tests"],
        unresolved_comments_section=sections["unresolved-comments"],
        diagram_section=sections["diagram"],
        files_section=sections["diffs"],
        double_check_section=sections["double-check"],
        timestamp=timestamp,
    )

    # The skill greps these two lines to apply the severity floor; they must
    # be the last thing on stderr, after every warning.
    if tests:
        c = tests.counts
        print(f"summary coverage: matched={c['matched']} unmatched={c['unmatched']}", file=sys.stderr)
        tallies = " ".join(f"{o}={c[o]}" for o in OUTCOMES + ("flaky",))
        print(f"summary tests: {tallies}", file=sys.stderr)
    return page
