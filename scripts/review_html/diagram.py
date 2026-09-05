"""Blast-radius diagram: projection of the one-hop graph, layout, and SVG.

``project`` applies the rendering rules the skill never applies (test
exclusion, expansion collapse, the column cap) and knows nothing about SVG;
``layout`` turns a ``Projected`` into boxes, frames, and edge paths using
the fixed constants below; ``render_diagram`` emits the section HTML.
"""
from __future__ import annotations

import math
import textwrap
from dataclasses import dataclass, field

from .common import digest, escape, file_anchor
from .warnings import Warnings

CAP = 15                 # side-column node cap (requirement 4.8)
COLLAPSE_ABOVE = 3       # expansion groups larger than this collapse (4.6)

COLUMNS = ("dependents", "changed", "dependencies")
SIDE_COLUMNS = ("dependents", "dependencies")
CHANGED_STATUSES = ("added", "modified", "deleted", "renamed")

# Layout constants (design, Q36 and Q56). Every text element declares a
# textLength of len(text) * ADV so the fit holds whatever font renders it.
ADV = 7.2
PAD = 10
BOX_H = 26
ROW_GAP = 8
GROUP_PAD = 8
GROUP_HEADER = 18
GROUP_GAP = 14
GUTTER = 56
LANE = 24
CONTENT_W = 1036
COL_W = (CONTENT_W - 2 * GUTTER) // 3          # 308
SIDE_BOX_W = COL_W - 2 * GROUP_PAD             # 292
CENTRE_BOX_W = SIDE_BOX_W - LANE               # 268
BADGE_RESERVE = 4                              # characters kept for the ⚑N badge
TRACK_GAP = 6                                  # centre lane tracks, three of them
LINE_H = 16                                    # header note and reason lines
TITLE_Y = 12
NOTES_Y = 30
BOTTOM_PAD = 16

COL_X = {"dependents": 0, "changed": COL_W + GUTTER, "dependencies": 2 * (COL_W + GUTTER)}
COL_TITLE = {"dependents": "Dependents", "changed": "Changed", "dependencies": "Dependencies"}

FILL = {
    "added": "var(--success, #22C55E)",
    "modified": "var(--accent-2, #E474E4)",
    "deleted": "var(--error, #EF476F)",
    "renamed": "var(--accent-3, #4C6CBC)",
}
NEUTRAL_FILL = "var(--surface-2, #142042)"
BORDER = "var(--border, #26324F)"
TEXT = "var(--text-primary, #EAF1FF)"
MUTED = "var(--text-tertiary, #7F8BB0)"
EDGE = "var(--text-tertiary, #7F8BB0)"
FONT = 'ui-monospace, "SF Mono", Menlo, monospace'


def budget(box_w: int, reserve: int = 0) -> int:
    """Largest label length L with (L + reserve) * ADV + 2 * PAD <= box_w."""
    return math.floor((box_w - 2 * PAD) / ADV) - reserve


SIDE_BUDGET = budget(SIDE_BOX_W)                       # 37
CENTRE_BUDGET = budget(CENTRE_BOX_W, BADGE_RESERVE)    # 30
BUDGET = {"dependents": SIDE_BUDGET, "changed": CENTRE_BUDGET, "dependencies": SIDE_BUDGET}


def shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return "…" + text[-(limit - 1):]


def text_len(s: str) -> float:
    return len(s) * ADV


# --- projection -------------------------------------------------------------

@dataclass
class PNode:
    id: str
    path: str                 # full path; first member path for collapsed nodes
    label: str                # path, "<group> (N files)", or "+N more"
    group: object             # str, or None for the overflow node
    status: str               # added|modified|deleted|renamed|unchanged|collapsed|more
    members: list = field(default_factory=list)   # sorted member paths, else []
    test_count: int = 0
    edges_to_changed: int = 0


@dataclass
class PGroup:
    name: object              # str, or None for the overflow group
    nodes: list


@dataclass
class PEdge:
    src: str                  # node id
    dst: str                  # node id
    column: str               # side column of the non-centre end; "changed" for centre-to-centre
    granularity: str


@dataclass
class Projected:
    columns: dict             # column -> list[PGroup]
    edges: list               # list[PEdge]
    column_status: dict       # dependents/dependencies -> status string
    package_granularity: dict # column -> bool
    skipped: list
    snapshot_tree: str
    base_tree: str

    def nodes(self, column: str) -> list:
        return [n for g in self.columns[column] for n in g.nodes]


