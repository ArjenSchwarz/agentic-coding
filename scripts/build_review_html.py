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
                            "diff"?: "<text>", "diff_file"?: "name.txt"}, ...],
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
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from string import Template


# --- helpers ---------------------------------------------------------------

def _escape(s: object) -> str:
    return html.escape("" if s is None else str(s))


def _file_anchor(path: str) -> str:
    return "file-" + hashlib.sha1(path.encode("utf-8")).hexdigest()[:10]


def _severity_pill(sev: str) -> str:
    klass = {
        "blocking": "error",
        "major": "error",
        "minor": "warning",
        "nit": "tertiary",
        "info": "tertiary",
    }.get(sev.lower(), "tertiary")
    return f'<span class="pill pill-{klass}">{_escape(sev)}</span>'


# --- section renderers -----------------------------------------------------

def render_metrics(metrics: list[dict]) -> str:
    return "\n".join(
        f'<span class="chip">{_escape(m.get("label"))} '
        f'<strong>{_escape(m.get("value"))}</strong></span>'
        for m in metrics
    )


def render_at_a_glance(items: list[str]) -> str:
    if not items:
        return ""
    bullets = "\n".join(f"<li>{item}</li>" for item in items)
    return f"""<div class="card">
      <h3>At a glance</h3>
      <ul>{bullets}</ul>
    </div>"""


def render_important_links(changes: list[dict]) -> str:
    if not changes:
        return ""
    bullets = "".join(
        f'<li><span class="tag">key</span>'
        f'<a href="#change-{i}">{_escape(c.get("title"))}</a></li>'
        for i, c in enumerate(changes)
    )
    return f"""<div class="card">
      <h3>Important changes</h3>
      <ul>{bullets}</ul>
    </div>"""


def render_verdict_card(verdict: dict) -> str:
    if not verdict:
        return ""
    tone = verdict.get("tone", "success")
    if tone not in ("success", "warning", "error"):
        tone = "success"
    return f"""<div class="card">
      <h3>Verdict</h3>
      <p><span class="verdict-pill verdict-{tone}">{_escape(verdict.get("label"))}</span></p>
      <p class="muted">{verdict.get("detail", "")}</p>
    </div>"""


def render_findings_summary_card(findings: list[dict]) -> str:
    if not findings:
        return ""
    raised = len(findings)
    fixed = sum(1 for f in findings if f.get("status", "fixed") == "fixed")
    skipped = raised - fixed
    return f"""<div class="card">
      <h3>Review findings</h3>
      <p>{raised} raised · {fixed} fixed · {skipped} skipped</p>
      <p><a href="#findings">Jump to findings →</a></p>
    </div>"""


def render_pr_description(pr: dict) -> str:
    """Render the PR author's body verbatim.

    The body is HTML-escaped and dropped into a <pre> with pre-wrap so the
    author's original text and line breaks survive unchanged. Markdown stays
    visible as markdown — no parser is applied because the point is to show
    motivation as the author wrote it, not the reviewer's interpretation.
    """
    if not pr or not pr.get("body"):
        return ""
    meta_parts = []
    if pr.get("author"):
        if pr.get("url"):
            meta_parts.append(
                f'<a href="{_escape(pr["url"])}">{_escape(pr["author"])}</a>'
            )
        else:
            meta_parts.append(_escape(pr["author"]))
    if pr.get("created_at"):
        meta_parts.append(_escape(pr["created_at"]))
    meta_line = " · ".join(meta_parts)
    meta_html = (
        f'<div class="meta">{meta_line}</div>' if meta_line else ""
    )
    return f"""<section id="pr-description">
    <h2>Author's PR description</h2>
    <p class="muted">Shown verbatim — the markdown the author wrote, unmodified.</p>
    <div class="pr-description">
      {meta_html}
      <pre>{_escape(pr["body"])}</pre>
    </div>
    </section>"""


