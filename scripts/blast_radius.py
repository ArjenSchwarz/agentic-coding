#!/usr/bin/env python3
"""Derive the one-hop dependency graph around a change from git trees.

Reads two trees (the snapshot and the base), scans imports per
``ecosystems.json``, and writes ``diagram.json`` (nodes, edges, column
status, skipped files) plus ``diff-tests.json`` (test declarations added and
removed in changed test files). The renderer applies the projection rules;
this script only reports what the trees say.

Usage:
    blast_radius.py --repo DIR --snapshot (SHA|working-tree) --base SHA
                    [--remote OWNER/REPO] [--ecosystems FILE] [--tools] --out DIR

``--remote`` reads both trees through the GitHub trees and blobs API instead
of git, for use without a clone; it cannot be combined with a working-tree
snapshot or ``--tools``. ``--tools`` runs each ecosystem row's dependency tool
in ``--repo`` and lets its edges replace scanned edges for the same pair.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import posixpath
import re
import stat
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

MAX_BLOB = 1024 * 1024          # blobs over this are recorded as skipped, never scanned
REMOTE_BLOB_CAP = 500           # blob API calls before dependents scanning stops
COMPARE_PAGE = 300              # compare API files per page
SKIP_MODES = ("120000", "160000")   # symlinks and submodules
STATUS_CODES = {"A": "added", "M": "modified", "D": "deleted", "R": "renamed",
                "C": "added", "T": "modified"}
REMOTE_STATUSES = {"added": "added", "modified": "modified", "removed": "deleted",
                   "renamed": "renamed", "copied": "added", "changed": "modified"}
# Without an ecosystem row: test-looking file names (test_x, x_test, x.test.ts,
# x.spec.js, XTests.swift, conftest.py) or a parent directory that is itself a
# test directory. Whole tokens only, so ``specs/`` and ``docs/testing.md`` are
# not tests.
_FALLBACK_TEST_NAME = re.compile(
    r"^(test[_-]|conftest\.py$)|[_-]tests?\.\w+$|\.(test|spec)\.\w+$|Tests?\.\w+$")
_FALLBACK_TEST_DIRS = frozenset({"test", "tests", "__tests__", "spec"})
# Documentation, data, and asset files never enter the diagram, changed or
# not. Code in a language without an ecosystem row keeps its node so the
# centre column still lists it.
_NON_CODE_EXTENSIONS = frozenset({
    ".md", ".markdown", ".mdx", ".rst", ".txt", ".adoc", ".asciidoc",
    ".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".cfg", ".csv", ".lock",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".pdf",
    ".woff", ".woff2", ".ttf", ".otf",
})


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


# --- ecosystems -------------------------------------------------------------

@dataclass
class ImportSpec:
    regex: re.Pattern
    resolve: str
    separator: str


@dataclass
class Row:
    name: str
    extensions: list
    test_files: list
    test_decl: object            # re.Pattern or None
    unit: dict
    imports: list
    source_roots: list
    index_files: list
    extension_map: dict
    tool: object                 # dict or None


class Ecosystems:
    def __init__(self, data: dict) -> None:
        self.rows = {}
        self.by_ext = {}
        for name, raw in data.items():
            row = Row(
                name=name,
                extensions=[e.lower() for e in raw.get("extensions", [])],
                test_files=[re.compile(p) for p in raw.get("test_files", [])],
                test_decl=re.compile(raw["test_decl"], re.MULTILINE) if raw.get("test_decl") else None,
                unit=raw.get("unit") or {"kind": "directory"},
                imports=[ImportSpec(re.compile(i["regex"], re.MULTILINE), i.get("resolve", "relative"),
                                    i.get("separator", "."))
                         for i in raw.get("imports", [])],
                source_roots=raw.get("source_roots") or ["."],
                index_files=raw.get("index_files") or [],
                extension_map=raw.get("extension_map") or {},
                tool=raw.get("tool"),
            )
            self.rows[name] = row
            for ext in row.extensions:
                self.by_ext.setdefault(ext, row)

    def row_for(self, path: str):
        return self.by_ext.get(posixpath.splitext(path)[1].lower())


def load_ecosystems(path: Path) -> Ecosystems:
    return Ecosystems(json.loads(path.read_text(encoding="utf-8")))


def is_test_file(path: str, row) -> bool:
    """The row's patterns, or the name/nearest-directory rule without a row."""
    if row is not None and row.test_files:
        return any(p.search(path) for p in row.test_files)
    name = posixpath.basename(path)
    parent = posixpath.basename(posixpath.dirname(path))
    return bool(_FALLBACK_TEST_NAME.search(name)) or parent in _FALLBACK_TEST_DIRS