def node_id(path: str) -> str:
    return "n-" + digest(path)


def _validate(desc: object) -> None:
    if not isinstance(desc, dict):
        raise ValueError("diagram description is not a JSON object")
    for key in ("nodes", "edges"):
        if not isinstance(desc.get(key), list):
            raise ValueError(f"diagram description has no {key!r} list")
    for n in desc["nodes"]:
        if not isinstance(n, dict) or not isinstance(n.get("path"), str):
            raise ValueError("diagram node without a path")
    for e in desc["edges"]:
        if not isinstance(e, dict) or not isinstance(e.get("from"), str) \
                or not isinstance(e.get("to"), str):
            raise ValueError("diagram edge without from and to")
    status = desc.get("column_status")
    if status is not None and not isinstance(status, dict):
        raise ValueError("column_status is not an object")


def _group_nodes(nodes: list) -> list:
    """Order nodes into groups by name, nodes by path; ``None`` group last."""
    named: dict = {}
    for n in nodes:
        named.setdefault(n.group, []).append(n)
    groups = []
    for name in sorted(k for k in named if k is not None):
        groups.append(PGroup(name, sorted(named[name], key=lambda n: n.path)))
    if None in named:
        groups.append(PGroup(None, sorted(named[None], key=lambda n: n.path)))
    return groups


def project(desc: dict) -> Projected:
    _validate(desc)
    raw_nodes = {}
    for n in desc["nodes"]:
        raw_nodes.setdefault(n["path"], n)
    status_of = {p: (n.get("status") or "unchanged") for p, n in raw_nodes.items()}
    changed = {p for p, s in status_of.items() if s in CHANGED_STATUSES}
    is_test = {p: bool(n.get("is_test")) for p, n in raw_nodes.items()}
    group_of = {p: str(n.get("group") or "") for p, n in raw_nodes.items()}

    # Edges between known nodes, deduplicated by (from, to), first wins.
    edges = {}
    for e in desc["edges"]:
        key = (e["from"], e["to"])
        if key in edges or key[0] not in raw_nodes or key[1] not in raw_nodes:
            continue
        if key[0] not in changed and key[1] not in changed:
            continue
        if key[0] == key[1]:
            continue
        edges[key] = str(e.get("granularity") or "file")

    # Column assignment.
    # A node with edges in both directions is a dependent.
    column_of = {p: "changed" for p in changed}
    for (a, b) in edges:
        if a not in changed:
            column_of[a] = "dependents"
        if b not in changed and column_of.get(b) != "dependents":
            column_of[b] = "dependencies"

    # 1. Test exclusion; counts include changed test files.
    test_count = {p: 0 for p in changed}
    for (a, b) in edges:
        if b in changed and is_test.get(a):
            test_count[b] += 1
    side_members = {
        col: [p for p, c in column_of.items() if c == col and not is_test[p]]
        for col in SIDE_COLUMNS
    }
    column_status = {}
    raw_status = desc.get("column_status") or {}
    for col in SIDE_COLUMNS:
        column_status[col] = str(raw_status.get(col) or "complete")
        if column_status[col].startswith("failed"):
            side_members[col] = []
    kept_paths = set(changed)
    for col in SIDE_COLUMNS:
        kept_paths.update(side_members[col])
    edges = {k: g for k, g in edges.items() if k[0] in kept_paths and k[1] in kept_paths}

    # Per path: the number of edges to a changed node, and whether every
    # such edge is package-granular (vacuously true with none).
    edge_count: dict = {}
    all_package: dict = {}
    for (a, b), g in edges.items():
        for p, other in ((a, b), (b, a)):
            if other in changed:
                edge_count[p] = edge_count.get(p, 0) + 1
                all_package[p] = all_package.get(p, True) and g == "package"

    # Node objects; ``owner`` maps a path to the node that represents it.
    owner = {}
    columns = {}
    for p in sorted(changed):
        node = PNode(node_id(p), p, p, group_of[p], status_of[p], [],
                     test_count[p], edge_count.get(p, 0))
        owner[p] = node
    columns["changed"] = _group_nodes([owner[p] for p in changed])

    for col in SIDE_COLUMNS:
        nodes = []
        # 2. Expansion collapse per group.
        by_group: dict = {}
        for p in side_members[col]:
            by_group.setdefault(group_of[p], []).append(p)
        for group, members in by_group.items():
            collapsible = sorted(p for p in members if all_package.get(p, True))
            collapsed = set(collapsible)
            singles = [p for p in members if p not in collapsed]
            if len(collapsible) > COLLAPSE_ABOVE:
                node = PNode(node_id("\n".join(collapsible)), collapsible[0],
                             f"{group} ({len(collapsible)} files)", group, "collapsed",
                             collapsible, 0, sum(edge_count.get(p, 0) for p in collapsible))
                for p in collapsible:
                    owner[p] = node
                nodes.append(node)
            else:
                singles += collapsible
            for p in singles:
                node = PNode(node_id(p), p, p, group, "unchanged", [], 0, edge_count.get(p, 0))
                owner[p] = node
                nodes.append(node)
        # 3. Cap.
        if len(nodes) > CAP:
            nodes.sort(key=lambda n: (-n.edges_to_changed, n.path))
            overflow = nodes[CAP:]
            nodes = nodes[:CAP]
            members = sorted(p for n in overflow for p in (n.members or [n.path]))
            more = PNode(node_id("\n".join(members)), members[0], f"+{len(members)} more",
                         None, "more", members, 0, sum(n.edges_to_changed for n in overflow))
            for p in members:
                owner[p] = more
            nodes.append(more)
        columns[col] = _group_nodes(nodes)

    # Projected edges between owning nodes, deduplicated.
    p_edges = []
    seen = set()
    for (a, b), gran in sorted(edges.items()):
        src, dst = owner[a], owner[b]
        if a in changed and b in changed:
            col = "changed"
        elif a in changed:
            col = column_of[b]
        else:
            col = column_of[a]
        key = (src.id, dst.id)
        if key in seen:
            continue
        seen.add(key)
        p_edges.append(PEdge(src.id, dst.id, col, gran))

    package_granularity = {
        col: any(e.column == col and e.granularity == "package" for e in p_edges)
        for col in COLUMNS
    }
    skipped = desc.get("skipped") if isinstance(desc.get("skipped"), list) else []
    return Projected(
        columns=columns,
        edges=p_edges,
        column_status=column_status,
        package_granularity=package_granularity,
        skipped=skipped,
        snapshot_tree=str(desc.get("snapshot_tree") or ""),
        base_tree=str(desc.get("base_tree") or ""),
    )