def render_commits(items: list[dict]) -> str:
    if not items:
        return ""
    rows = []
    for c in items:
        sha = _escape(c.get("sha"))
        subj = _escape(c.get("subject"))
        meta = c.get("meta")
        if meta is not None:
            meta_html = _escape(meta)
        else:
            meta_html = f'{_escape(c.get("author"))} · {_escape(c.get("date"))}'
        rows.append(
            f'<li><code class="commit-sha">{sha}</code> '
            f'<span class="commit-subj">{subj}</span> '
            f'<span class="commit-meta">— {meta_html}</span></li>'
        )
    return f"""<section id="commits">
    <h2>Commits</h2>
    <ul class="commit-list">{"".join(rows)}</ul>
    </section>"""


def render_explanation(panels: dict) -> str:
    if not panels:
        return ""
    order = [("beginner", "Beginner"),
             ("intermediate", "Intermediate"),
             ("expert", "Expert")]
    levels = [(key, label, panels[key]) for key, label in order if panels.get(key)]
    if not levels:
        return ""
    radios = "\n".join(
        f'<input type="radio" name="tabs" id="tab-{key}"'
        f'{" checked" if i == 0 else ""}>'
        for i, (key, _, _) in enumerate(levels)
    )
    labels = "\n".join(
        f'<label for="tab-{key}">{_escape(label)}</label>'
        for key, label, _ in levels
    )
    panels_html = "\n".join(
        f'<div id="panel-{key}" class="tab-panel">{content}</div>'
        for key, _, content in levels
    )
    return f"""<section id="explanation">
    <h2>Three-level explanation</h2>
    <div class="tabs">
      {radios}
      <div class="tab-labels">{labels}</div>
      <div class="tab-panels">{panels_html}</div>
    </div>
    </section>"""


def render_important_changes(changes: list[dict]) -> str:
    if not changes:
        return ""
    cards = []
    for i, c in enumerate(changes):
        file_path = c.get("file", "")
        file_anchor = _file_anchor(file_path) if file_path else ""
        what_text = _escape(c.get("what"))
        what_block = (
            f'<p><strong>What to look at.</strong> '
            f'<a href="#{file_anchor}">{what_text}</a></p>'
            if file_anchor and what_text
            else (f'<p><strong>What to look at.</strong> {what_text}</p>' if what_text else "")
        )
        takeaway = c.get("takeaway")
        takeaway_block = (
            f'<div class="callout callout-takeaway">'
            f'<strong>Takeaway.</strong> {_escape(takeaway)}</div>'
            if takeaway else ""
        )
        if c.get("rationale_unknown"):
            rationale_block = (
                '<div class="callout callout-warning">'
                '<strong>Open question.</strong> Rationale not stated by the author '
                'and not inferable from the diff.</div>'
            )
        elif c.get("rationale"):
            rationale_html = _escape(c["rationale"])
            if c.get("rationale_inferred"):
                rationale_html += (
                    ' <span class="muted">(inferred — not stated by the author)</span>'
                )
            rationale_block = (
                '<div class="callout callout-rationale">'
                f'<strong>Rationale.</strong> {rationale_html}</div>'
            )
        else:
            rationale_block = ""
        cards.append(textwrap.dedent(f"""\
            <div class="change-card" id="change-{i}">
              <h3>{_escape(c.get("title"))}</h3>
              <p class="muted">{_escape(file_path)}</p>
              <p><strong>Why it matters.</strong> {_escape(c.get("why"))}</p>
              {what_block}
              {takeaway_block}
              {rationale_block}
            </div>"""))
    return f"""<section id="important-changes">
    <h2>Important changes — detailed</h2>
    {"".join(cards)}
    </section>"""


def render_decisions(items: list[dict]) -> str:
    if not items:
        return ""
    callouts = []
    for d in items:
        body = d.get("body", "")
        if d.get("inferred"):
            body = body + ' <span class="muted">(inferred — not stated by the author.)</span>'
        callouts.append(
            '<div class="callout callout-rationale">'
            f'<strong>{_escape(d.get("title"))}</strong> {body}</div>'
        )
    return f"""<section id="decisions">
    <h2>Key decisions</h2>
    {"".join(callouts)}
    </section>"""


