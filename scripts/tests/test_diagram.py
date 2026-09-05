"""Tests for review_html.diagram: projection, layout, and section rendering."""
from __future__ import annotations

import contextlib
import io
import json
import random
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from review_html import render
from review_html.common import digest, file_anchor
from review_html.diagram import (
    ADV,
    BOX_H,
    CAP,
    CENTRE_BOX_W,
    CENTRE_BUDGET,
    COL_W,
    CONTENT_W,
    GROUP_GAP,
    GROUP_HEADER,
    GROUP_PAD,
    GUTTER,
    LANE,
    PAD,
    ROW_GAP,
    SIDE_BOX_W,
    SIDE_BUDGET,
    Projected,
    budget,
    layout,
    project,
    render_diagram,
    shorten,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def desc(nodes, edges, column_status=None, **extra):
    """Build a diagram description from compact tuples.

    ``nodes`` are ``(path, status, group, is_test)``; ``edges`` are
    ``(from, to, granularity)`` with method ``import`` for file edges and
    ``expansion`` for package edges.
    """
    d = {
        "snapshot_tree": "abc1234",
        "base_tree": "def5678",
        "nodes": [
            {"path": p, "status": s, "group": g, "is_test": t, "old_path": None}
            for p, s, g, t in nodes
        ],
        "edges": [
            {"from": a, "to": b, "granularity": gran,
             "method": "expansion" if gran == "package" else "import",
             "tree": "snapshot"}
            for a, b, gran in edges
        ],
        "column_status": column_status or {"dependents": "complete", "dependencies": "complete"},
        "skipped": [],
    }
    d.update(extra)
    return d


def paths(p: Projected, column: str) -> list:
    return [n.path for n in p.nodes(column)]


def labels(p: Projected, column: str) -> list:
    return [n.label for n in p.nodes(column)]


class ColumnAssignmentTest(unittest.TestCase):
    def test_changed_nodes_go_to_centre(self) -> None:
        p = project(desc(
            [("a.py", "modified", "pkg", False), ("b.py", "added", "pkg", False),
             ("c.py", "deleted", "pkg", False), ("d.py", "renamed", "pkg", False)],
            [],
        ))
        self.assertEqual(paths(p, "changed"), ["a.py", "b.py", "c.py", "d.py"])
        self.assertEqual(paths(p, "dependents"), [])
        self.assertEqual(paths(p, "dependencies"), [])

    def test_unchanged_with_edge_into_changed_is_dependent(self) -> None:
        p = project(desc(
            [("a.py", "modified", "pkg", False), ("u.py", "unchanged", "pkg", False)],
            [("u.py", "a.py", "file")],
        ))
        self.assertEqual(paths(p, "dependents"), ["u.py"])
        self.assertEqual(paths(p, "dependencies"), [])
        self.assertEqual(len(p.edges), 1)
        self.assertEqual((p.edges[0].src, p.edges[0].dst, p.edges[0].column),
                         ("n-" + digest("u.py"), "n-" + digest("a.py"), "dependents"))

    def test_unchanged_with_edge_from_changed_is_dependency(self) -> None:
        p = project(desc(
            [("a.py", "modified", "pkg", False), ("u.py", "unchanged", "pkg", False)],
            [("a.py", "u.py", "file")],
        ))
        self.assertEqual(paths(p, "dependencies"), ["u.py"])
        self.assertEqual(paths(p, "dependents"), [])
        self.assertEqual(p.edges[0].column, "dependencies")

    def test_both_goes_to_dependents_with_both_edges(self) -> None:
        p = project(desc(
            [("a.py", "modified", "pkg", False), ("u.py", "unchanged", "pkg", False)],
            [("u.py", "a.py", "file"), ("a.py", "u.py", "file")],
        ))
        self.assertEqual(paths(p, "dependents"), ["u.py"])
        self.assertEqual(paths(p, "dependencies"), [])
        self.assertEqual(sorted((e.src, e.dst, e.column) for e in p.edges), sorted([
            ("n-" + digest("u.py"), "n-" + digest("a.py"), "dependents"),
            ("n-" + digest("a.py"), "n-" + digest("u.py"), "dependents"),
        ]))

    def test_centre_to_centre_edges_are_kept(self) -> None:
        p = project(desc(
            [("a.py", "modified", "pkg", False), ("b.py", "added", "pkg", False)],
            [("a.py", "b.py", "file")],
        ))
        self.assertEqual(len(p.edges), 1)
        self.assertEqual(p.edges[0].column, "changed")

    def test_unchanged_only_edges_and_orphans_are_dropped(self) -> None:
        p = project(desc(
            [("a.py", "modified", "pkg", False), ("u.py", "unchanged", "pkg", False),
             ("v.py", "unchanged", "pkg", False), ("w.py", "unchanged", "pkg", False)],
            [("u.py", "v.py", "file"), ("v.py", "a.py", "file")],
        ))
        self.assertEqual(paths(p, "dependents"), ["v.py"])
        self.assertEqual(len(p.edges), 1)

    def test_node_ids_share_the_anchor_digest(self) -> None:
        p = project(desc([("src/a.py", "modified", "src", False)], []))
        self.assertEqual(p.nodes("changed")[0].id, "n-" + digest("src/a.py"))

    def test_trees_and_skipped_pass_through(self) -> None:
        p = project(desc([("a.py", "modified", "pkg", False)], [],
                         skipped=[{"path": "big.go", "reason": "blob over 1 MB"}]))
        self.assertEqual(p.snapshot_tree, "abc1234")
        self.assertEqual(p.base_tree, "def5678")
        self.assertEqual(p.skipped, [{"path": "big.go", "reason": "blob over 1 MB"}])


class TestExclusionTest(unittest.TestCase):
    def test_test_files_leave_side_columns(self) -> None:
        p = project(desc(
            [("a.py", "modified", "pkg", False),
             ("test_a.py", "unchanged", "tests", True),
             ("u.py", "unchanged", "pkg", False)],
            [("test_a.py", "a.py", "file"), ("u.py", "a.py", "file"), ("a.py", "test_a.py", "file")],
        ))
        self.assertEqual(paths(p, "dependents"), ["u.py"])
        self.assertEqual(paths(p, "dependencies"), [])
        self.assertEqual(len(p.edges), 1)

    def test_counts_include_changed_test_files(self) -> None:
        p = project(desc(
            [("a.py", "modified", "pkg", False),
             ("test_a.py", "unchanged", "tests", True),
             ("test_b.py", "added", "tests", True),
             ("u.py", "unchanged", "pkg", False)],
            [("test_a.py", "a.py", "file"), ("test_b.py", "a.py", "file"), ("u.py", "a.py", "file"),
             ("a.py", "test_b.py", "file")],
        ))
        by_path = {n.path: n for n in p.nodes("changed")}
        self.assertEqual(by_path["a.py"].test_count, 2)
        self.assertEqual(by_path["test_b.py"].test_count, 0)
        self.assertEqual(paths(p, "changed"), ["a.py", "test_b.py"])

    def test_changed_test_file_stays_a_changed_node(self) -> None:
        p = project(desc([("test_a.py", "modified", "tests", True)], []))
        self.assertEqual(paths(p, "changed"), ["test_a.py"])


def package_group(n: int, prefix: str = "pkg", target: str = "a.go"):
    nodes = [(f"{prefix}/f{i}.go", "unchanged", prefix, False) for i in range(n)]
    edges = [(f"{prefix}/f{i}.go", target, "package") for i in range(n)]
    return nodes, edges


class ExpansionCollapseTest(unittest.TestCase):
    def test_more_than_three_package_nodes_collapse(self) -> None:
        nodes, edges = package_group(4)
        p = project(desc([("a.go", "modified", "root", False)] + nodes, edges))
        col = p.nodes("dependents")
        self.assertEqual(len(col), 1)
        node = col[0]
        self.assertEqual(node.label, "pkg (4 files)")
        self.assertEqual(node.status, "collapsed")
        members = sorted(f"pkg/f{i}.go" for i in range(4))
        self.assertEqual(node.members, members)
        self.assertEqual(node.id, "n-" + digest("\n".join(members)))
        self.assertEqual(node.path, members[0])
        self.assertEqual(node.edges_to_changed, 4)
        self.assertEqual(len(p.edges), 1)
        self.assertEqual(p.edges[0].src, node.id)
        self.assertEqual(p.edges[0].granularity, "package")

    def test_three_package_nodes_do_not_collapse(self) -> None:
        nodes, edges = package_group(3)
        p = project(desc([("a.go", "modified", "root", False)] + nodes, edges))
        self.assertEqual(len(p.nodes("dependents")), 3)

    def test_nodes_with_a_file_granular_edge_stay(self) -> None:
        nodes, edges = package_group(5)
        edges.append(("pkg/f0.go", "b.go", "file"))
        p = project(desc(
            [("a.go", "modified", "root", False), ("b.go", "added", "root", False)] + nodes, edges))
        col = p.nodes("dependents")
        # Nodes order by path; the collapsed node sorts by its first member.
        self.assertEqual([n.label for n in col], ["pkg/f0.go", "pkg (4 files)"])
        self.assertEqual(col[1].members, [f"pkg/f{i}.go" for i in range(1, 5)])

    def test_collapse_is_per_group_and_per_column(self) -> None:
        n1, e1 = package_group(4, "one")
        n2, e2 = package_group(2, "two")
        n3, e3 = package_group(4, "three")
        e3 = [(b, a, g) for a, b, g in e3]  # dependencies
        p = project(desc([("a.go", "modified", "root", False)] + n1 + n2 + n3, e1 + e2 + e3))
        self.assertEqual(labels(p, "dependents"), ["one (4 files)", "two/f0.go", "two/f1.go"])
        self.assertEqual(labels(p, "dependencies"), ["three (4 files)"])

    def test_collapsed_rank_key_sums_member_edges(self) -> None:
        nodes, edges = package_group(4)
        edges += [(f"pkg/f{i}.go", "b.go", "package") for i in range(2)]
        p = project(desc(
            [("a.go", "modified", "root", False), ("b.go", "added", "root", False)] + nodes, edges))
        node = p.nodes("dependents")[0]
        self.assertEqual(node.edges_to_changed, 6)
        self.assertEqual(len(p.edges), 2)

    def test_test_exclusion_precedes_collapse(self) -> None:
        nodes, edges = package_group(4)
        nodes[0] = ("pkg/f0.go", "unchanged", "pkg", True)
        p = project(desc([("a.go", "modified", "root", False)] + nodes, edges))
        self.assertEqual(len(p.nodes("dependents")), 3)
        self.assertEqual(p.nodes("changed")[0].test_count, 1)


class CapTest(unittest.TestCase):
    def test_side_column_over_cap_keeps_ranked_nodes(self) -> None:
        nodes = [("a.go", "modified", "root", False), ("b.go", "added", "root", False)]
        edges = []
        for i in range(20):
            path = f"lib/d{i:02d}.go"
            nodes.append((path, "unchanged", "lib", False))
            edges.append((path, "a.go", "file"))
            if i % 4 == 0:
                edges.append((path, "b.go", "file"))
        p = project(desc(nodes, edges))
        col = p.nodes("dependents")
        self.assertEqual(len(col), CAP + 1)
        kept = [n.path for n in col if n.status != "more"]
        self.assertEqual(len(kept), CAP)
        two_edge = [f"lib/d{i:02d}.go" for i in range(20) if i % 4 == 0]
        for path in two_edge:
            self.assertIn(path, kept)
        one_edge = [f"lib/d{i:02d}.go" for i in range(20) if i % 4 != 0]
        self.assertEqual(sorted(set(kept) - set(two_edge)), one_edge[:CAP - len(two_edge)])
        more = col[-1]
        self.assertEqual(more.status, "more")
        self.assertEqual(more.label, "+5 more")
        self.assertEqual(more.members, one_edge[CAP - len(two_edge):])
        self.assertEqual(more.id, "n-" + digest("\n".join(more.members)))
        self.assertIsNone(more.group)
        self.assertEqual(p.columns["dependents"][-1].name, None)
        self.assertEqual(p.columns["dependents"][-1].nodes, [more])
        self.assertTrue(any(e.src == more.id for e in p.edges))

    def test_exactly_cap_nodes_are_not_capped(self) -> None:
        nodes = [("a.go", "modified", "root", False)]
        edges = []
        for i in range(CAP):
            nodes.append((f"lib/d{i:02d}.go", "unchanged", "lib", False))
            edges.append((f"lib/d{i:02d}.go", "a.go", "file"))
        p = project(desc(nodes, edges))
        self.assertEqual(len(p.nodes("dependents")), CAP)
        self.assertFalse(any(n.status == "more" for n in p.nodes("dependents")))

    def test_collapsed_node_ranks_by_first_member_and_summed_edges(self) -> None:
        nodes = [("a.go", "modified", "root", False)]
        edges = []
        # 16 file-granular dependents with one edge each ...
        for i in range(16):
            nodes.append((f"zzz/d{i:02d}.go", "unchanged", "zzz", False))
            edges.append((f"zzz/d{i:02d}.go", "a.go", "file"))
        # ... plus a package group of 4 collapsing to one node with 4 edges.
        gn, ge = package_group(4, "aaa")
        p = project(desc(nodes + gn, edges + ge))
        col = p.nodes("dependents")
        self.assertEqual(len(col), CAP + 1)
        self.assertEqual(col[0].label, "aaa (4 files)")
        more = col[-1]
        self.assertEqual(more.label, "+2 more")
        self.assertEqual(more.members, ["zzz/d14.go", "zzz/d15.go"])

    def test_more_node_flattens_collapsed_members(self) -> None:
        changed = ["a.go", "b.go", "c.go", "d.go"]
        nodes = [(c, "modified", "root", False) for c in changed]
        edges = []
        for i in range(CAP):
            nodes.append((f"aaa/d{i:02d}.go", "unchanged", "aaa", False))
            for c in changed:
                edges.append((f"aaa/d{i:02d}.go", c, "file"))
            edges.append((f"aaa/d{i:02d}.go", "a.go", "file"))  # duplicate, deduped
        gn, ge = package_group(4, "zzz")
        p = project(desc(nodes + gn, edges + ge))
        more = p.nodes("dependents")[-1]
        self.assertEqual(more.status, "more")
        self.assertEqual(more.label, "+4 more")
        self.assertEqual(more.members, [f"zzz/f{i}.go" for i in range(4)])

    def test_centre_is_never_capped(self) -> None:
        nodes = [(f"src/c{i:02d}.py", "modified", "src", False) for i in range(40)]
        p = project(desc(nodes, []))
        self.assertEqual(len(p.nodes("changed")), 40)


class OrderingTest(unittest.TestCase):
    def test_groups_by_name_and_nodes_by_path(self) -> None:
        p = project(desc(
            [("a.py", "modified", "root", False),
             ("zeta/b.py", "unchanged", "zeta", False), ("zeta/a.py", "unchanged", "zeta", False),
             ("alpha/z.py", "unchanged", "alpha", False), ("alpha/m.py", "unchanged", "alpha", False)],
            [("zeta/b.py", "a.py", "file"), ("zeta/a.py", "a.py", "file"),
             ("alpha/z.py", "a.py", "file"), ("alpha/m.py", "a.py", "file")],
        ))
        groups = p.columns["dependents"]
        self.assertEqual([g.name for g in groups], ["alpha", "zeta"])
        self.assertEqual([n.path for n in groups[0].nodes], ["alpha/m.py", "alpha/z.py"])
        self.assertEqual([n.path for n in groups[1].nodes], ["zeta/a.py", "zeta/b.py"])

    def test_centre_grouped_too(self) -> None:
        p = project(desc(
            [("b/x.py", "modified", "b", False), ("a/y.py", "added", "a", False),
             ("a/x.py", "deleted", "a", False)], []))
        self.assertEqual([g.name for g in p.columns["changed"]], ["a", "b"])
        self.assertEqual(paths(p, "changed"), ["a/x.py", "a/y.py", "b/x.py"])


class ColumnStatusTest(unittest.TestCase):
    def test_partial_keeps_nodes(self) -> None:
        p = project(desc(
            [("a.py", "modified", "pkg", False), ("u.py", "unchanged", "pkg", False)],
            [("u.py", "a.py", "file")],
            {"dependents": "partial: remote scan cap reached", "dependencies": "complete"},
        ))
        self.assertEqual(paths(p, "dependents"), ["u.py"])
        self.assertEqual(p.column_status["dependents"], "partial: remote scan cap reached")

    def test_failed_keeps_no_nodes_or_edges(self) -> None:
        p = project(desc(
            [("a.py", "modified", "pkg", False), ("u.py", "unchanged", "pkg", False),
             ("v.py", "unchanged", "pkg", False)],
            [("u.py", "a.py", "file"), ("a.py", "v.py", "file")],
            {"dependents": "failed: no import patterns for .py", "dependencies": "complete"},
        ))
        self.assertEqual(paths(p, "dependents"), [])
        self.assertEqual(paths(p, "dependencies"), ["v.py"])
        self.assertEqual(len(p.edges), 1)
        self.assertEqual(p.column_status["dependents"], "failed: no import patterns for .py")

    def test_missing_status_defaults_to_complete(self) -> None:
        d = desc([("a.py", "modified", "pkg", False)], [])
        del d["column_status"]
        p = project(d)
        self.assertEqual(p.column_status, {"dependents": "complete", "dependencies": "complete"})


class GranularityNoteTest(unittest.TestCase):
    def test_package_edge_flags_its_column_only(self) -> None:
        p = project(desc(
            [("a.go", "modified", "root", False), ("u.go", "unchanged", "u", False),
             ("v.go", "unchanged", "v", False)],
            [("u.go", "a.go", "package"), ("a.go", "v.go", "file")],
        ))
        self.assertEqual(p.package_granularity,
                         {"dependents": True, "changed": False, "dependencies": False})

    def test_tool_edges_count_by_granularity(self) -> None:
        d = desc([("a.go", "modified", "root", False), ("b.go", "added", "root", False)],
                 [("a.go", "b.go", "package")])
        d["edges"][0]["method"] = "tool:go list"
        p = project(d)
        self.assertTrue(p.package_granularity["changed"])


class InvalidDescriptionTest(unittest.TestCase):
    def test_rejects_non_dict_and_missing_lists(self) -> None:
        for bad in ([], "x", {}, {"nodes": []}, {"edges": []}, {"nodes": "x", "edges": []},
                    {"nodes": [{"status": "added"}], "edges": []},
                    {"nodes": [{"path": "a"}], "edges": [{"from": "a"}]}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    project(bad)


def random_description(rng: random.Random) -> dict:
    """A random one-hop graph whose non-failed side columns are never empty."""
    groups = [f"g{i}" for i in range(rng.randint(1, 5))]
    changed = [f"c{i}.go" for i in range(rng.randint(1, 8))]
    nodes = [(c, rng.choice(["added", "modified", "deleted", "renamed"]),
              rng.choice(groups), rng.random() < 0.2) for c in changed]
    edges = []
    status = {}
    for column, prefix in (("dependents", "in"), ("dependencies", "out")):
        status[column] = rng.choice(["complete", "complete", "partial: cap", "failed: no patterns"])
        count = rng.randint(0, 40)
        column_nodes = []
        for i in range(count):
            path = f"{prefix}/{rng.choice(groups)}/f{i:02d}.go"
            is_test = rng.random() < 0.25
            column_nodes.append((path, "unchanged", rng.choice(groups), is_test))
        if not status[column].startswith("failed"):
            column_nodes.append((f"{prefix}/anchor.go", "unchanged", groups[0], False))
        for path, _, _, _ in column_nodes:
            gran = rng.choice(["file", "package", "package"])
            targets = rng.sample(changed, rng.randint(1, len(changed)))
            for t in targets:
                if column == "dependents":
                    edges.append((path, t, gran))
                else:
                    edges.append((t, path, gran))
        nodes += column_nodes
    # A few centre-to-centre edges and some noise edges among unchanged nodes.
    for _ in range(rng.randint(0, 4)):
        a, b = rng.choice(changed), rng.choice(changed)
        if a != b:
            edges.append((a, b, rng.choice(["file", "package"])))
    rng.shuffle(nodes)
    rng.shuffle(edges)
    return desc(nodes, edges, status)


class ProjectPropertyTest(unittest.TestCase):
    def test_properties_over_random_descriptions(self) -> None:
        rng = random.Random(20260904)
        for case in range(200):
            d = random_description(rng)
            with self.subTest(case=case):
                first = project(d)
                second = project(d)
                self.assertEqual(first, second)
                for column in ("dependents", "dependencies"):
                    nodes = first.nodes(column)
                    self.assertLessEqual(len(nodes), CAP + 1)
                    self.assertLessEqual(len([n for n in nodes if n.status != "more"]), CAP)
                    if not first.column_status[column].startswith("failed"):
                        self.assertTrue(nodes, column)
                    else:
                        self.assertEqual(nodes, [])
                    for n in nodes:
                        self.assertEqual(n.test_count, 0)
                self.assertEqual(len(first.nodes("changed")),
                                 sum(1 for n in d["nodes"] if n["status"] != "unchanged"))
                ids = {n.id for c in first.columns for n in first.nodes(c)}
                for e in first.edges:
                    self.assertIn(e.src, ids)
                    self.assertIn(e.dst, ids)


# --- layout ---------------------------------------------------------------

def numbers(d: str) -> list:
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", d)]


def points(d: str) -> list:
    nums = numbers(d)
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]


class LayoutConstantsTest(unittest.TestCase):
    def test_constants_match_the_design(self) -> None:
        self.assertEqual(ADV, 7.2)
        self.assertEqual(PAD, 10)
        self.assertEqual(BOX_H, 26)
        self.assertEqual(ROW_GAP, 8)
        self.assertEqual(GROUP_PAD, 8)
        self.assertEqual(GROUP_HEADER, 18)
        self.assertEqual(GROUP_GAP, 14)
        self.assertEqual(GUTTER, 56)
        self.assertEqual(LANE, 24)
        self.assertEqual(CONTENT_W, 1036)
        self.assertEqual(COL_W, 308)
        self.assertEqual(COL_W, (CONTENT_W - 2 * GUTTER) // 3)
        self.assertEqual(SIDE_BOX_W, 292)
        self.assertEqual(SIDE_BOX_W, COL_W - 2 * GROUP_PAD)
        self.assertEqual(CENTRE_BOX_W, 268)
        self.assertEqual(CENTRE_BOX_W, SIDE_BOX_W - LANE)

    def test_budgets_compute_to_37_and_30(self) -> None:
        self.assertEqual(budget(SIDE_BOX_W), 37)
        self.assertEqual(budget(CENTRE_BOX_W, reserve=4), 30)
        self.assertEqual(SIDE_BUDGET, 37)
        self.assertEqual(CENTRE_BUDGET, 30)
        self.assertLessEqual(37 * ADV + 2 * PAD, SIDE_BOX_W)
        self.assertGreater(38 * ADV + 2 * PAD, SIDE_BOX_W)
        self.assertLessEqual((30 + 4) * ADV + 2 * PAD, CENTRE_BOX_W)
        self.assertGreater((31 + 4) * ADV + 2 * PAD, CENTRE_BOX_W)

    def test_shorten_keeps_trailing_characters_with_leading_ellipsis(self) -> None:
        self.assertEqual(shorten("short.py", 37), "short.py")
        long = "a/" * 30 + "file.py"
        out = shorten(long, 37)
        self.assertEqual(len(out), 37)
        self.assertTrue(out.startswith("…"))
        self.assertTrue(long.endswith(out[1:]))


class LayoutPropertyTest(unittest.TestCase):
    def test_properties_over_random_projections(self) -> None:
        rng = random.Random(4711)
        col_x = {"dependents": 0, "changed": COL_W + GUTTER, "dependencies": 2 * (COL_W + GUTTER)}
        lane_x0 = col_x["changed"] + GROUP_PAD + CENTRE_BOX_W
        lane_x1 = lane_x0 + LANE
        for case in range(200):
            p = project(random_description(rng))
            with self.subTest(case=case):
                lay = layout(p)
                self.assertEqual(lay, layout(p))
                self.assertEqual(lay.width, CONTENT_W)
                self.assertGreater(lay.height, 0)
                for box in lay.boxes.values():
                    self.assertLessEqual(box.text_len + 2 * PAD, box.w + 1e-6)
                    if box.badge:
                        self.assertLessEqual(box.badge_len + 2 * PAD, box.w + 1e-6)
                        self.assertLessEqual(box.text_len + box.badge_len + 2 * PAD, box.w + 1e-6)
                    expected_w = CENTRE_BOX_W if box.column == "changed" else SIDE_BOX_W
                    self.assertEqual(box.w, expected_w)
                    self.assertEqual(box.h, BOX_H)
                    self.assertEqual(box.x, col_x[box.column] + GROUP_PAD)
                    self.assertLessEqual(box.y + box.h, lay.height)
                for frame in lay.frames:
                    self.assertLessEqual(frame.text_len + 2 * PAD, frame.w + 1e-6)
                    self.assertEqual(frame.w, COL_W)
                    self.assertEqual(frame.x, col_x[frame.column])
                # Boxes in one column never overlap vertically.
                for column in ("dependents", "changed", "dependencies"):
                    ys = sorted((b.y, b.y + b.h) for b in lay.boxes.values() if b.column == column)
                    for (a0, a1), (b0, b1) in zip(ys, ys[1:]):
                        self.assertLessEqual(a1, b0)
                by_id = lay.boxes
                for edge in lay.edges:
                    src, dst = by_id[edge.src], by_id[edge.dst]
                    pts = points(edge.d)
                    start, end = pts[0], pts[-1]
                    if edge.column == "changed":
                        for x, _ in pts:
                            self.assertGreaterEqual(x, lane_x0)
                            self.assertLessEqual(x, lane_x1)
                        self.assertEqual(start, (src.x + src.w, src.y + src.h / 2))
                        self.assertEqual(end, (dst.x + dst.w, dst.y + dst.h / 2))
                    elif dst.x > src.x:
                        self.assertEqual(start, (src.x + src.w, src.y + src.h / 2))
                        self.assertEqual(end, (dst.x, dst.y + dst.h / 2))
                    else:
                        self.assertEqual(start, (src.x, src.y + src.h / 2))
                        self.assertEqual(end, (dst.x + dst.w, dst.y + dst.h / 2))


class LayoutFromProjectedTest(unittest.TestCase):
    """Layout tests that build a Projected directly, without project()."""

    def test_reverse_edge_attaches_on_the_correct_sides(self) -> None:
        from review_html.diagram import PEdge, PGroup, PNode
        dep = PNode("n-dep", "u.py", "u.py", "pkg", "unchanged", [], 0, 2)
        chg = PNode("n-chg", "a.py", "a.py", "pkg", "modified", [], 1, 2)
        p = Projected(
            columns={"dependents": [PGroup("pkg", [dep])], "changed": [PGroup("pkg", [chg])],
                     "dependencies": []},
            edges=[PEdge("n-dep", "n-chg", "dependents", "file"),
                   PEdge("n-chg", "n-dep", "dependents", "file")],
            column_status={"dependents": "complete", "dependencies": "complete"},
            package_granularity={"dependents": False, "changed": False, "dependencies": False},
            skipped=[], snapshot_tree="s", base_tree="b",
        )
        lay = layout(p)
        forward = next(e for e in lay.edges if e.src == "n-dep")
        reverse = next(e for e in lay.edges if e.src == "n-chg")
        d, c = lay.boxes["n-dep"], lay.boxes["n-chg"]
        self.assertEqual(points(forward.d)[0], (d.x + d.w, d.y + d.h / 2))
        self.assertEqual(points(forward.d)[-1], (c.x, c.y + c.h / 2))
        self.assertEqual(points(reverse.d)[0], (c.x, c.y + c.h / 2))
        self.assertEqual(points(reverse.d)[-1], (d.x + d.w, d.y + d.h / 2))
        mid = (COL_W + (COL_W + GUTTER)) / 2
        self.assertEqual(points(forward.d)[1][0], mid)
        self.assertEqual(points(reverse.d)[1][0], mid)
        self.assertEqual(c.badge, "⚑1")

    def test_group_geometry(self) -> None:
        from review_html.diagram import PGroup, PNode
        nodes = [PNode(f"n-{i}", f"p{i}", f"p{i}", "g", "unchanged", [], 0, 1) for i in range(3)]
        p = Projected(
            columns={"dependents": [PGroup("g", nodes)], "changed": [], "dependencies": []},
            edges=[], column_status={"dependents": "complete", "dependencies": "complete"},
            package_granularity={"dependents": False, "changed": False, "dependencies": False},
            skipped=[], snapshot_tree="s", base_tree="b",
        )
        lay = layout(p)
        frame = lay.frames[0]
        boxes = [lay.boxes[f"n-{i}"] for i in range(3)]
        self.assertEqual(boxes[0].y, frame.y + GROUP_PAD + GROUP_HEADER)
        self.assertEqual(boxes[1].y - boxes[0].y, BOX_H + ROW_GAP)
        self.assertEqual(frame.h, GROUP_PAD + GROUP_HEADER + 3 * BOX_H + 2 * ROW_GAP + GROUP_PAD)


# --- rendering ------------------------------------------------------------

def svg_of(html: str) -> ET.Element:
    start = html.index("<svg")
    end = html.index("</svg>") + len("</svg>")
    root = ET.fromstring(html[start:end])
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def render_section(d: dict) -> tuple:
    from review_html.warnings import Warnings
    w = Warnings()
    with contextlib.redirect_stderr(io.StringIO()):
        html = render_diagram(d, w)
    return html, w.items


def sample() -> dict:
    nodes = [
        ("pkg/a.go", "modified", "pkg", False), ("pkg/b.go", "added", "pkg", False),
        ("pkg/gone.go", "deleted", "pkg", False), ("pkg/new.go", "renamed", "pkg", False),
        ("pkg/a_test.go", "unchanged", "pkg", True), ("pkg/b_test.go", "added", "pkg", True),
        ("cmd/main.go", "unchanged", "cmd", False), ("util/u.go", "unchanged", "util", False),
    ]
    edges = [
        ("pkg/a_test.go", "pkg/a.go", "package"), ("pkg/b_test.go", "pkg/a.go", "package"),
        ("cmd/main.go", "pkg/a.go", "package"), ("pkg/a.go", "util/u.go", "file"),
        ("pkg/a.go", "pkg/b.go", "file"), ("pkg/b.go", "pkg/new.go", "file"),
    ]
    gn, ge = package_group(4, "big", "pkg/b.go")
    return desc(nodes + gn, edges + ge,
                skipped=[{"path": "vendor/huge.go", "reason": "blob over 1 MB"}])


class RenderDiagramMarkupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.html, self.warnings = render_section(sample())
        self.svg = svg_of(self.html)

    def test_no_warnings_and_section_shell(self) -> None:
        self.assertEqual(self.warnings, [])
        self.assertIn('<section id="diagram">', self.html)
        self.assertIn("<h2>Blast radius</h2>", self.html)
        self.assertIn('<div class="blast-scroll">', self.html)
        self.assertIn('class="blast-legend"', self.html)
        self.assertIn("abc1234", self.html)
        self.assertIn("def5678", self.html)

    def test_declared_size_and_no_scripts(self) -> None:
        self.assertEqual(self.svg.get("width"), str(CONTENT_W))
        self.assertTrue(int(self.svg.get("height")) > 0)
        self.assertNotIn("<script", self.html)
        self.assertNotIn("http://", self.html.replace("http://www.w3.org/2000/svg", ""))

    def test_node_markup(self) -> None:
        nid = "n-" + digest("pkg/a.go")
        g = self.svg.find(f".//g[@id='{nid}']")
        self.assertIsNotNone(g)
        self.assertEqual(g.find("title").text, "pkg/a.go")
        self.assertIsNotNone(g.find("rect"))
        texts = g.findall("text")
        self.assertEqual(texts[0].text, "pkg/a.go")
        self.assertEqual(texts[1].text, "⚑2")
        for t in texts:
            self.assertIsNotNone(t.get("textLength"))
            self.assertEqual(t.get("lengthAdjust"), "spacingAndGlyphs")
        # Changed nodes are wrapped in a link to the per-file diff anchor.
        a = self.svg.find(f".//a[@href='#{file_anchor('pkg/a.go')}']")
        self.assertIsNotNone(a)
        self.assertIsNotNone(a.find(f"g[@id='{nid}']"))

    def test_badge_only_on_changed_nodes_with_tests(self) -> None:
        for path in ("pkg/b.go", "cmd/main.go", "util/u.go", "pkg/b_test.go"):
            g = self.svg.find(f".//g[@id='n-{digest(path)}']")
            self.assertIsNotNone(g, path)
            self.assertEqual(len(g.findall("text")), 1, path)
        for path in ("cmd/main.go", "util/u.go"):
            self.assertIsNone(self.svg.find(f".//a[@href='#{file_anchor(path)}']"))

    def test_edge_markup(self) -> None:
        src, dst = "n-" + digest("cmd/main.go"), "n-" + digest("pkg/a.go")
        edges = [e for e in self.svg.iter("path") if e.get("class", "").startswith("edge ")]
        self.assertTrue(edges)
        for e in edges:
            self.assertEqual(e.get("class"), f"edge e-{e.get('data-from')} e-{e.get('data-to')}")
            self.assertEqual(e.get("marker-end"), "url(#blast-arrow)")
        self.assertTrue(any(e.get("data-from") == src and e.get("data-to") == dst for e in edges))
        self.assertIsNotNone(self.svg.find(".//marker[@id='blast-arrow']"))

    def test_fills_and_strokes_carry_literal_fallbacks(self) -> None:
        pattern = re.compile(r"^var\(--[a-z0-9-]+, #[0-9A-Fa-f]{6}\)$")
        seen = 0
        for el in self.svg.iter():
            for attr in ("fill", "stroke"):
                value = el.get(attr)
                if value is None or value == "none":
                    continue
                seen += 1
                self.assertRegex(value, pattern)
        self.assertGreater(seen, 10)
        for path, var in (("pkg/b.go", "--success,"), ("pkg/a.go", "--accent-2,"),
                          ("pkg/gone.go", "--error,"), ("pkg/new.go", "--accent-3,"),
                          ("cmd/main.go", "--surface-2,")):
            rect = self.svg.find(f".//g[@id='n-{digest(path)}']/rect")
            self.assertIn(var, rect.get("fill"), path)

    def test_collapsed_node_is_dashed_and_members_listed(self) -> None:
        members = [f"big/f{i}.go" for i in range(4)]
        nid = "n-" + digest("\n".join(members))
        g = self.svg.find(f".//g[@id='{nid}']")
        self.assertIsNotNone(g)
        self.assertIsNotNone(g.find("rect").get("stroke-dasharray"))
        self.assertEqual(g.find("text").text, "big (4 files)")
        self.assertIsNone(self.svg.find(f".//g[@id='n-{digest('pkg/a.go')}']/rect").get("stroke-dasharray"))
        ul = re.search(r'<ul class="blast-members">(.*?)</ul>', self.html, re.DOTALL)
        self.assertIsNotNone(ul)
        positions = [ul.group(1).index(m) for m in members]
        self.assertEqual(positions, sorted(positions))

    def test_skipped_list(self) -> None:
        self.assertIn('<ul class="blast-skipped">', self.html)
        self.assertIn("vendor/huge.go", self.html)
        self.assertIn("blob over 1 MB", self.html)

    def test_hover_rules_per_node_in_style_element(self) -> None:
        style = re.search(r"<style>(.*?)</style>", self.html, re.DOTALL).group(1)
        for g in self.svg.iter("g"):
            nid = g.get("id")
            if nid and nid.startswith("n-"):
                self.assertIn(f".blast:has(#{nid}:hover) .edge:not(.e-{nid}){{opacity:.15}}", style)
                self.assertIn(f".blast:has(#{nid}:hover) .edge.e-{nid}{{stroke-width:2}}", style)

    def test_package_granularity_note_under_header(self) -> None:
        # Dependents (cmd/main.go) and the centre (pkg/b_test.go → pkg/a.go)
        # carry package edges; dependencies has only a file edge.
        texts = [t.text for t in self.svg.iter("text")]
        self.assertEqual(texts.count("edges at package granularity"), 2)

    def test_every_text_declares_textlength_within_its_box(self) -> None:
        for g in self.svg.iter("g"):
            rect = g.find("rect")
            if rect is None:
                continue
            w = float(rect.get("width"))
            for t in g.findall("text"):
                self.assertLessEqual(float(t.get("textLength")) + 2 * PAD, w + 1e-6, t.text)
        for t in self.svg.iter("text"):
            self.assertIsNotNone(t.get("textLength"), t.text)
            self.assertLessEqual(float(t.get("textLength")) + 2 * PAD, COL_W + 1e-6, t.text)

    def test_legend_swatches(self) -> None:
        legend = re.search(r'<div class="blast-legend">(.*?)</div>', self.html, re.DOTALL).group(1)
        for name in ("added", "modified", "deleted", "renamed", "unchanged", "collapsed"):
            self.assertIn(f"blast-swatch-{name}", legend)


class RenderDiagramColumnStatusTest(unittest.TestCase):
    def test_failed_column_shows_reason_in_place(self) -> None:
        d = desc([("a.py", "modified", "pkg", False), ("u.py", "unchanged", "pkg", False)],
                 [("u.py", "a.py", "file")],
                 {"dependents": "failed: no import patterns for .py", "dependencies": "complete"})
        html, _ = render_section(d)
        svg = svg_of(html)
        self.assertIsNone(svg.find(f".//g[@id='n-{digest('u.py')}']"))
        texts = " ".join(t.text or "" for t in svg.iter("text"))
        self.assertIn("no import patterns for .py", texts)

    def test_partial_column_shows_nodes_and_reason(self) -> None:
        d = desc([("a.py", "modified", "pkg", False), ("u.py", "unchanged", "pkg", False)],
                 [("u.py", "a.py", "file")],
                 {"dependents": "partial: remote scan cap reached", "dependencies": "complete"})
        html, _ = render_section(d)
        svg = svg_of(html)
        self.assertIsNotNone(svg.find(f".//g[@id='n-{digest('u.py')}']"))
        texts = " ".join(t.text or "" for t in svg.iter("text"))
        self.assertIn("remote scan cap reached", texts)

    def test_empty_complete_column_says_so(self) -> None:
        html, _ = render_section(desc([("a.py", "modified", "pkg", False)], []))
        texts = [t.text for t in svg_of(html).iter("text")]
        self.assertEqual(texts.count("none found"), 2)


class RenderDiagramEscapingTest(unittest.TestCase):
    def test_special_characters_render_literally(self) -> None:
        nasty = 'src/a<b>&"$x.py'
        d = desc([(nasty, "modified", 'g<&"$', False), ("u<&.py", "unchanged", 'g<&"$', False)],
                 [("u<&.py", nasty, "file")],
                 skipped=[{"path": "s<&\"$.py", "reason": "r<&"}])
        html, warnings = render_section(d)
        self.assertEqual(warnings, [])
        svg = svg_of(html)
        g = svg.find(f".//g[@id='n-{digest(nasty)}']")
        self.assertEqual(g.find("title").text, nasty)
        self.assertEqual(g.find("text").text, nasty)
        self.assertIn("&lt;b&gt;&amp;&quot;$x.py", html)
        self.assertIn('g&lt;&amp;&quot;$', html)
        self.assertIn("s&lt;&amp;&quot;$.py", html)
        self.assertNotIn("<b>", html)

    def test_long_path_is_shortened_with_full_title(self) -> None:
        long = "very/" * 12 + "deep/file.py"
        html, _ = render_section(desc([(long, "added", "very", False)], []))
        g = svg_of(html).find(f".//g[@id='n-{digest(long)}']")
        self.assertEqual(g.find("title").text, long)
        label = g.find("text").text
        self.assertEqual(len(label), CENTRE_BUDGET)
        self.assertTrue(label.startswith("…"))
        self.assertTrue(long.endswith(label[1:]))


class RenderDiagramInvalidTest(unittest.TestCase):
    def test_invalid_description_warns_and_returns_empty(self) -> None:
        for bad in ([], {"nodes": "x"}, {"nodes": [], "edges": [{"from": 1}]}):
            with self.subTest(bad=bad):
                html, warnings = render_section(bad)
                self.assertEqual(html, "")
                self.assertEqual(len(warnings), 1)
                self.assertIn("diagram", warnings[0])


class DiagramDeterminismTest(unittest.TestCase):
    def test_same_description_renders_identical_bytes(self) -> None:
        rng = random.Random(99)
        for _ in range(20):
            d = random_description(rng)
            a, _ = render_section(d)
            b, _ = render_section(json.loads(json.dumps(d)))
            self.assertEqual(a, b)


class RenderWiringTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.stderr = io.StringIO()
        self._redirect = contextlib.redirect_stderr(self.stderr)
        self._redirect.__enter__()

    def tearDown(self) -> None:
        self._redirect.__exit__(None, None, None)
        self._tmp.cleanup()

    def base_data(self) -> dict:
        return {
            "repo": {"name": "x/y", "path": "/tmp/y"},
            "title": "t",
            "unresolved_comments": [{"author": "a", "type": "review", "body": "hi"}],
            "files": [{"path": "pkg/a.go", "badge": "Modified", "stat": "+1 / -1", "diff": "+x\n"}],
        }

    def test_diagram_file_renders_section_and_toc_before_diffs(self) -> None:
        (self.dir / "diagram.json").write_text(json.dumps(sample()), encoding="utf-8")
        data = self.base_data()
        data["diagram_file"] = "diagram.json"
        html = render(data, self.dir)
        self.assertIn('<section id="diagram">', html)
        self.assertIn('<li><a href="#diagram">Blast radius</a></li>', html)
        self.assertLess(html.index('<section id="unresolved-comments">'), html.index('<section id="diagram">'))
        self.assertLess(html.index('<section id="diagram">'), html.index('<section id="diffs">'))
        self.assertEqual(self.stderr.getvalue(), "")
        self.assertIn(".blast-scroll", html)

    def test_missing_diagram_file_warns_and_omits(self) -> None:
        data = self.base_data()
        data["diagram_file"] = "absent.json"
        html = render(data, self.dir)
        self.assertNotIn('id="diagram"', html)
        self.assertNotIn("Blast radius", html)
        self.assertIn("warning:", self.stderr.getvalue())
        self.assertIn("absent.json", self.stderr.getvalue())

    def test_invalid_json_warns_and_omits(self) -> None:
        (self.dir / "diagram.json").write_text("{not json", encoding="utf-8")
        data = self.base_data()
        data["diagram_file"] = "diagram.json"
        html = render(data, self.dir)
        self.assertNotIn('id="diagram"', html)
        self.assertIn("diagram.json", self.stderr.getvalue())

    def test_docs_only_suppresses_without_warning(self) -> None:
        (self.dir / "diagram.json").write_text(json.dumps(sample()), encoding="utf-8")
        data = self.base_data()
        data["diagram_file"] = "diagram.json"
        data["change_classification"] = "docs-only"
        html = render(data, self.dir)
        self.assertNotIn('id="diagram"', html)
        self.assertEqual(self.stderr.getvalue(), "")

    def test_no_diagram_file_is_silent(self) -> None:
        html = render(self.base_data(), self.dir)
        self.assertNotIn('id="diagram"', html)
        self.assertEqual(self.stderr.getvalue(), "")

    def test_entry_point_exits_zero_on_missing_description(self) -> None:
        data = self.base_data()
        data["diagram_file"] = "absent.json"
        (self.dir / "review.json").write_text(json.dumps(data), encoding="utf-8")
        out = self.dir / "review.html"
        result = subprocess.run(
            [sys.executable, "scripts/build_review_html.py",
             "--data", str(self.dir / "review.json"), "--output", str(out)],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("warning:", result.stderr)
        self.assertIn("absent.json", result.stderr)
        self.assertNotIn('id="diagram"', out.read_text(encoding="utf-8"))

    def test_entry_point_exits_two_on_malformed_review_json(self) -> None:
        (self.dir / "review.json").write_text('{"repo": ', encoding="utf-8")
        out = self.dir / "review.html"
        result = subprocess.run(
            [sys.executable, "scripts/build_review_html.py",
             "--data", str(self.dir / "review.json"), "--output", str(out)],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        lines = result.stderr.splitlines()
        self.assertEqual(len(lines), 1, result.stderr)
        self.assertTrue(lines[0].startswith("error: "), lines[0])
        self.assertIn("review.json", lines[0])
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
