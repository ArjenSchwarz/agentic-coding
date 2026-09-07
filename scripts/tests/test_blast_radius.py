"""Tests for scripts/blast_radius.py against a generated git repository.

One repository is built per test class in a temp directory with Go, Python,
TypeScript, Rust, and Swift files; a base commit, a snapshot commit with every
change kind, a docs-only commit on a side branch, and an untracked file. The
script is driven in-process through ``main`` so ``--remote`` can be served by
a fake ``gh_api`` fed from the same repository.
"""
from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import blast_radius

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "blast_radius.py"
ECOSYSTEMS = REPO_ROOT / "scripts" / "ecosystems.json"

BASE_FILES = {
    "go.mod": "module example.com/m\n\ngo 1.21\n",
    "main.go": (
        'package main\n\nimport (\n\t"fmt"\n\n\t"example.com/m/pkg"\n\t"example.com/m/util"\n)\n\n'
        "func main() { fmt.Println(pkg.A(), util.U()) }\n"
    ),
    "pkg/a.go": 'package pkg\n\nimport "example.com/m/util"\n\nfunc A() string { return util.U() }\n',
    "pkg/b.go": 'package pkg\n\nfunc B() string { return "b" }\n',
    "pkg/gone.go": (
        'package pkg\n\nimport "example.com/m/util"\n\n// Gone is the legacy entry point.\n'
        'func Gone() string { return "gone:" + util.U() }\n\n'
        "// GoneTwice repeats Gone.\nfunc GoneTwice() string { return Gone() + Gone() }\n"
    ),
    "pkg/a_test.go": (
        'package pkg_test\n\nimport (\n\t"testing"\n\n\t"example.com/m/pkg"\n)\n\n'
        "func TestA(t *testing.T) { _ = pkg.A() }\n\nfunc TestOld(t *testing.T) {}\n"
    ),
    "util/u.go": 'package util\n\nfunc U() string { return "u" }\n',
    "util/u_test.go": 'package util\n\nimport "testing"\n\nfunc TestU(t *testing.T) { _ = U() }\n',
    "src/app/__init__.py": "",
    "src/app/core.py": (
        "from .helpers import h\nfrom app.models import M\nfrom app.legacy import L\n\n\n"
        "def core():\n    return h(), M, L\n"
    ),
    "src/app/helpers.py": "def h():\n    return 1\n",
    "src/app/models.py": "M = 1\n",
    "src/app/legacy.py": "L = 2\n",
    "src/app/report.py": "from app.models import M\n\n\ndef report():\n    return M\n",
    # Under src/ so the Swift Tests/ directory does not collide with it on
    # case-insensitive filesystems.
    "src/tests/test_core.py": "from app.core import core\n\n\ndef test_one():\n    assert core()\n",
    "web/index.ts": 'export * from "./lib";\n',
    "web/lib/index.ts": 'import { x } from "./x.js";\nexport { x };\n',
    "web/lib/x.ts": "export const x = 1;\n",
    "web/app.ts": 'import { x } from "./lib";\nconsole.log(x);\n',
    "web/lib/x.test.ts": 'import { x } from "./x";\n\nit("does x", () => { expect(x).toBe(1); });\n',
    "src/lib.rs": "mod foo;\nmod bar;\n\nuse crate::bar::baz::Q;\n\npub fn lib() -> i32 { foo::f() + Q }\n",
    "src/foo.rs": "pub fn f() -> i32 { 1 }\n",
    "src/bar/mod.rs": "pub mod baz;\n",
    "src/bar/baz.rs": "pub const Q: i32 = 2;\n",
    "Sources/App/main.swift": "import Foundation\nimport Core\n\nprint(core())\n",
    "Sources/Core/core.swift": 'public func core() -> String { "core" }\n',
    "Tests/CoreTests/CoreTests.swift": (
        "import XCTest\n@testable import Core\n\nfinal class CoreTests: XCTestCase {\n"
        "    func testCore() { XCTAssertEqual(core(), \"core\") }\n}\n"
    ),
    "notes.txt": "notes\n",
    "README.md": "# readme\n",
}

