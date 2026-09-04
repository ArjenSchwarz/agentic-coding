"""Page orchestration: turn a review JSON document into the final HTML."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .common import escape
from .css import CSS
from .diffs import load_fragments
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
from .warnings import Warnings


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
    # both consume this dict. Uncovered line marks arrive with the Tests
    # section; until then every file has none.
    fragments = load_fragments(files, diff_dir, warnings)
    uncovered: dict[str, set[int]] = {}

    sections = {
        "pr-description": render_pr_description(data.get("pr_description", {})),
        "commits": render_commits(data.get("commits", [])),
        "explanation": render_explanation(data.get("explanation", {})),
        "important-changes": render_important_changes(important_changes),
        "decisions": render_decisions(data.get("decisions", [])),
        "findings": render_findings_table(findings),
        "unresolved-comments": render_unresolved_comments(data.get("unresolved_comments", [])),
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
        "unresolved-comments": "Unresolved comments",
        "diffs": "Per-file diffs",
        "double-check": "Things to double-check",
    }
    toc_entries = [(sid, toc_labels[sid]) for sid in sections if sections[sid]]

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return PAGE_TEMPLATE.substitute(
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
        toc=build_toc(toc_entries),
        pr_description_section=sections["pr-description"],
        commits_section=sections["commits"],
        explanation_section=sections["explanation"],
        important_changes_section=sections["important-changes"],
        decisions_section=sections["decisions"],
        findings_section=sections["findings"],
        unresolved_comments_section=sections["unresolved-comments"],
        files_section=sections["diffs"],
        double_check_section=sections["double-check"],
        timestamp=timestamp,
    )