def render_findings_table(findings: list[dict]) -> str:
    if not findings:
        return ""
    rows = []
    for f in findings:
        rows.append(
            "<tr>"
            f'<td>{_severity_pill(f.get("severity", "nit"))}</td>'
            f'<td>{_escape(f.get("area"))}</td>'
            f'<td>{_escape(f.get("finding"))}</td>'
            f'<td>{_escape(f.get("resolution"))}</td>'
            "</tr>"
        )
    return f"""<section id="findings">
    <h2>Review findings</h2>
    <table class="findings">
      <thead><tr><th>Severity</th><th>Area</th><th>Finding</th><th>Resolution</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
    </section>"""


def render_unresolved_comments(items: list[dict]) -> str:
    if not items:
        return ""

    type_labels = {"code": "code", "review": "review", "discussion": "discussion"}

    cards = []
    for c in items:
        ctype = (c.get("type") or "discussion").lower()
        label = type_labels.get(ctype, ctype)
        author = c.get("author") or "(unknown)"
        url = c.get("url")
        created = c.get("created_at")
        path = c.get("path")
        line = c.get("line")

        location_bits = []
        if path:
            loc = _escape(path)
            if line:
                loc += f":{_escape(line)}"
            location_bits.append(f'<code>{loc}</code>')
        if created:
            location_bits.append(f'<span class="muted">{_escape(created)}</span>')
        if url:
            location_bits.append(
                f'<a href="{_escape(url)}" target="_blank" rel="noopener">view on GitHub</a>'
            )
        location_line = " · ".join(location_bits)

        body = _escape(c.get("body") or "").replace("\n", "<br>")

        replies_html = ""
        replies = c.get("replies") or []
        if replies:
            reply_blocks = []
            for r in replies:
                r_author = _escape(r.get("author") or "(unknown)")
                r_created = r.get("created_at")
                header_bits = [f'<strong>{r_author}</strong>']
                if r_created:
                    header_bits.append(f'<span class="muted">{_escape(r_created)}</span>')
                r_body = _escape(r.get("body") or "").replace("\n", "<br>")
                reply_blocks.append(
                    '<div class="reply">'
                    f'<div class="reply-header">{" · ".join(header_bits)}</div>'
                    f'<div class="reply-body">{r_body}</div>'
                    '</div>'
                )
            replies_html = (
                '<details class="replies">'
                f'<summary>{len(replies)} earlier repl'
                f'{"y" if len(replies) == 1 else "ies"}</summary>'
                f'{"".join(reply_blocks)}'
                '</details>'
            )

        cards.append(
            '<div class="unresolved-comment">'
            '<div class="unresolved-header">'
            f'<span class="pill pill-warning">{_escape(label)}</span> '
            f'<strong>{_escape(author)}</strong>'
            f'{" · " + location_line if location_line else ""}'
            '</div>'
            f'<div class="unresolved-body">{body}</div>'
            f'{replies_html}'
            '</div>'
        )

    return f"""<section id="unresolved-comments">
    <h2>Unresolved comments</h2>
    <p class="muted">Open review threads and PR-level comments still awaiting a response.</p>
    {"".join(cards)}
    </section>"""


def render_double_check(items: list[dict]) -> str:
    if not items:
        return ""
    callouts = "".join(
        '<div class="callout callout-warning">'
        f'<strong>{_escape(d.get("title"))}</strong> {d.get("body", "")}</div>'
        for d in items
    )
    return f"""<section id="double-check">
    <h2>Things to double-check</h2>
    {callouts}
    </section>"""