BIG_LINE = "// " + "x" * 97 + "\n"          # 101 bytes
BIG_FILE = "package pkg\n" + BIG_LINE * 10500  # > 1 MiB


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=True,
                            capture_output=True, text=True)
    return result.stdout


def write(repo: Path, rel: str, content: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_repo(repo: Path) -> dict:
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "T")
    git(repo, "config", "core.symlinks", "true")
    for rel, content in BASE_FILES.items():
        write(repo, rel, content)
    os.symlink("pkg/a.go", repo / "link_to_a.go")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    base = git(repo, "rev-parse", "HEAD").strip()

    write(repo, "pkg/a.go", BASE_FILES["pkg/a.go"] + "\n// changed\n")
    write(repo, "pkg/c.go", (
        'package pkg\n\nimport (\n\t"strings"\n\n\t"example.com/m/util"\n)\n\n'
        "// C upper-cases the util value.\nfunc C() string { return strings.ToUpper(util.U()) }\n"
        "\nfunc c2() int { return 2 }\n"))
    (repo / "pkg/gone.go").unlink()
    write(repo, "util/v.go", BASE_FILES["util/u.go"])            # copy of u.go ...
    write(repo, "util/u.go", BASE_FILES["util/u.go"] + "// modified\n")  # ... whose source changed
    git(repo, "mv", "src/app/models.py", "src/app/entities.py")
    write(repo, "src/app/core.py",
          "from .helpers import h\nfrom app.entities import M\n\n\ndef core():\n    return h(), M\n")
    (repo / "src/app/legacy.py").unlink()
    (repo / "notes.txt").unlink()
    os.symlink("README.md", repo / "notes.txt")                # type change
    write(repo, "pkg/big.go", BIG_FILE)
    write(repo, "web/lib/x.ts", "export const x = 2;\n")
    write(repo, "src/foo.rs", "pub fn f() -> i32 { 11 }\n")
    write(repo, "src/bar/baz.rs", "pub const Q: i32 = 22;\n")
    write(repo, "Sources/Core/core.swift", 'public func core() -> String { "core2" }\n')
    write(repo, "Tests/CoreTests/CoreTests.swift",
          BASE_FILES["Tests/CoreTests/CoreTests.swift"].replace(
              "}\n}\n", "}\n    func testNew() {}\n}\n"))
    write(repo, "pkg/a_test.go", BASE_FILES["pkg/a_test.go"].replace("TestOld", "TestNew"))
    write(repo, "src/tests/test_core.py",
          BASE_FILES["src/tests/test_core.py"] + "\n\ndef test_two():\n    assert True\n")
    write(repo, "spec/foo_spec.rb", 'describe "foo" do\n  it "works" do\n  end\nend\n')
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "snapshot")
    snapshot = git(repo, "rev-parse", "HEAD").strip()

    git(repo, "checkout", "-q", "-b", "docs")
    write(repo, "README.md", "# readme\n\nmore\n")
    write(repo, "config.yaml", "key: value\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "docs only")
    docs_only = git(repo, "rev-parse", "HEAD").strip()
    write(repo, "spec/foo_spec.rb", 'describe "foo" do\n  it "works better" do\n  end\nend\n')
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "docs")
    docs = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "checkout", "-q", "main")

    write(repo, "pkg/untracked.go", 'package pkg\n\nimport "example.com/m/util"\n\nfunc N() string { return util.U() }\n')
    return {"base": base, "snapshot": snapshot, "docs": docs, "docs_only": docs_only}


def run(args: list, stderr: io.StringIO = None) -> tuple:
    """Run main() in-process and return (exit code, diagram, diff_tests, stderr)."""
    buf = stderr if stderr is not None else io.StringIO()
    with tempfile.TemporaryDirectory() as out:
        with contextlib.redirect_stderr(buf), contextlib.redirect_stdout(io.StringIO()):
            try:
                code = blast_radius.main(args + ["--out", out])
            except SystemExit as exc:      # argparse errors
                code = exc.code
        diagram = diff_tests = None
        if (Path(out) / "diagram.json").exists():
            diagram = json.loads((Path(out) / "diagram.json").read_text(encoding="utf-8"))
        if (Path(out) / "diff-tests.json").exists():
            diff_tests = json.loads((Path(out) / "diff-tests.json").read_text(encoding="utf-8"))
    return code, diagram, diff_tests, buf.getvalue()