def is_code(path: str) -> bool:
    """False for documentation, data, and asset files by extension."""
    return posixpath.splitext(path)[1].lower() not in _NON_CODE_EXTENSIONS


# --- changed files ----------------------------------------------------------

@dataclass
class Changed:
    path: str
    status: str
    old_path: object = None      # str for renames


def parse_name_status(raw: str) -> list:
    """Parse ``git diff --name-status -z`` output; C becomes added, T modified."""
    parts = raw.split("\0")
    out = []
    i = 0
    while i < len(parts) and parts[i]:
        code = parts[i][0]
        if code in "RC":
            old, new = parts[i + 1], parts[i + 2]
            i += 3
        else:
            old, new = None, parts[i + 1]
            i += 2
        if code in STATUS_CODES:
            out.append(Changed(new, STATUS_CODES[code], old if code == "R" else None))
    return out


def git(repo: Path, *args: str, binary: bool = False):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])} failed: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.stdout if binary else result.stdout.decode("utf-8", "replace")


def changed_files_local(repo: Path, base: str, snapshot: str) -> list:
    args = ["diff", "--name-status", "-M", "-C", "-z", base]
    if snapshot != "working-tree":
        args.append(snapshot)
    changed = parse_name_status(git(repo, *args))
    if snapshot == "working-tree":
        seen = {c.path for c in changed}
        for path in git(repo, "ls-files", "--others", "--exclude-standard", "-z").split("\0"):
            if path and path not in seen:
                changed.append(Changed(path, "added", None))
    return changed