def render_files(files: list[dict], diff_dir: Path | None) -> str:
    if not files:
        return ""
    blocks = []
    for f in files:
        path = f.get("path", "")
        badge = f.get("badge", "Modified")
        stat = f.get("stat", "")
        diff = f.get("diff")
        if diff is None and f.get("diff_file") and diff_dir is not None:
            fragment = diff_dir / f["diff_file"]
            try:
                diff = fragment.read_text(encoding="utf-8")
            except FileNotFoundError:
                diff = f"(diff fragment {f['diff_file']!r} missing)"
        if diff is None:
            diff = "(no diff provided)"
        anchor = _file_anchor(path)
        badge_class = "badge-" + "".join(ch for ch in badge.lower() if ch.isalnum())
        blocks.append(textwrap.dedent(f"""\
            <details id="{anchor}" class="file-diff">
              <summary><span class="file-path">{_escape(path)}</span> <span class="badge {badge_class}">{_escape(badge)}</span> <span class="line-stat">{_escape(stat)}</span></summary>
              <pre><code class="language-diff">{_escape(diff)}</code></pre>
            </details>"""))
    return f"""<section id="diffs">
    <h2>Per-file diffs</h2>
    <p class="muted">Click to expand.</p>
    {"".join(blocks)}
    </section>"""


def render_publish_metadata(meta: dict) -> str:
    """Emit a <script id="review-meta"> block consumable by `pulsar publish`.

    See pulsar's docs/agent-contract.md. Fields are passed through verbatim,
    minus a `</` escape inside the JSON to prevent premature </script> closure.
    """
    if not meta:
        return ""
    payload = json.dumps(meta, indent=2, ensure_ascii=False).replace("</", "<\\/")
    return (
        f'<script type="application/json" id="review-meta">\n{payload}\n</script>'
    )


def build_toc(entries: list[tuple[str, str]]) -> str:
    if not entries:
        return ""
    items = "\n".join(
        f'<li><a href="#{sid}">{_escape(label)}</a></li>'
        for sid, label in entries
    )
    return f'<nav class="toc"><ul>{items}</ul></nav>'


# --- CSS (Prism Dark palette) ---------------------------------------------