# --- layout -----------------------------------------------------------------

@dataclass
class Box:
    id: str
    column: str
    x: float
    y: float
    w: float
    h: float
    label: str
    text_len: float
    badge: object            # "⚑N" or None
    badge_len: float
    node: PNode


@dataclass
class Frame:
    column: str
    x: float
    y: float
    w: float
    h: float
    label: str
    text_len: float


@dataclass
class EdgePath:
    src: str
    dst: str
    column: str
    d: str


@dataclass
class Header:
    column: str
    title: str
    notes: list             # lines under the title
    reason: list            # lines drawn where nodes would be (failed or empty column)


@dataclass
class Layout:
    boxes: dict             # node id -> Box
    frames: list            # list[Frame]
    edges: list             # list[EdgePath]
    headers: list           # list[Header]
    width: int
    height: int
    content_top: int        # y where the column contents start, below the header notes


def _wrap(text: str, limit: int) -> list:
    return textwrap.wrap(text, limit, break_long_words=True) or [""]


def layout(p: Projected) -> Layout:
    headers = []
    for col in COLUMNS:
        notes = []
        status = p.column_status.get(col, "complete")
        if col != "changed" and status.startswith("partial"):
            notes += _wrap(status, SIDE_BUDGET)
        if p.package_granularity.get(col):
            notes.append("edges at package granularity")
        reason = []
        if col != "changed" and status.startswith("failed"):
            reason = _wrap(status, SIDE_BUDGET)
        elif not p.columns[col]:
            reason = ["none found"]
        headers.append(Header(col, COL_TITLE[col], notes, reason))
    content_top = NOTES_Y + LINE_H * max(len(h.notes) for h in headers)

    boxes = {}
    frames = []
    bottom = content_top
    for col in COLUMNS:
        x = COL_X[col]
        y = content_top
        box_w = CENTRE_BOX_W if col == "changed" else SIDE_BOX_W
        limit = BUDGET[col]
        header = next(h for h in headers if h.column == col)
        if header.reason:
            y += LINE_H * len(header.reason)
        for gi, group in enumerate(p.columns[col]):
            if gi:
                y += GROUP_GAP
            n = len(group.nodes)
            if group.name is not None:
                label = shorten(group.name, limit)
                h = GROUP_PAD + GROUP_HEADER + n * BOX_H + (n - 1) * ROW_GAP + GROUP_PAD
                frames.append(Frame(col, x, y, COL_W, h, label, text_len(label)))
                node_y = y + GROUP_PAD + GROUP_HEADER
            else:
                h = n * BOX_H + (n - 1) * ROW_GAP
                node_y = y
            for node in group.nodes:
                label = shorten(node.label, limit)
                badge = f"⚑{node.test_count}" if node.test_count > 0 else None
                boxes[node.id] = Box(node.id, col, x + GROUP_PAD, node_y, box_w, BOX_H, label,
                                     text_len(label), badge, text_len(badge) if badge else 0.0,
                                     node)
                node_y += BOX_H + ROW_GAP
            y += h
        bottom = max(bottom, y)
    height = int(bottom + BOTTOM_PAD)

    edges = []
    lane_x0 = COL_X["changed"] + GROUP_PAD + CENTRE_BOX_W
    centre_index = 0
    for e in p.edges:
        src, dst = boxes.get(e.src), boxes.get(e.dst)
        if src is None or dst is None:
            continue
        sy, dy = src.y + src.h / 2, dst.y + dst.h / 2
        if e.column == "changed":
            track = lane_x0 + TRACK_GAP * (centre_index % 3 + 1)
            centre_index += 1
            x = src.x + src.w
            d = f"M {_n(x)} {_n(sy)} L {_n(track)} {_n(sy)} L {_n(track)} {_n(dy)} L {_n(x)} {_n(dy)}"
        else:
            left = min(COL_X[src.column], COL_X[dst.column])
            mid = left + COL_W + GUTTER / 2
            if dst.x > src.x:
                x1, x2 = src.x + src.w, dst.x
            else:
                x1, x2 = src.x, dst.x + dst.w
            d = f"M {_n(x1)} {_n(sy)} C {_n(mid)} {_n(sy)} {_n(mid)} {_n(dy)} {_n(x2)} {_n(dy)}"
        edges.append(EdgePath(e.src, e.dst, e.column, d))
    return Layout(boxes, frames, edges, headers, CONTENT_W, height, content_top)