def node_map(diagram: dict) -> dict:
    return {n["path"]: n for n in diagram["nodes"]}


def edge_map(diagram: dict) -> dict:
    return {(e["from"], e["to"]): e for e in diagram["edges"]}


EXPECTED_EDGES = {
    # (from, to): (method, granularity, tree)
    ("main.go", "pkg/a.go"): ("expansion", "package", "snapshot"),
    ("main.go", "pkg/c.go"): ("expansion", "package", "snapshot"),
    ("main.go", "pkg/gone.go"): ("expansion", "package", "base"),
    ("main.go", "util/u.go"): ("expansion", "package", "snapshot"),
    ("main.go", "util/v.go"): ("expansion", "package", "snapshot"),
    ("pkg/a.go", "util/u.go"): ("expansion", "package", "snapshot"),
    ("pkg/c.go", "util/u.go"): ("expansion", "package", "snapshot"),
    ("pkg/c.go", "util/v.go"): ("expansion", "package", "snapshot"),
    ("pkg/gone.go", "util/u.go"): ("expansion", "package", "base"),
    ("pkg/a_test.go", "pkg/a.go"): ("expansion", "package", "snapshot"),
    ("pkg/a_test.go", "pkg/gone.go"): ("expansion", "package", "base"),
    ("src/app/core.py", "src/app/helpers.py"): ("import", "file", "snapshot"),
    ("src/app/core.py", "src/app/entities.py"): ("import", "file", "snapshot"),
    ("src/app/core.py", "src/app/legacy.py"): ("import", "file", "base"),
    ("src/app/report.py", "src/app/entities.py"): ("import", "file", "base"),
    ("src/tests/test_core.py", "src/app/core.py"): ("import", "file", "snapshot"),
    # Expansion reaches every file in the imported package, test files included;
    # the renderer, not the script, drops test files from the side columns.
    ("pkg/a_test.go", "pkg/b.go"): ("expansion", "package", "snapshot"),
    ("pkg/a.go", "util/u_test.go"): ("expansion", "package", "snapshot"),
    ("web/lib/index.ts", "web/lib/x.ts"): ("import", "file", "snapshot"),
    ("web/lib/x.test.ts", "web/lib/x.ts"): ("import", "file", "snapshot"),
    ("src/lib.rs", "src/foo.rs"): ("import", "file", "snapshot"),
    ("src/lib.rs", "src/bar/baz.rs"): ("import", "file", "snapshot"),
    ("src/bar/mod.rs", "src/bar/baz.rs"): ("import", "file", "snapshot"),
    ("Sources/App/main.swift", "Sources/Core/core.swift"): ("expansion", "package", "snapshot"),
    ("Tests/CoreTests/CoreTests.swift", "Sources/Core/core.swift"): ("expansion", "package", "snapshot"),
}

EXPECTED_NODES = {
    # path: (status, group, is_test, old_path)
    "pkg/a.go": ("modified", "example.com/m/pkg", False, None),
    "pkg/c.go": ("added", "example.com/m/pkg", False, None),
    "pkg/gone.go": ("deleted", "example.com/m/pkg", False, None),
    "pkg/big.go": ("added", "example.com/m/pkg", False, None),
    "pkg/a_test.go": ("modified", "example.com/m/pkg", True, None),
    "util/u.go": ("modified", "example.com/m/util", False, None),
    "util/v.go": ("added", "example.com/m/util", False, None),
    "main.go": ("unchanged", "example.com/m", False, None),
    "src/app/core.py": ("modified", "src/app", False, None),
    "src/app/entities.py": ("renamed", "src/app", False, "src/app/models.py"),
    "src/app/legacy.py": ("deleted", "src/app", False, None),
    "src/app/helpers.py": ("unchanged", "src/app", False, None),
    "src/app/report.py": ("unchanged", "src/app", False, None),
    "src/tests/test_core.py": ("modified", "src/tests", True, None),
    "pkg/b.go": ("unchanged", "example.com/m/pkg", False, None),
    "util/u_test.go": ("unchanged", "example.com/m/util", True, None),
    "web/lib/x.ts": ("modified", "web/lib", False, None),
    "web/lib/index.ts": ("unchanged", "web/lib", False, None),
    "web/lib/x.test.ts": ("unchanged", "web/lib", True, None),
    "src/foo.rs": ("modified", "src", False, None),
    "src/bar/baz.rs": ("modified", "src/bar", False, None),
    "src/lib.rs": ("unchanged", "src", False, None),
    "src/bar/mod.rs": ("unchanged", "src/bar", False, None),
    "Sources/Core/core.swift": ("modified", "Core", False, None),
    "Sources/App/main.swift": ("unchanged", "App", False, None),
    "Tests/CoreTests/CoreTests.swift": ("modified", "Tests/CoreTests", True, None),
    "spec/foo_spec.rb": ("added", "spec", True, None),
}


class RepoTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.repo = Path(cls._tmp.name) / "repo"
        cls.repo.mkdir()
        cls.shas = build_repo(cls.repo)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def assert_graph(self, diagram: dict, snapshot_tree: str) -> None:
        self.assertEqual(diagram["snapshot_tree"], snapshot_tree)
        self.assertEqual(diagram["base_tree"], self.shas["base"])
        nodes = node_map(diagram)
        for path, (status, group, is_test, old_path) in EXPECTED_NODES.items():
            with self.subTest(node=path):
                self.assertIn(path, nodes)
                n = nodes[path]
                self.assertEqual(n["status"], status)
                self.assertEqual(n["group"], group)
                self.assertEqual(n["is_test"], is_test)
                self.assertEqual(n["old_path"], old_path)
        for absent in ("link_to_a.go", "web/index.ts", "web/app.ts", "go.mod", "README.md",
                       "notes.txt", "fmt", "testing", "strings", "src/app/models.py",
                       "src/app/__init__.py"):
            self.assertNotIn(absent, nodes, absent)
        edges = edge_map(diagram)
        for key, (method, granularity, tree) in EXPECTED_EDGES.items():
            with self.subTest(edge=key):
                self.assertIn(key, edges)
                e = edges[key]
                self.assertEqual(e["method"], method)
                self.assertEqual(e["granularity"], granularity)
                self.assertEqual(e["tree"], tree)
        for (a, b) in edges:
            self.assertIn(a, nodes, a)
            self.assertIn(b, nodes, b)
            self.assertTrue(nodes[a]["status"] != "unchanged" or nodes[b]["status"] != "unchanged")
        self.assertFalse(any(a == "pkg/big.go" for (a, _) in edges))
        self.assertEqual(diagram["column_status"], {"dependents": "complete", "dependencies": "complete"})
        self.assertIn({"path": "pkg/big.go", "reason": "blob over 1 MB"}, diagram["skipped"])

    def assert_diff_tests(self, diff_tests: dict) -> None:
        self.assertEqual(diff_tests["added"], ["TestNew", "testNew", "test_two"])
        self.assertEqual(diff_tests["removed"], ["TestOld"])
        self.assertEqual(diff_tests["unpatterned_files"], ["spec/foo_spec.rb"])


