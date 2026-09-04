"""Section renderers for the review page.

Each function takes the relevant slice of the review JSON and returns
HTML, or an empty string when the section has nothing to show."""
from __future__ import annotations

import json
import textwrap

from .common import escape, file_anchor, severity_pill
from .diffs import render_diff


# --- section renderers -----------------------------------------------------

def render_metrics(metrics: list[dict]) -> str:
    return "\n".join(
        f'<span class="chip">{escape(m.get("label"))} '
        f'<strong>{escape(m.get("value"))}</strong></span>'
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
        f'<a href="#change-{i}">{escape(c.get("title"))}</a></li>'
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
      <p><span class="verdict-pill verdict-{tone}">{escape(verdict.get("label"))}</span></p>
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
                f'<a href="{escape(pr["url"])}">{escape(pr["author"])}</a>'
            )
        else:
            meta_parts.append(escape(pr["author"]))
    if pr.get("created_at"):
        meta_parts.append(escape(pr["created_at"]))
    meta_line = " · ".join(meta_parts)
    meta_html = (
        f'<div class="meta">{meta_line}</div>' if meta_line else ""
    )
    return f"""<section id="pr-description">
    <h2>Author's PR description</h2>
    <p class="muted">Shown verbatim — the markdown the author wrote, unmodified.</p>
    <div class="pr-description">
      {meta_html}
      <pre>{escape(pr["body"])}</pre>
    </div>
    </section>"""


def render_commits(items: list[dict]) -> str:
    if not items:
        return ""
    rows = []
    for c in items:
        sha = escape(c.get("sha"))
        subj = escape(c.get("subject"))
        meta = c.get("meta")
        if meta is not None:
            meta_html = escape(meta)
        else:
            meta_html = f'{escape(c.get("author"))} · {escape(c.get("date"))}'
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
        f'<label for="tab-{key}">{escape(label)}</label>'
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
        anchor = file_anchor(file_path) if file_path else ""
        what_text = escape(c.get("what"))
        what_block = (
            f'<p><strong>What to look at.</strong> '
            f'<a href="#{anchor}">{what_text}</a></p>'
            if anchor and what_text
            else (f'<p><strong>What to look at.</strong> {what_text}</p>' if what_text else "")
        )
        takeaway = c.get("takeaway")
        takeaway_block = (
            f'<div class="callout callout-takeaway">'
            f'<strong>Takeaway.</strong> {escape(takeaway)}</div>'
            if takeaway else ""
        )
        if c.get("rationale_unknown"):
            rationale_block = (
                '<div class="callout callout-warning">'
                '<strong>Open question.</strong> Rationale not stated by the author '
                'and not inferable from the diff.</div>'
            )
        elif c.get("rationale"):
            rationale_html = escape(c["rationale"])
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
              <h3>{escape(c.get("title"))}</h3>
              <p class="muted">{escape(file_path)}</p>
              <p><strong>Why it matters.</strong> {escape(c.get("why"))}</p>
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
            f'<strong>{escape(d.get("title"))}</strong> {body}</div>'
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
            f'<td>{severity_pill(f.get("severity", "nit"))}</td>'
            f'<td>{escape(f.get("area"))}</td>'
            f'<td>{escape(f.get("finding"))}</td>'
            f'<td>{escape(f.get("resolution"))}</td>'
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
            loc = escape(path)
            if line:
                loc += f":{escape(line)}"
            location_bits.append(f'<code>{loc}</code>')
        if created:
            location_bits.append(f'<span class="muted">{escape(created)}</span>')
        if url:
            location_bits.append(
                f'<a href="{escape(url)}" target="_blank" rel="noopener">view on GitHub</a>'
            )
        location_line = " · ".join(location_bits)

        body = escape(c.get("body") or "").replace("\n", "<br>")

        replies_html = ""
        replies = c.get("replies") or []
        if replies:
            reply_blocks = []
            for r in replies:
                r_author = escape(r.get("author") or "(unknown)")
                r_created = r.get("created_at")
                header_bits = [f'<strong>{r_author}</strong>']
                if r_created:
                    header_bits.append(f'<span class="muted">{escape(r_created)}</span>')
                r_body = escape(r.get("body") or "").replace("\n", "<br>")
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
            f'<span class="pill pill-warning">{escape(label)}</span> '
            f'<strong>{escape(author)}</strong>'
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
        f'<strong>{escape(d.get("title"))}</strong> {d.get("body", "")}</div>'
        for d in items
    )
    return f"""<section id="double-check">
    <h2>Things to double-check</h2>
    {callouts}
    </section>"""


def render_files(files: list[dict], fragments: dict[str, str],
                 uncovered: dict[str, set[int]]) -> str:
    """Per-file diff blocks.

    ``fragments`` comes from ``diffs.load_fragments``; ``uncovered`` maps a
    path to the new-file line numbers that have coverage data and zero hits.
    """
    if not files:
        return ""
    blocks = []
    for f in files:
        path = f.get("path", "")
        badge = f.get("badge", "Modified")
        stat = f.get("stat", "")
        diff = fragments.get(path, "(no diff provided)")
        anchor = file_anchor(path)
        badge_class = "badge-" + "".join(ch for ch in badge.lower() if ch.isalnum())
        blocks.append(textwrap.dedent(f"""\
            <details id="{anchor}" class="file-diff">
              <summary><span class="file-path">{escape(path)}</span> <span class="badge {badge_class}">{escape(badge)}</span> <span class="line-stat">{escape(stat)}</span></summary>
              <pre><code class="diff-block">{render_diff(diff, uncovered.get(path))}</code></pre>
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
        f'<li><a href="#{sid}">{escape(label)}</a></li>'
        for sid, label in entries
    )
    return f'<nav class="toc"><ul>{items}</ul></nav>'