def _n(v: float) -> str:
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


# --- SVG and section --------------------------------------------------------

def _text(x: float, y: float, s: str, fill: str, anchor: str = "start", cls: str = "") -> str:
    klass = f' class="{cls}"' if cls else ""
    return (f'<text{klass} x="{_n(x)}" y="{_n(y)}" textLength="{_n(text_len(s))}" '
            f'lengthAdjust="spacingAndGlyphs" dominant-baseline="middle" '
            f'text-anchor="{anchor}" fill="{fill}">{escape(s)}</text>')


def render_svg(p: Projected, lay: Layout) -> str:
    out = [
        f'<svg class="blast" xmlns="http://www.w3.org/2000/svg" width="{lay.width}" '
        f'height="{lay.height}" viewBox="0 0 {lay.width} {lay.height}" '
        f"font-family='{FONT}' font-size=\"12\">",
        '<defs><marker id="blast-arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{EDGE}"/></marker></defs>',
    ]
    out.append('<g class="headers">')
    for h in lay.headers:
        x = COL_X[h.column] + PAD
        out.append(_text(x, TITLE_Y, h.title, TEXT, cls="col-title"))
        for i, note in enumerate(h.notes):
            out.append(_text(x, NOTES_Y + LINE_H * i, note, MUTED, cls="col-note"))
        for i, line in enumerate(h.reason):
            out.append(_text(x, lay.content_top + LINE_H * i + LINE_H / 2, line, MUTED, cls="col-reason"))
    out.append("</g>")

    out.append('<g class="frames">')
    for f in lay.frames:
        out.append(
            f'<g class="group"><rect x="{_n(f.x)}" y="{_n(f.y)}" width="{_n(f.w)}" '
            f'height="{_n(f.h)}" rx="8" fill="none" stroke="{BORDER}"/>'
            + _text(f.x + PAD, f.y + GROUP_PAD + GROUP_HEADER / 2, f.label, MUTED, cls="group-label")
            + "</g>"
        )
    out.append("</g>")

    out.append('<g class="edges">')
    for e in lay.edges:
        out.append(
            f'<path class="edge e-{e.src} e-{e.dst}" data-from="{e.src}" data-to="{e.dst}" '
            f'd="{e.d}" fill="none" stroke="{EDGE}" stroke-width="1.2" '
            'marker-end="url(#blast-arrow)"/>'
        )
    out.append("</g>")

    out.append('<g class="nodes">')
    for box in lay.boxes.values():
        node = box.node
        changed = node.status in CHANGED_STATUSES
        if changed:
            colour = FILL[node.status]
            rect = (f'<rect x="{_n(box.x)}" y="{_n(box.y)}" width="{_n(box.w)}" height="{_n(box.h)}" '
                    f'rx="6" fill="{colour}" fill-opacity="0.18" stroke="{colour}"/>')
        else:
            dashed = ' stroke-dasharray="5 3"' if node.status in ("collapsed", "more") else ""
            rect = (f'<rect x="{_n(box.x)}" y="{_n(box.y)}" width="{_n(box.w)}" height="{_n(box.h)}" '
                    f'rx="6" fill="{NEUTRAL_FILL}" stroke="{BORDER}"{dashed}/>')
        title = node.path if not node.members else "\n".join(node.members)
        parts = [f'<g id="{box.id}"><title>{escape(title)}</title>', rect,
                 _text(box.x + PAD, box.y + box.h / 2, box.label, TEXT, cls="label")]
        if box.badge:
            parts.append(_text(box.x + box.w - PAD, box.y + box.h / 2, box.badge, TEXT,
                               anchor="end", cls="badge"))
        parts.append("</g>")
        g = "".join(parts)
        if changed:
            g = f'<a href="#{file_anchor(node.path)}">{g}</a>'
        out.append(g)
    out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)