class ShaSnapshotTest(RepoTestCase):
    def test_graph_and_diff_tests(self) -> None:
        code, diagram, diff_tests, err = run(
            ["--repo", str(self.repo), "--snapshot", self.shas["snapshot"], "--base", self.shas["base"]])
        self.assertEqual(code, 0, err)
        self.assert_graph(diagram, self.shas["snapshot"])
        self.assertNotIn("pkg/untracked.go", node_map(diagram))
        self.assert_diff_tests(diff_tests)

    def test_output_is_deterministic(self) -> None:
        args = ["--repo", str(self.repo), "--snapshot", self.shas["snapshot"], "--base", self.shas["base"]]
        _, a, ta, _ = run(args)
        _, b, tb, _ = run(args)
        self.assertEqual(a, b)
        self.assertEqual(ta, tb)

    def test_failed_columns_without_import_patterns(self) -> None:
        code, diagram, diff_tests, err = run(
            ["--repo", str(self.repo), "--snapshot", self.shas["docs"], "--base", self.shas["snapshot"]])
        self.assertEqual(code, 0, err)
        self.assertEqual(diagram["column_status"], {
            "dependents": "failed: no import patterns for .rb",
            "dependencies": "failed: no import patterns for .rb",
        })
        self.assertEqual(diagram["edges"], [])
        self.assertEqual(sorted(node_map(diagram)), ["spec/foo_spec.rb"])
        self.assertEqual(diff_tests, {"added": [], "removed": [], "unpatterned_files": ["spec/foo_spec.rb"]})

    def test_non_code_changes_leave_no_nodes(self) -> None:
        code, diagram, diff_tests, err = run(
            ["--repo", str(self.repo), "--snapshot", self.shas["docs_only"], "--base", self.shas["snapshot"]])
        self.assertEqual(code, 0, err)
        self.assertEqual(diagram["nodes"], [])
        self.assertEqual(diagram["edges"], [])
        self.assertEqual(diagram["column_status"], {
            "dependents": "failed: no code files changed",
            "dependencies": "failed: no code files changed",
        })
        self.assertEqual(diff_tests, {"added": [], "removed": [], "unpatterned_files": []})

    def test_script_runs_from_the_command_line(self) -> None:
        with tempfile.TemporaryDirectory() as out:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--repo", str(self.repo),
                 "--snapshot", self.shas["snapshot"], "--base", self.shas["base"], "--out", out],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(out) / "diagram.json").exists())
            self.assertTrue((Path(out) / "diff-tests.json").exists())
            self.assertIn("diagram.json", result.stdout)

    def test_bad_base_exits_non_zero(self) -> None:
        code, diagram, _, err = run(
            ["--repo", str(self.repo), "--snapshot", self.shas["snapshot"], "--base", "0" * 40])
        self.assertNotEqual(code, 0)
        self.assertIsNone(diagram)
        self.assertIn("error", err)


class WorkingTreeSnapshotTest(RepoTestCase):
    def test_reads_disk_and_counts_untracked_as_added(self) -> None:
        code, diagram, diff_tests, err = run(
            ["--repo", str(self.repo), "--snapshot", "working-tree", "--base", self.shas["base"]])
        self.assertEqual(code, 0, err)
        self.assert_graph(diagram, "working-tree")
        nodes = node_map(diagram)
        self.assertEqual(nodes["pkg/untracked.go"],
                         {"path": "pkg/untracked.go", "status": "added", "group": "example.com/m/pkg",
                          "is_test": False, "old_path": None})
        edges = edge_map(diagram)
        self.assertEqual(edges[("pkg/untracked.go", "util/u.go")]["tree"], "snapshot")
        self.assertEqual(edges[("main.go", "pkg/untracked.go")]["method"], "expansion")
        self.assert_diff_tests(diff_tests)

    def test_untracked_test_file_contributes_diff_tests(self) -> None:
        write(self.repo, "pkg/extra_test.go",
              'package pkg\n\nimport "testing"\n\nfunc TestExtra(t *testing.T) {}\n')
        try:
            code, diagram, diff_tests, err = run(
                ["--repo", str(self.repo), "--snapshot", "working-tree", "--base", self.shas["base"]])
            self.assertEqual(code, 0, err)
            self.assertIn("TestExtra", diff_tests["added"])
            self.assertTrue(node_map(diagram)["pkg/extra_test.go"]["is_test"])
        finally:
            (self.repo / "pkg/extra_test.go").unlink()


GO_LIST_STUB = '''\
import json, sys
repo = sys.argv[1]
pkgs = [
    {"ImportPath": "example.com/m", "Dir": repo, "GoFiles": ["main.go"],
     "Imports": ["fmt", "example.com/m/pkg", "example.com/m/util"]},
    {"ImportPath": "example.com/m/pkg", "Dir": repo + "/pkg", "GoFiles": ["a.go", "b.go", "c.go"],
     "TestGoFiles": [], "XTestGoFiles": ["a_test.go"], "XTestImports": ["testing", "example.com/m/pkg"],
     "Imports": ["example.com/m/util"]},
    {"ImportPath": "example.com/m/util", "Dir": repo + "/util", "GoFiles": ["u.go", "v.go"],
     "Imports": []},
]
for p in pkgs:
    print(json.dumps(p, indent=1))
'''