CSS = """
:root {
  --bg: #0B1020;
  --bg-deep: #050C1B;
  --surface-1: #101A33;
  --surface-2: #142042;
  --border: #26324F;
  --border-subtle: #1F2A45;
  --text-primary: #EAF1FF;
  --text-secondary: #B7C3E3;
  --text-tertiary: #7F8BB0;
  --accent: #44C4DC;
  --accent-2: #E474E4;
  --accent-3: #4C6CBC;
  --code-bg: #0A1226;
  --code-border: #1F2A45;
  --success: #22C55E;
  --warning: #FBBF24;
  --error: #EF476F;
  --diff-add-bg: rgba(34, 197, 94, 0.12);
  --diff-add-fg: #86EFAC;
  --diff-del-bg: rgba(239, 71, 111, 0.12);
  --diff-del-fg: #FCA5A5;
}

* { box-sizing: border-box; }
html { background: var(--bg); }
body {
  background: var(--bg);
  color: var(--text-primary);
  font-family: -apple-system, "SF Pro Text", system-ui, sans-serif;
  line-height: 1.6;
  margin: 0;
  padding: 0;
}

.page { max-width: 1100px; margin: 0 auto; padding: 32px; }

header.top-bar {
  position: sticky; top: 0; z-index: 10;
  background: var(--bg-deep);
  border-bottom: 1px solid var(--border-subtle);
}
.top-stripe { height: 4px; background: linear-gradient(135deg, var(--accent-3), var(--accent-2)); }
.top-content {
  display: flex; gap: 16px; flex-wrap: wrap; align-items: center;
  padding: 14px 32px; max-width: 1100px; margin: 0 auto;
}
.top-content .repo-title { font-weight: 600; font-size: 15px; color: var(--text-primary); }

.chip {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--surface-1); border: 1px solid var(--border-subtle);
  border-radius: 999px; padding: 4px 12px; font-size: 12px; color: var(--text-secondary);
}
.chip strong { color: var(--text-primary); }

h1, h2, h3 { color: var(--text-primary); line-height: 1.3; }
h1 { font-size: 30px; margin: 8px 0 4px; }
h2 { font-size: 22px; margin: 32px 0 12px; padding-top: 12px; border-top: 1px solid var(--border-subtle); }
h3 { font-size: 17px; margin: 16px 0 8px; }

p { color: var(--text-secondary); }
strong { color: var(--text-primary); }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.muted { color: var(--text-tertiary); }
code { font-family: ui-monospace, "SF Mono", Menlo, monospace; }

.card-grid {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;
  margin: 24px 0 32px;
}

.card {
  background: var(--surface-1); border: 1px solid var(--border);
  border-radius: 16px; padding: 20px;
  transition: background-color 120ms ease;
}
.card:hover { background: var(--surface-2); }
.card h3 {
  margin-top: 0; font-size: 14px;
  text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-tertiary);
}
.card ul { margin: 8px 0 0; padding-left: 20px; }
.card li { margin: 4px 0; color: var(--text-secondary); }

.tag {
  display: inline-block;
  background: rgba(228, 116, 228, 0.15);
  color: var(--accent-2);
  border-radius: 4px;
  padding: 0 6px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  margin-right: 6px;
}

.verdict-pill {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 10px 18px; border-radius: 999px;
  font-weight: 600; font-size: 14px;
  text-transform: uppercase; letter-spacing: 0.05em;
}
.verdict-success { background: rgba(34, 197, 94, 0.18); color: var(--success); border: 1px solid rgba(34,197,94,0.35); }
.verdict-warning { background: rgba(251, 191, 36, 0.15); color: var(--warning); border: 1px solid rgba(251,191,36,0.35); }
.verdict-error   { background: rgba(239, 71, 111, 0.15); color: var(--error);   border: 1px solid rgba(239,71,111,0.35); }

.toc {
  background: var(--surface-1); border: 1px solid var(--border);
  border-radius: 16px; padding: 16px 20px; margin: 0 0 24px;
}
.toc ul { list-style: none; padding-left: 0; margin: 0; column-count: 2; column-gap: 24px; }
.toc li { margin: 4px 0; }
.toc a { color: var(--text-secondary); }
.toc a:hover { color: var(--accent); }

.tabs {
  margin: 16px 0; border: 1px solid var(--border);
  border-radius: 16px; background: var(--surface-1);
}
.tabs input[type="radio"] { display: none; }
.tab-labels { display: flex; border-bottom: 1px solid var(--border-subtle); }
.tab-labels label {
  padding: 12px 20px; cursor: pointer; color: var(--text-tertiary);
  font-weight: 600; font-size: 13px;
  text-transform: uppercase; letter-spacing: 0.06em;
  border-bottom: 2px solid transparent; margin-bottom: -1px;
}
.tab-labels label:hover { color: var(--text-secondary); }

#tab-beginner:checked ~ .tab-labels label[for="tab-beginner"],
#tab-intermediate:checked ~ .tab-labels label[for="tab-intermediate"],
#tab-expert:checked ~ .tab-labels label[for="tab-expert"] {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.tab-panels { padding: 20px; }
.tab-panel { display: none; }
#tab-beginner:checked ~ .tab-panels #panel-beginner,
#tab-intermediate:checked ~ .tab-panels #panel-intermediate,
#tab-expert:checked ~ .tab-panels #panel-expert {
  display: block;
}

.change-card {
  background: var(--surface-1); border: 1px solid var(--border);
  border-radius: 16px; padding: 20px; margin: 16px 0;
  transition: background-color 120ms ease;
}
.change-card:hover { background: var(--surface-2); }

.callout {
  margin: 12px 0; padding: 10px 14px;
  background: var(--bg-deep);
  border-radius: 6px; font-size: 14px; color: var(--text-secondary);
}
.callout-takeaway  { border-left: 3px solid var(--accent-2); }
.callout-rationale { border-left: 3px solid var(--accent); }
.callout-warning   { border-left: 3px solid var(--warning); }

table.findings {
  width: 100%; border-collapse: collapse;
  margin: 16px 0; background: var(--surface-1);
  border: 1px solid var(--border); border-radius: 12px; overflow: hidden;
}
table.findings th, table.findings td {
  padding: 10px 14px; text-align: left;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 14px; vertical-align: top;
}
table.findings th {
  background: var(--surface-2); color: var(--text-secondary);
  text-transform: uppercase; font-size: 11px; letter-spacing: 0.08em;
}
table.findings tr:last-child td { border-bottom: none; }

.pill {
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.06em;
}
.pill-error    { background: rgba(239,71,111,0.18); color: var(--error); }
.pill-warning  { background: rgba(251,191,36,0.18); color: var(--warning); }
.pill-success  { background: rgba(34,197,94,0.18); color: var(--success); }
.pill-tertiary { background: rgba(127,139,176,0.18); color: var(--text-tertiary); }

.unresolved-comment {
  background: var(--surface-1); border: 1px solid var(--border);
  border-left: 3px solid var(--warning);
  border-radius: 10px; padding: 14px 16px; margin: 12px 0;
}
.unresolved-header {
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
  font-size: 13px; color: var(--text-secondary); margin-bottom: 8px;
}
.unresolved-header code {
  background: var(--code-bg); color: var(--accent);
  padding: 1px 6px; border-radius: 4px; font-size: 12px;
}
.unresolved-body {
  color: var(--text-primary); font-size: 14px; line-height: 1.55;
  white-space: pre-wrap; word-break: break-word;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
}
.replies {
  margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--border-subtle);
}
.replies > summary {
  cursor: pointer; color: var(--text-tertiary); font-size: 12px;
}
.reply { margin: 8px 0 0 12px; padding-left: 10px; border-left: 2px solid var(--border-subtle); }
.reply-header { font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }
.reply-body {
  color: var(--text-primary); font-size: 13px;
  white-space: pre-wrap; word-break: break-word;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
}

.commit-list { list-style: none; padding-left: 0; }
.commit-list li { padding: 6px 0; border-bottom: 1px solid var(--border-subtle); }
.commit-list li:last-child { border-bottom: none; }
.commit-sha {
  color: var(--accent); background: var(--code-bg);
  padding: 2px 6px; border-radius: 4px;
  font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 12px;
}
.commit-subj { color: var(--text-primary); }
.commit-meta { color: var(--text-tertiary); font-size: 13px; }

.file-diff {
  background: var(--surface-1); border: 1px solid var(--border);
  border-radius: 12px; margin: 8px 0; overflow: hidden;
}
.file-diff > summary {
  cursor: pointer; padding: 12px 16px; font-weight: 500;
  list-style: none; display: flex; gap: 12px; align-items: center;
}
.file-diff > summary::-webkit-details-marker { display: none; }
.file-diff > summary::before {
  content: "▸"; color: var(--text-tertiary); font-size: 12px; margin-right: 4px;
}
.file-diff[open] > summary::before { content: "▾"; }
.file-path { font-family: ui-monospace, "SF Mono", Menlo, monospace; color: var(--text-primary); }
.line-stat {
  color: var(--text-tertiary);
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 12px; margin-left: auto;
}

.badge {
  display: inline-block; font-size: 10px;
  text-transform: uppercase; letter-spacing: 0.06em; font-weight: 700;
  padding: 2px 8px; border-radius: 4px;
}
.badge-added    { background: rgba(34,197,94,0.18);  color: var(--success); }
.badge-modified { background: rgba(68,196,220,0.18); color: var(--accent); }
.badge-deleted  { background: rgba(239,71,111,0.18); color: var(--error); }
.badge-renamed  { background: rgba(76,108,188,0.18); color: var(--accent-3); }

.file-diff pre {
  margin: 0; background: var(--code-bg);
  border-top: 1px solid var(--code-border);
  padding: 12px 16px; overflow-x: auto; line-height: 1.45;
}
.file-diff code {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 13px; color: var(--text-secondary); white-space: pre;
}

.hljs-addition, code .hljs-addition {
  background: var(--diff-add-bg) !important;
  color: var(--diff-add-fg) !important;
  display: block;
}
.hljs-deletion, code .hljs-deletion {
  background: var(--diff-del-bg) !important;
  color: var(--diff-del-fg) !important;
  display: block;
}
.hljs-meta, code .hljs-meta { color: var(--text-tertiary) !important; }
.hljs-comment, code .hljs-comment { color: var(--text-tertiary) !important; }

.pr-description {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent-2);
  border-radius: 12px;
  padding: 16px 20px;
  margin: 8px 0 16px;
}
.pr-description .meta {
  color: var(--text-tertiary);
  font-size: 12px;
  margin-bottom: 12px;
}
.pr-description pre {
  margin: 0;
  background: transparent;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 13px;
  line-height: 1.55;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-wrap: break-word;
}
.pr-description pre code,
.pr-description pre a { color: var(--text-primary); }

footer {
  margin-top: 64px; padding-top: 24px;
  border-top: 1px solid var(--border-subtle);
  color: var(--text-tertiary); font-size: 13px;
}

@media (max-width: 720px) {
  .card-grid { grid-template-columns: 1fr; }
  .toc ul { column-count: 1; }
  .page { padding: 16px; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; }
}
"""