def _hover_style(lay: Layout) -> str:
    rules = []
    for nid in lay.boxes:
        rules.append(f".blast:has(#{nid}:hover) .edge:not(.e-{nid}){{opacity:.15}}")
        rules.append(f".blast:has(#{nid}:hover) .edge.e-{nid}{{stroke-width:2}}")
    return "<style>\n" + "\n".join(rules) + "\n</style>"


def _legend() -> str:
    keys = [("added", "added"), ("modified", "modified"), ("deleted", "deleted"),
            ("renamed", "renamed"), ("unchanged", "unchanged"),
            ("collapsed", "collapsed package group or +N more")]
    spans = "".join(
        f'<span class="blast-key"><span class="blast-swatch blast-swatch-{k}"></span>{label}</span>'
        for k, label in keys
    )
    spans += '<span class="blast-key">⚑N test files with an edge to the node</span>'
    return f'<div class="blast-legend">{spans}</div>'


def render_diagram(desc: dict, warnings: Warnings) -> str:
    try:
        p = project(desc)
    except ValueError as exc:
        warnings.add(f"diagram description invalid: {exc}")
        return ""
    lay = layout(p)
    collapsed = [n for col in COLUMNS for n in p.nodes(col) if n.members]
    members_html = ""
    if collapsed:
        items = "".join(
            f"<li><code>{escape(n.label)}</code>: "
            + ", ".join(f"<code>{escape(m)}</code>" for m in n.members) + "</li>"
            for n in collapsed
        )
        members_html = f'<h3>Collapsed nodes</h3>\n<ul class="blast-members">{items}</ul>'
    skipped_html = ""
    if p.skipped:
        items = "".join(
            f'<li><code>{escape(s.get("path"))}</code> — {escape(s.get("reason"))}</li>'
            for s in p.skipped if isinstance(s, dict)
        )
        skipped_html = f'<h3>Skipped files</h3>\n<ul class="blast-skipped">{items}</ul>'
    return f"""<section id="diagram">
    <h2>Blast radius</h2>
    <p class="muted">Files that import a changed file on the left, changed files in the centre, files a changed file imports on the right. Snapshot <code>{escape(p.snapshot_tree)}</code> against base <code>{escape(p.base_tree)}</code>.</p>
    {_hover_style(lay)}
    <div class="blast-scroll">{render_svg(p, lay)}</div>
    {_legend()}
    {members_html}
    {skipped_html}
    </section>"""