class ToolsTest(RepoTestCase):
    def ecosystems_with_tool(self, deps: str) -> Path:
        data = json.loads(ECOSYSTEMS.read_text(encoding="utf-8"))
        data["go"]["tool"] = {"name": "go list", "deps": deps, "format": "go-list-json",
                              "granularity": "package"}
        path = Path(self._tmp.name) / "eco.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_tool_edges_replace_scanned_pairs(self) -> None:
        stub = Path(self._tmp.name) / "golist.py"
        stub.write_text(GO_LIST_STUB, encoding="utf-8")
        eco = self.ecosystems_with_tool(f'"{sys.executable}" "{stub}" "{self.repo}"')
        code, diagram, _, err = run(
            ["--repo", str(self.repo), "--snapshot", self.shas["snapshot"], "--base", self.shas["base"],
             "--tools", "--ecosystems", str(eco)])
        self.assertEqual(code, 0, err)
        edges = edge_map(diagram)
        for key in (("main.go", "pkg/a.go"), ("main.go", "pkg/c.go"), ("pkg/a.go", "util/u.go"),
                    ("pkg/a_test.go", "pkg/a.go")):
            self.assertEqual(edges[key]["method"], "tool:go list", key)
            self.assertEqual(edges[key]["granularity"], "package")
            self.assertEqual(edges[key]["tree"], "snapshot")
        # The tool knows nothing about the base tree or other languages.
        self.assertEqual(edges[("main.go", "pkg/gone.go")]["method"], "expansion")
        self.assertEqual(edges[("main.go", "pkg/gone.go")]["tree"], "base")
        self.assertEqual(edges[("src/app/core.py", "src/app/helpers.py")]["method"], "import")
        self.assertEqual(edges[("pkg/a_test.go", "pkg/b.go")]["method"], "tool:go list")

    def test_failing_tool_keeps_scanned_edges_with_a_warning(self) -> None:
        eco = self.ecosystems_with_tool(f'"{sys.executable}" -c "import sys; sys.exit(3)"')
        code, diagram, _, err = run(
            ["--repo", str(self.repo), "--snapshot", self.shas["snapshot"], "--base", self.shas["base"],
             "--tools", "--ecosystems", str(eco)])
        self.assertEqual(code, 0, err)
        self.assertEqual(edge_map(diagram)[("main.go", "pkg/a.go")]["method"], "expansion")
        self.assertIn("warning", err)
        self.assertIn("go list", err)


class FakeGitHub:
    """Serves compare, trees, and blobs from the local repository."""

    def __init__(self, repo: Path, truncated: bool = False) -> None:
        self.repo = repo
        self.truncated = truncated
        self.blob_calls = 0
        self.tree_calls = 0
        self.compare_calls = 0

    def __call__(self, path: str) -> object:
        m = re.match(r"repos/([^/]+/[^/]+)/(compare|git/trees|git/blobs)/([^?]+)(?:\?(.*))?$", path)
        assert m, path
        kind, rest = m.group(2), m.group(3)
        if kind == "compare":
            self.compare_calls += 1
            base, head = rest.split("...")
            files = []
            raw = git(self.repo, "diff", "--name-status", "-M", "-C", "-z", base, head)
            parts = raw.split("\0")
            i = 0
            names = {"A": "added", "M": "modified", "D": "removed", "R": "renamed",
                     "C": "copied", "T": "changed"}
            while i < len(parts) and parts[i]:
                status = parts[i][0]
                if status in "RC":
                    old, new = parts[i + 1], parts[i + 2]
                    i += 3
                else:
                    old, new = None, parts[i + 1]
                    i += 2
                entry = {"status": names[status], "filename": new}
                if old:
                    entry["previous_filename"] = old
                patch = git(self.repo, "diff", base, head, "-M", "-C", "--", *(p for p in (old, new) if p))
                body = patch.split("\n@@", 1)
                if len(body) == 2:
                    entry["patch"] = "@@" + body[1]
                files.append(entry)
            page = int(re.search(r"(?:^|&)page=(\d+)", m.group(4) or "page=1").group(1))
            return {"files": files if page == 1 else [], "merge_base_commit": {"sha": base}}
        if kind == "git/trees":
            self.tree_calls += 1
            entries = []
            for line in git(self.repo, "ls-tree", "-r", "-l", rest).splitlines():
                meta, _, p = line.partition("\t")
                mode, typ, sha, size = meta.split()
                entries.append({"path": p, "mode": mode, "type": typ, "sha": sha,
                                "size": int(size) if size != "-" else 0})
            return {"sha": rest, "tree": entries, "truncated": self.truncated}
        self.blob_calls += 1
        raw = subprocess.run(["git", "-C", str(self.repo), "cat-file", "blob", rest],
                             check=True, capture_output=True).stdout
        return {"sha": rest, "encoding": "base64", "content": base64.b64encode(raw).decode()}