# --- top-level template ----------------------------------------------------

PAGE_TEMPLATE = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>$title_plain</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
$publish_metadata
<style>$css</style>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/atom-one-dark.min.css">
<script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/highlight.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/languages/diff.min.js" defer></script>
<script>document.addEventListener("DOMContentLoaded", function () { if (window.hljs) hljs.highlightAll(); });</script>
</head>
<body>
<header class="top-bar">
  <div class="top-stripe"></div>
  <div class="top-content">
    <span class="repo-title">$repo_name</span>
    $metrics_chips
  </div>
</header>

<div class="page">
  <h1>$title_html</h1>
  <p class="muted">$subtitle</p>

  <section class="card-grid">
    $at_a_glance
    $important_links
    $verdict_card
    $findings_summary
  </section>

  $toc

  $pr_description_section
  $commits_section
  $explanation_section
  $important_changes_section
  $decisions_section
  $findings_section
  $unresolved_comments_section
  $files_section
  $double_check_section

  <footer>
    Generated $timestamp · repo <code>$repo_path</code> · regenerate with <code>/pre-push-review</code>.
  </footer>
</div>
</body>
</html>
""")


def render(data: dict, diff_dir: Path | None) -> str:
    repo = data.get("repo", {})
    repo_name = _escape(repo.get("name", "(repo)"))
    repo_path = _escape(repo.get("path", ""))

    title = data.get("title") or f"Pre-push review: {repo.get('name', '')}"

    important_changes = data.get("important_changes", [])
    findings = data.get("findings", [])

    sections = {
        "pr-description": render_pr_description(data.get("pr_description", {})),
        "commits": render_commits(data.get("commits", [])),
        "explanation": render_explanation(data.get("explanation", {})),
        "important-changes": render_important_changes(important_changes),
        "decisions": render_decisions(data.get("decisions", [])),
        "findings": render_findings_table(findings),
        "unresolved-comments": render_unresolved_comments(data.get("unresolved_comments", [])),
        "diffs": render_files(data.get("files", []), diff_dir),
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
        title_plain=_escape(title),
        title_html=_escape(title),
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
    data = json.loads(args.data.read_text(encoding="utf-8"))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(data, diff_dir), encoding="utf-8")
    print(str(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