def gh_api(path: str) -> object:
    """One GitHub API call through ``gh``; tests replace this function."""
    remote = "/".join(path.split("/")[1:3])
    result = subprocess.run(["gh", "api", "-R", remote, path], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh api {path}: {result.stderr.strip()}")
    return json.loads(result.stdout)


def changed_files_remote(remote: str, base: str, snapshot: str) -> tuple:
    files = []
    page = 1
    while True:
        data = gh_api(f"repos/{remote}/compare/{base}...{snapshot}?per_page={COMPARE_PAGE}&page={page}")
        batch = data.get("files") or []
        files.extend(batch)
        if len(batch) < COMPARE_PAGE:
            break
        page += 1
    changed = []
    patches = {}
    for f in files:
        status = REMOTE_STATUSES.get(f.get("status"))
        if status is None:
            continue
        old = f.get("previous_filename") if f.get("status") == "renamed" else None
        changed.append(Changed(f["filename"], status, old))
        patches[f["filename"]] = f.get("patch") or ""
    return changed, patches


# --- trees ------------------------------------------------------------------

@dataclass
class Entry:
    path: str
    sha: object                  # str, or None for working-tree files
    size: int
    mode: str


def parse_ls_tree(raw: str) -> dict:
    """Parse ``git ls-tree -r -l -z``; symlinks and submodules are dropped."""
    entries = {}
    for record in raw.split("\0"):
        if not record:
            continue
        meta, _, path = record.partition("\t")
        fields = meta.split()
        if len(fields) != 4:
            continue
        mode, kind, sha, size = fields
        if mode in SKIP_MODES or kind != "blob":
            continue
        entries[path] = Entry(path, sha, int(size) if size.isdigit() else 0, mode)
    return entries


class CatFile:
    """One ``git cat-file --batch`` process serving blob reads by SHA."""

    def __init__(self, repo: Path) -> None:
        self.proc = subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch"],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def read(self, sha: str):
        self.proc.stdin.write((sha + "\n").encode("ascii"))
        self.proc.stdin.flush()
        header = self.proc.stdout.readline().split()
        if len(header) < 3:
            return None
        size = int(header[2])
        data = self.proc.stdout.read(size)
        self.proc.stdout.read(1)
        return data

    def close(self) -> None:
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


class Tree:
    """A file listing plus a blob reader; ``label`` names it on edges."""

    label = ""
    truncated = False

    def __init__(self) -> None:
        self.entries = {}

    def read(self, path: str, essential: bool = False):
        raise NotImplementedError

    def close(self) -> None:
        pass


class GitTree(Tree):
    def __init__(self, repo: Path, sha: str, label: str) -> None:
        super().__init__()
        self.label = label
        self.entries = parse_ls_tree(git(repo, "ls-tree", "-r", "-l", "-z", sha))
        self.cat = CatFile(repo)

    def read(self, path: str, essential: bool = False):
        entry = self.entries.get(path)
        if entry is None:
            return None
        data = self.cat.read(entry.sha)
        return None if data is None else data.decode("utf-8", "replace")

    def close(self) -> None:
        self.cat.close()


class WorkingTree(Tree):
    label = "snapshot"

    def __init__(self, repo: Path) -> None:
        super().__init__()
        self.repo = repo
        tracked = git(repo, "ls-files", "-z")
        self.tracked = set(tracked.split("\0"))
        listing = tracked + git(repo, "ls-files", "--others", "--exclude-standard", "-z")
        for path in listing.split("\0"):
            if not path:
                continue
            try:
                st = os.lstat(repo / path)
            except OSError:
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            self.entries[path] = Entry(path, None, st.st_size, "100644")

    def read(self, path: str, essential: bool = False):
        try:
            return (self.repo / path).read_bytes().decode("utf-8", "replace")
        except OSError:
            return None


class RemoteBudget:
    def __init__(self) -> None:
        self.calls = 0
        self.cap_hit = False


class RemoteTree(Tree):
    def __init__(self, remote: str, sha: str, label: str, budget: RemoteBudget) -> None:
        super().__init__()
        self.remote = remote
        self.label = label
        self.budget = budget
        data = gh_api(f"repos/{remote}/git/trees/{sha}?recursive=1")
        self.truncated = bool(data.get("truncated"))
        for item in data.get("tree") or []:
            if item.get("type") != "blob" or item.get("mode") in SKIP_MODES:
                continue
            self.entries[item["path"]] = Entry(item["path"], item["sha"], int(item.get("size") or 0),
                                               item.get("mode", "100644"))

    def read(self, path: str, essential: bool = False):
        entry = self.entries.get(path)
        if entry is None:
            return None
        if not essential and self.budget.calls >= REMOTE_BLOB_CAP:
            self.budget.cap_hit = True
            return None
        self.budget.calls += 1
        data = gh_api(f"repos/{self.remote}/git/blobs/{entry.sha}")
        content = data.get("content") or ""
        if data.get("encoding") == "base64":
            raw = base64.b64decode(content)
        else:
            raw = content.encode("utf-8")
        return raw.decode("utf-8", "replace")


# --- groups and resolution --------------------------------------------------

class Grouper:
    """Maps a file to its unit (package, target, or directory) within one tree."""

    def __init__(self, eco: Ecosystems, tree: Tree) -> None:
        self.eco = eco
        self.tree = tree
        self._modules = {}       # module_file name -> {dir: module path}

    def _modules_for(self, row: Row) -> dict:
        name = row.unit.get("module_file")
        if name in self._modules:
            return self._modules[name]
        regex = re.compile(row.unit.get("module_regex", r"^module\s+(\S+)"), re.MULTILINE)
        modules = {}
        for path in sorted(self.tree.entries):
            if posixpath.basename(path) != name:
                continue
            text = self.tree.read(path, essential=True) or ""
            m = regex.search(text)
            if m:
                modules[posixpath.dirname(path)] = m.group(1)
        self._modules[name] = modules
        return modules

    def group(self, path: str, row) -> str:
        directory = posixpath.dirname(path) or "."
        if row is None:
            return directory
        kind = row.unit.get("kind", "directory")
        if kind == "module_file":
            modules = self._modules_for(row)
            d = posixpath.dirname(path)
            while True:
                if d in modules:
                    rel = posixpath.relpath(posixpath.dirname(path) or ".", d or ".")
                    return modules[d] if rel == "." else modules[d] + "/" + rel
                if not d:
                    return directory
                d = posixpath.dirname(d)
        if kind == "target_root":
            root = row.unit.get("target_root", "Sources")
            if path.startswith(root + "/"):
                segments = path[len(root) + 1:].split("/")
                if len(segments) >= 2:
                    return segments[0]
        return directory


class Resolver:
    """Resolves import strings to files of one tree."""

    def __init__(self, eco: Ecosystems, tree: Tree, grouper: Grouper) -> None:
        self.eco = eco
        self.paths = set(tree.entries)
        self.grouper = grouper
        self._by_group = None

    def _unit_index(self) -> dict:
        if self._by_group is None:
            index = {}
            for path in sorted(self.paths):
                row = self.eco.row_for(path)
                if row is None:
                    continue
                index.setdefault((row.name, self.grouper.group(path, row)), []).append(path)
            self._by_group = index
        return self._by_group

    def resolve(self, importer: str, name: str, spec: ImportSpec, row: Row) -> list:
        """Return ``[(target, granularity), ...]``; an unresolved import yields ``[]``."""
        if not name:
            return []
        if spec.resolve == "unit":
            targets = self._unit_index().get((row.name, name), [])
            return [(t, "package") for t in targets if t != importer]
        if spec.resolve == "roots":
            target = self._roots(importer, name, spec, row)
        else:
            target = self._relative(importer, name, row)
        if target is None or target == importer:
            return []
        return [(target, "file")]

    def _try(self, candidate: str, row: Row, with_extensions: bool = True):
        if with_extensions:
            if candidate in self.paths:
                return candidate
            ext = posixpath.splitext(candidate)[1]
            for alt in row.extension_map.get(ext, []):
                p = candidate[:-len(ext)] + alt
                if p in self.paths:
                    return p
            for e in row.extensions:
                if candidate + e in self.paths:
                    return candidate + e
        for index in row.index_files:
            p = posixpath.join(candidate, index) if candidate else index
            if p in self.paths:
                return p
        return None

    def _relative(self, importer: str, name: str, row: Row):
        base = posixpath.dirname(importer)
        bases = [base]
        if not name.startswith("."):
            # A bare name (Rust ``mod foo;``) may live under the importer's own
            # module directory; crate roots and index files use the sibling rule.
            stem = posixpath.splitext(posixpath.basename(importer))[0]
            if posixpath.basename(importer) not in row.index_files and stem not in ("lib", "main"):
                bases.insert(0, posixpath.join(base, stem) if base else stem)
        for b in bases:
            candidate = posixpath.normpath(posixpath.join(b, name) if b else name)
            if candidate.startswith("../") or candidate == "..":
                continue
            found = self._try(candidate, row)
            if found:
                return found
        return None

    def _roots(self, importer: str, name: str, spec: ImportSpec, row: Row):
        sep = spec.separator or "."
        if name.startswith(sep):
            level = 0
            while name.startswith(sep, level * len(sep)):
                level += 1
            rest = name[level * len(sep):]
            d = posixpath.dirname(importer)
            for _ in range(level - 1):
                d = posixpath.dirname(d)
            segments = [s for s in rest.split(sep) if s]
            bases = [d]
        else:
            segments = [s for s in name.split(sep) if s]
            bases = ["" if r == "." else r for r in row.source_roots]
        attempts = [segments]
        if segments:
            attempts.append(segments[:-1])     # a symbol import: drop the last segment once
        for attempt in attempts:
            for b in bases:
                candidate = posixpath.join(b, *attempt) if attempt else b
                found = self._try(candidate, row, with_extensions=bool(attempt))
                if found:
                    return found
        return None


def _groups(m: re.Match) -> list:
    """The match's participating capture groups, in order."""
    return [g for g in m.groups() if g is not None]


def scan_imports(text: str, row: Row) -> list:
    """``[(import string, spec), ...]`` in source order."""
    out = []
    for spec in row.imports:
        for m in spec.regex.finditer(text):
            groups = _groups(m)
            if not groups:
                name = m.group(0)
            elif len(groups) == 1:
                name = groups[0]
            else:
                name = groups[0]
                for g in groups[1:]:
                    name += g if name.endswith(spec.separator) else spec.separator + g
            out.append((name.strip(), spec))
    return out


# --- tools ------------------------------------------------------------------

def parse_go_list(output: str, repo: Path) -> list:
    """File pairs from ``go list -json`` output (a stream of JSON objects)."""
    decoder = json.JSONDecoder()
    packages = []
    text = output.strip()
    index = 0
    while index < len(text):
        obj, end = decoder.raw_decode(text, index)
        packages.append(obj)
        index = end
        while index < len(text) and text[index].isspace():
            index += 1
    by_import = {p.get("ImportPath"): p for p in packages}
    real_repo = os.path.realpath(str(repo))

    def rel(pkg: dict, name: str) -> str:
        d = pkg.get("Dir") or ""
        if os.path.isabs(d):
            d = os.path.relpath(os.path.realpath(d), real_repo)
        return posixpath.normpath(posixpath.join(d.replace(os.sep, "/"), name))

    def files_of(pkg: dict) -> list:
        return [rel(pkg, f) for f in (pkg.get("GoFiles") or []) + (pkg.get("CgoFiles") or [])]

    pairs = []
    for pkg in packages:
        sets = (
            (files_of(pkg) + [rel(pkg, f) for f in pkg.get("TestGoFiles") or []],
             (pkg.get("Imports") or []) + (pkg.get("TestImports") or [])),
            ([rel(pkg, f) for f in pkg.get("XTestGoFiles") or []], pkg.get("XTestImports") or []),
        )
        for files, imports in sets:
            targets = [t for imp in imports if imp in by_import for t in files_of(by_import[imp])]
            for f in files:
                for t in targets:
                    pairs.append((f, t))
    return pairs


def parse_pairs(output: str) -> list:
    pairs = []
    for line in output.splitlines():
        a, _, b = line.partition("\t")
        if a and b:
            pairs.append((a.strip(), b.strip()))
    return pairs


def tool_edges(row: Row, repo: Path) -> list:
    tool = row.tool
    result = subprocess.run(tool["deps"], shell=True, cwd=str(repo), capture_output=True, text=True)
    if result.returncode != 0:
        tail = result.stderr.strip().splitlines()[-1:] or [""]
        raise RuntimeError(f"exit {result.returncode}: {tail[0]}")
    if tool.get("format") == "go-list-json":
        return parse_go_list(result.stdout, repo)
    return parse_pairs(result.stdout)


# --- diff-derived tests -----------------------------------------------------

def _decl_names(text: str, row: Row) -> set:
    names = set()
    for m in row.test_decl.finditer(text):
        groups = _groups(m)
        if groups:
            names.add(groups[0])
        else:
            names.add(re.sub(r"^\s*\w+\s+", "", m.group(0)).strip())
    return names


def diff_test_names(diff: str, row: Row) -> tuple:
    """``(added, removed)`` declaration names from a unified diff."""
    added, removed = [], []
    for line in diff.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
    return _decl_names("\n".join(added), row), _decl_names("\n".join(removed), row)


def local_diff(repo: Path, base: str, snapshot: str, changed: Changed, tracked: bool) -> str:
    if not tracked:
        result = subprocess.run(["git", "-C", str(repo), "diff", "--no-index", "--", "/dev/null", changed.path],
                                capture_output=True)
        return result.stdout.decode("utf-8", "replace")
    args = ["diff", "-M", "-C", base]
    if snapshot != "working-tree":
        args.append(snapshot)
    args += ["--"] + [p for p in (changed.old_path, changed.path) if p]
    return git(repo, *args)


# --- build ------------------------------------------------------------------

@dataclass
class Graph:
    nodes: dict = field(default_factory=dict)
    edges: dict = field(default_factory=dict)
    skipped: dict = field(default_factory=dict)


def build(args: argparse.Namespace, eco: Ecosystems) -> tuple:
    repo = Path(args.repo).resolve()
    base, snapshot = args.base, args.snapshot
    working = snapshot == "working-tree"
    patches = {}
    if args.remote:
        changed, patches = changed_files_remote(args.remote, base, snapshot)
        budget = RemoteBudget()
        snap_tree = RemoteTree(args.remote, snapshot, "snapshot", budget)
        base_tree = RemoteTree(args.remote, base, "base", budget)
    else:
        changed = changed_files_local(repo, base, snapshot)
        budget = None
        snap_tree = WorkingTree(repo) if working else GitTree(repo, snapshot, "snapshot")
        base_tree = GitTree(repo, base, "base")
    try:
        return _build(args, eco, repo, changed, patches, snap_tree, base_tree, budget)
    finally:
        snap_tree.close()
        base_tree.close()


def _build(args, eco, repo, changed, patches, snap_tree, base_tree, budget) -> tuple:
    changed = [c for c in changed if is_code(c.path)]
    changed_set = {c.path for c in changed}
    deleted = {c.path for c in changed if c.status == "deleted"}
    old_to_new = {c.old_path: c.path for c in changed if c.old_path}
    groupers = {snap_tree.label: Grouper(eco, snap_tree), base_tree.label: Grouper(eco, base_tree)}
    trees = {snap_tree.label: snap_tree, base_tree.label: base_tree}
    resolvers = {label: Resolver(eco, tree, groupers[label]) for label, tree in trees.items()}
    graph = Graph()

    def ensure_node(path: str, tree_label: str, changed_entry=None) -> None:
        if path in graph.nodes:
            return
        row = eco.row_for(path)
        status = changed_entry.status if changed_entry else "unchanged"
        graph.nodes[path] = {
            "path": path, "status": status,
            "group": groupers[tree_label].group(path, row),
            "is_test": is_test_file(path, row),
            "old_path": changed_entry.old_path if changed_entry else None,
        }

    for c in changed:
        ensure_node(c.path, "base" if c.status == "deleted" else "snapshot", c)

    column_status = {"dependents": "complete", "dependencies": "complete"}
    failed = None
    if snap_tree.truncated or base_tree.truncated:
        failed = "tree listing truncated"
    elif not changed:
        failed = "no code files changed"
    elif not any(eco.row_for(c.path) and eco.row_for(c.path).imports for c in changed):
        exts = sorted({posixpath.splitext(c.path)[1] or "(none)" for c in changed})
        failed = "no import patterns for " + ", ".join(exts)
    if failed:
        column_status = {"dependents": "failed: " + failed, "dependencies": "failed: " + failed}
    else:
        def add_edge(a: str, b: str, method: str, granularity: str, tree_label: str,
                     replace: bool = False) -> None:
            if a == b or (a not in changed_set and b not in changed_set):
                return
            if not is_code(a) or not is_code(b):
                return
            if (a, b) in graph.edges and not replace:
                return
            graph.edges[(a, b)] = {"from": a, "to": b, "method": method,
                                   "granularity": granularity, "tree": tree_label}
            ensure_node(a, tree_label)
            ensure_node(b, tree_label)

        import_cache = {}

        def scan(path: str, tree_label: str, essential: bool, only_targets=None) -> None:
            tree = trees[tree_label]
            row = eco.row_for(path)
            entry = tree.entries.get(path)
            if row is None or not row.imports or entry is None:
                return
            if entry.size > MAX_BLOB:
                graph.skipped.setdefault(path, "blob over 1 MB")
                return
            key = (entry.sha, row.name) if entry.sha else None
            imports = import_cache.get(key) if key else None
            if imports is None:
                text = tree.read(path, essential)
                if text is None:
                    return
                imports = scan_imports(text, row)
                if key:
                    import_cache[key] = imports
            source = old_to_new.get(path, path) if tree_label == "base" else path
            for name, spec in imports:
                for target, granularity in resolvers[tree_label].resolve(path, name, spec, row):
                    if only_targets is not None and target not in only_targets:
                        continue
                    mapped = old_to_new.get(target, target) if tree_label == "base" else target
                    add_edge(source, mapped, "expansion" if granularity == "package" else "import",
                             granularity, tree_label)

        # Dependencies and centre edges: the changed files' own blobs.
        for c in changed:
            if c.status != "deleted":
                scan(c.path, "snapshot", essential=True)
        for path in sorted(deleted):
            scan(path, "base", essential=True)
        # Dependents: every other snapshot file.
        for path in sorted(snap_tree.entries):
            if path not in changed_set:
                scan(path, "snapshot", essential=False)
        # Base-tree importers of deleted files and old renamed paths.
        base_targets = deleted | set(old_to_new)
        if base_targets:
            for path in sorted(base_tree.entries):
                if path not in base_targets:
                    scan(path, "base", essential=False, only_targets=base_targets)
        if budget is not None and budget.cap_hit:
            column_status["dependents"] = "partial: remote scan cap reached"

        if args.tools:
            changed_rows = {eco.row_for(c.path).name for c in changed if eco.row_for(c.path)}
            for name in sorted(changed_rows):
                row = eco.rows[name]
                if not row.tool:
                    continue
                tool_name = row.tool.get("name") or row.tool["deps"].split()[0]
                try:
                    pairs = tool_edges(row, repo)
                except (RuntimeError, OSError, ValueError) as exc:
                    warn(f"tool {tool_name} failed, keeping scanned edges: {exc}")
                    continue
                for a, b in pairs:
                    add_edge(a, b, f"tool:{tool_name}", row.tool.get("granularity", "package"),
                             "snapshot", replace=True)

    # Diff-derived tests.
    added, removed, unpatterned = set(), set(), []
    for c in changed:
        row = eco.row_for(c.path)
        if not is_test_file(c.path, row):
            continue
        if row is None or row.test_decl is None:
            unpatterned.append(c.path)
            continue
        if args.remote:
            diff = patches.get(c.path, "")
        else:
            # A working-tree snapshot is a WorkingTree, which lists the tracked files.
            is_tracked = (args.snapshot != "working-tree" or c.status == "deleted"
                          or c.path in snap_tree.tracked)
            diff = local_diff(repo, args.base, args.snapshot, c, is_tracked)
        a, r = diff_test_names(diff, row)
        added |= a
        removed |= r

    diagram = {
        "snapshot_tree": args.snapshot,
        "base_tree": args.base,
        "nodes": [graph.nodes[p] for p in sorted(graph.nodes)],
        "edges": [graph.edges[k] for k in sorted(graph.edges)],
        "column_status": column_status,
        "skipped": [{"path": p, "reason": r} for p, r in sorted(graph.skipped.items())],
    }
    diff_tests = {
        "added": sorted(added - removed),
        "removed": sorted(removed - added),
        "unpatterned_files": sorted(unpatterned),
    }
    return diagram, diff_tests


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Derive the one-hop dependency graph around a change.")
    parser.add_argument("--repo", default=".", help="Repository directory (default: current directory).")
    parser.add_argument("--snapshot", required=True, help="Commit SHA, or 'working-tree'.")
    parser.add_argument("--base", required=True, help="Base commit SHA.")
    parser.add_argument("--remote", default=None, metavar="OWNER/REPO",
                        help="Read both trees through the GitHub API instead of git.")
    parser.add_argument("--ecosystems", type=Path,
                        default=Path(__file__).resolve().parent / "ecosystems.json")
    parser.add_argument("--tools", action="store_true",
                        help="Run each ecosystem row's dependency tool in --repo.")
    parser.add_argument("--out", required=True, type=Path, help="Directory for the two output files.")
    args = parser.parse_args(argv)

    if args.remote and args.snapshot == "working-tree":
        parser.error("--remote needs a commit SHA snapshot, not working-tree")
    if args.remote and args.tools:
        parser.error("--tools needs a local checkout and cannot be combined with --remote")
    try:
        eco = load_ecosystems(args.ecosystems)
    except (OSError, ValueError) as exc:
        print(f"error: cannot load ecosystems file {args.ecosystems}: {exc}", file=sys.stderr)
        return 1
    try:
        diagram, diff_tests = build(args, eco)
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    for name, payload in (("diagram.json", diagram), ("diff-tests.json", diff_tests)):
        path = args.out / name
        path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(str(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