class RemoteTest(RepoTestCase):
    def setUp(self) -> None:
        self._gh = blast_radius.gh_api
        self._cap = blast_radius.REMOTE_BLOB_CAP

    def tearDown(self) -> None:
        blast_radius.gh_api = self._gh
        blast_radius.REMOTE_BLOB_CAP = self._cap

    def test_remote_matches_local(self) -> None:
        fake = FakeGitHub(self.repo)
        blast_radius.gh_api = fake
        code, diagram, diff_tests, err = run(
            ["--remote", "acme/widgets", "--snapshot", self.shas["snapshot"], "--base", self.shas["base"]])
        self.assertEqual(code, 0, err)
        self.assert_graph(diagram, self.shas["snapshot"])
        self.assert_diff_tests(diff_tests)
        self.assertEqual(fake.tree_calls, 2)
        self.assertGreater(fake.blob_calls, 0)
        self.assertLessEqual(fake.blob_calls, blast_radius.REMOTE_BLOB_CAP)
        _, local, _, _ = run(
            ["--repo", str(self.repo), "--snapshot", self.shas["snapshot"], "--base", self.shas["base"]])
        self.assertEqual(diagram, local)

    def test_blob_cap_marks_dependents_partial(self) -> None:
        fake = FakeGitHub(self.repo)
        blast_radius.gh_api = fake
        blast_radius.REMOTE_BLOB_CAP = 1
        code, diagram, _, err = run(
            ["--remote", "acme/widgets", "--snapshot", self.shas["snapshot"], "--base", self.shas["base"]])
        self.assertEqual(code, 0, err)
        self.assertEqual(diagram["column_status"]["dependents"], "partial: remote scan cap reached")
        self.assertEqual(diagram["column_status"]["dependencies"], "complete")
        edges = edge_map(diagram)
        # Dependencies come from the changed files' own blobs and are unaffected.
        self.assertIn(("src/app/core.py", "src/app/helpers.py"), edges)
        self.assertIn(("pkg/a.go", "util/u.go"), edges)
        self.assertNotIn(("web/lib/index.ts", "web/lib/x.ts"), edges)

    def test_truncated_tree_fails_both_columns(self) -> None:
        blast_radius.gh_api = FakeGitHub(self.repo, truncated=True)
        code, diagram, _, err = run(
            ["--remote", "acme/widgets", "--snapshot", self.shas["snapshot"], "--base", self.shas["base"]])
        self.assertEqual(code, 0, err)
        self.assertEqual(diagram["column_status"], {
            "dependents": "failed: tree listing truncated",
            "dependencies": "failed: tree listing truncated",
        })
        self.assertEqual(diagram["edges"], [])
        self.assertIn("pkg/a.go", node_map(diagram))

    def test_remote_rejects_working_tree_and_tools(self) -> None:
        blast_radius.gh_api = FakeGitHub(self.repo)
        code, diagram, _, err = run(
            ["--remote", "acme/widgets", "--snapshot", "working-tree", "--base", self.shas["base"]])
        self.assertEqual(code, 2)
        self.assertIsNone(diagram)
        self.assertIn("working-tree", err)
        code, diagram, _, err = run(
            ["--remote", "acme/widgets", "--snapshot", self.shas["snapshot"], "--base", self.shas["base"],
             "--tools"])
        self.assertEqual(code, 2)
        self.assertIsNone(diagram)
        self.assertIn("--tools", err)


