"""Stylesheet for the review page (Prism Dark palette).

``CSS`` is substituted into the page template as a value, never pasted
into the template literal, so ``$`` inside it needs no escaping."""
from __future__ import annotations

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

table.findings, table.tests {
  width: 100%; border-collapse: collapse;
  margin: 16px 0; background: var(--surface-1);
  border: 1px solid var(--border); border-radius: 12px; overflow: hidden;
}
table.findings th, table.findings td,
table.tests th, table.tests td {
  padding: 10px 14px; text-align: left;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 14px; vertical-align: top;
}
table.findings th, table.tests th {
  background: var(--surface-2); color: var(--text-secondary);
  text-transform: uppercase; font-size: 11px; letter-spacing: 0.08em;
}
table.findings tr:last-child td, table.tests tr:last-child td { border-bottom: none; }
table.tests td:last-child { white-space: pre-wrap; word-break: break-word; }
table.tests a { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 13px; }

.tests-provenance, .tests-availability, .tests-totals, .tests-matching {
  font-size: 14px; color: var(--text-secondary);
}
.tests-nodata {
  border-left: 3px solid var(--warning);
  margin: 16px 0;
}
.tests-nodata:hover { background: var(--surface-1); }

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
  padding: 12px 0; overflow-x: auto; line-height: 1.45;
}
.file-diff code {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 13px; color: var(--text-secondary);
  display: inline-block; min-width: 100%;
}
.diff-line {
  display: block;
  padding: 0 16px;
  min-height: 1.45em;
}
.diff-add         { background: var(--diff-add-bg); color: var(--diff-add-fg); }
.diff-del         { background: var(--diff-del-bg); color: var(--diff-del-fg); }
.diff-hunk        { color: var(--accent); }
.diff-file-header { color: var(--text-tertiary); }
.diff-meta        { color: var(--text-tertiary); }
.diff-context     { color: var(--text-secondary); }
.diff-uncovered {
  border-left: 3px solid var(--error);
  padding-left: 13px;
}
.diff-uncovered::before {
  content: "▌"; color: var(--error); margin-right: 6px;
}

.blast-scroll {
  overflow-x: auto;
  background: var(--surface-1); border: 1px solid var(--border);
  border-radius: 12px; padding: 12px; margin: 12px 0;
}
.blast-scroll svg { display: block; }
.blast-legend {
  display: flex; flex-wrap: wrap; gap: 8px 18px;
  margin: 12px 0; font-size: 13px; color: var(--text-secondary);
}
.blast-key { display: inline-flex; align-items: center; gap: 6px; }
.blast-swatch {
  display: inline-block; width: 14px; height: 14px; border-radius: 3px;
  background: var(--surface-2); border: 1px solid var(--border);
}
.blast-swatch-added    { background: rgba(34,197,94,0.18);   border-color: var(--success); }
.blast-swatch-modified { background: rgba(228,116,228,0.18); border-color: var(--accent-2); }
.blast-swatch-deleted  { background: rgba(239,71,111,0.18);  border-color: var(--error); }
.blast-swatch-renamed  { background: rgba(76,108,188,0.18);  border-color: var(--accent-3); }
.blast-swatch-collapsed { border-style: dashed; }
.blast-members, .blast-skipped { font-size: 13px; color: var(--text-secondary); }
.blast-members code, .blast-skipped code { color: var(--text-primary); font-size: 12px; }

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