class ParserTest(unittest.TestCase):
    def test_name_status_mapping(self) -> None:
        raw = ("A\0a.go\0M\0b.go\0D\0c.go\0R100\0old.py\0new.py\0C075\0src.go\0copy.go\0"
               "T\0notes.txt\0")
        changed = blast_radius.parse_name_status(raw)
        self.assertEqual(
            [(c.path, c.status, c.old_path) for c in changed],
            [("a.go", "added", None), ("b.go", "modified", None), ("c.go", "deleted", None),
             ("new.py", "renamed", "old.py"), ("copy.go", "added", None),
             ("notes.txt", "modified", None)],
        )

    def test_ls_tree_parsing_skips_symlinks_and_submodules(self) -> None:
        raw = ("100644 blob aaaa     12\tpkg/a.go\0"
               "120000 blob bbbb      8\tlink.go\0"
               "160000 commit cccc       -\tvendor/sub\0"
               "100755 blob dddd 2000000\tpkg/big.go\0"
               "100644 blob eeee      3\tdir with\ttab/x.py\0")
        entries = blast_radius.parse_ls_tree(raw)
        self.assertEqual(sorted(entries), ["dir with\ttab/x.py", "pkg/a.go", "pkg/big.go"])
        self.assertEqual(entries["pkg/a.go"].sha, "aaaa")
        self.assertEqual(entries["pkg/big.go"].size, 2000000)

    def test_test_decl_names(self) -> None:
        eco = blast_radius.load_ecosystems(ECOSYSTEMS)
        diff = ("@@ -1,3 +1,4 @@\n+func TestNew(t *testing.T) {}\n-func TestOld(t *testing.T) {}\n"
                " func helper() {}\n+++ b/x_test.go\n")
        added, removed = blast_radius.diff_test_names(diff, eco.row_for("x_test.go"))
        self.assertEqual((added, removed), ({"TestNew"}, {"TestOld"}))
        rust = ("+#[test]\n+fn added_case() {}\n-#[tokio::test]\n-async fn removed_case() {}\n"
                "+fn not_a_test() {}\n")
        added, removed = blast_radius.diff_test_names(rust, eco.row_for("src/lib.rs"))
        self.assertEqual((added, removed), ({"added_case"}, {"removed_case"}))
        ts = "+it('adds numbers', () => {});\n+test(\"names things\", () => {});\n"
        added, _ = blast_radius.diff_test_names(ts, eco.row_for("a.test.ts"))
        self.assertEqual(added, {"adds numbers", "names things"})

    def test_test_file_detection(self) -> None:
        eco = blast_radius.load_ecosystems(ECOSYSTEMS)
        cases = {
            "pkg/a_test.go": True, "pkg/a.go": False,
            "tests/test_core.py": True, "src/app/core.py": False, "conftest.py": True,
            "web/lib/x.test.ts": True, "web/__tests__/y.ts": True, "web/lib/x.ts": False,
            "Tests/CoreTests/CoreTests.swift": True, "Sources/Core/core.swift": False,
            "tests/integration.rs": True, "src/lib.rs": False,
            "spec/foo_spec.rb": True, "lib/foo.rb": False, "docs/testing.md": False,
            # No row: whole-token names and directories only.
            "specs/review-html-tests-diagram/design.md": False, "specs/overview.md": False,
            "contest/latest.md": False, "lib/foo-test.sh": True, "lib/foo.spec.rb": True,
            "app/test/Helpers.kt": True, "Sources/App/AppTests.kt": True,
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(blast_radius.is_test_file(path, eco.row_for(path)), expected)

    def test_code_detection(self) -> None:
        cases = {
            "pkg/a.go": True, "lib/foo.rb": True, "deploy.sh": True, "Makefile": True,
            "main.tf": True, ".gitignore": True,
            "README.md": False, "docs/design.MD": False, "notes.txt": False, "guide.rst": False,
            "package.json": False, "config.yaml": False, "Cargo.toml": False, "go.sum": True,
            "Cargo.lock": False, "logo.png": False, "icon.svg": False, "fonts/a.woff2": False,
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(blast_radius.is_code(path), expected)


if __name__ == "__main__":
    unittest.main()
