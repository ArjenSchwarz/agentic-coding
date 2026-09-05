"""Coverage parsing, path mapping, matching against changed files, arithmetic.

The order is mapping → matching → merging: ``apply_path_map`` rewrites
paths, ``match`` decides which entries belong to which changed file in five
global passes, and only its last pass (and ``overall``) sums hits.
"""
from __future__ import annotations

import posixpath
from dataclasses import dataclass
from pathlib import Path

from .inputs import read_guarded, xml_root
from .warnings import Warnings


@dataclass
class Entry:
    paths: list[str]         # primary path first, then aliases
    hits: dict[int, int]


Coverage = list[Entry]

NO_CANDIDATE = "no candidate"
AMBIGUOUS = "ambiguous"


# --- parsing ---------------------------------------------------------------

def _sniff(path: Path) -> str | None:
    """``"xml"``, ``"lcov"``, ``"coverprofile"``, or ``None`` from the file head."""
    try:
        with path.open("rb") as fh:
            head = fh.read(4096)
    except OSError:
        return None
    text = head.decode("utf-8", errors="replace").lstrip("\N{ZERO WIDTH NO-BREAK SPACE} \t\r\n")
    if text.startswith("<"):
        return "xml"
    if text.startswith(("TN:", "SF:")):
        return "lcov"
    if text.startswith("mode: "):
        return "coverprofile"
    return None


def parse_coverage(path: Path, warnings: Warnings) -> Coverage:
    kind = _sniff(path)
    text = read_guarded(path, warnings, xml=(kind == "xml"))
    if text is None:
        return []
    if kind == "lcov":
        return _parse_lcov(text)
    if kind == "coverprofile":
        return _parse_coverprofile(text, path.name, warnings)
    if kind == "xml":
        return _parse_cobertura(text, path.name, warnings)
    warnings.add(f"{path.name}: skipped, not lcov, Cobertura XML, or Go coverprofile")
    return []


def _parse_lcov(text: str) -> Coverage:
    cov: Coverage = []
    current: Entry | None = None
    for line in text.splitlines():
        if line.startswith("SF:"):
            current = Entry([line[3:].strip()], {})
            cov.append(current)
        elif line.startswith("DA:") and current is not None:
            number, _, rest = line[3:].partition(",")
            count = rest.partition(",")[0]
            try:
                n = int(number)
                h = int(count)
            except ValueError:
                continue
            current.hits[n] = current.hits.get(n, 0) + h
        elif line.startswith("end_of_record"):
            current = None
    return [e for e in cov if e.paths[0]]


def _parse_coverprofile(text: str, name: str, warnings: Warnings) -> Coverage:
    lines = text.splitlines()
    if not lines or not lines[0].startswith("mode: "):
        warnings.add(f"{name}: skipped, coverprofile has no mode line")
        return []
    entries: dict[str, Entry] = {}
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        file, sep, rest = line.rpartition(":")
        if not sep:
            continue
        parts = rest.split()
        if len(parts) != 3:
            continue
        try:
            start, end = parts[0].split(",")
            sl = int(start.split(".")[0])
            el = int(end.split(".")[0])
            count = int(parts[2])
        except ValueError:
            continue
        entry = entries.get(file)
        if entry is None:
            entry = entries[file] = Entry([file], {})
        for n in range(sl, el + 1):
            if count > entry.hits.get(n, -1):
                entry.hits[n] = count
    return list(entries.values())


def _parse_cobertura(text: str, name: str, warnings: Warnings) -> Coverage:
    root = xml_root(text, name, warnings, ("coverage",), "coverage XML", "Cobertura <coverage>")
    if root is None:
        return []
    sources = [s.text.strip() for s in root.iter("source") if s.text and s.text.strip()]
    cov: Coverage = []
    for cls in root.iter("class"):
        filename = cls.get("filename")
        if not filename:
            continue
        hits: dict[int, int] = {}
        for line in cls.findall("lines/line"):
            try:
                n = int(line.get("number", ""))
                h = int(float(line.get("hits", "0")))
            except ValueError:
                continue
            if h > hits.get(n, -1):
                hits[n] = h
        paths = [filename] + [f"{s}/{filename}" for s in sources]
        cov.append(Entry(paths, hits))
    return cov


# --- normalisation and mapping --------------------------------------------

def normalise(path: str) -> str:
    return posixpath.normpath(path.replace("\\", "/"))


def apply_path_map(cov: Coverage, strip: str | None, prepend: str | None) -> Coverage:
    """Normalise every path, then strip and prepend whole leading segments."""
    strip = normalise(strip) if strip else None
    prepend = normalise(prepend) if prepend else None
    out: Coverage = []
    for e in cov:
        paths = []
        for p in e.paths:
            p = normalise(p)
            if strip:
                p = p.removeprefix(strip + "/")
            if prepend:
                p = normalise(f"{prepend}/{p}")
            paths.append(p)
        out.append(Entry(paths, e.hits))
    return out


# --- matching ---------------------------------------------------------------

def _segments(path: str) -> tuple[str, ...]:
    return tuple(path.split("/"))


def _residual(e: tuple[str, ...], c: tuple[str, ...]) -> tuple[str, tuple[str, ...]] | None:
    """Direction and uncovered segments when one segment tuple is a whole-segment suffix of the other."""
    if len(e) > len(c) and e[-len(c):] == c:
        return ("entry", e[:-len(c)])
    if len(c) > len(e) and c[-len(e):] == e:
        return ("file", c[:-len(e)])
    return None


def _merge(entries: list[Entry]) -> dict[int, int]:
    merged: dict[int, int] = {}
    for e in entries:
        for n, h in e.hits.items():
            merged[n] = merged.get(n, 0) + h
    return merged


def match(cov: Coverage, changed: list[str]) -> tuple[dict[str, dict[int, int]], dict[str, str]]:
    """Five global passes: exact, pools, shared removal, residuals, merge.

    Returns merged hits per matched changed file and the reason
    (``"no candidate"`` or ``"ambiguous"``) per unmatched file.
    """
    matched: dict[str, dict[int, int]] = {}
    unmatched: dict[str, str] = {}
    norm = {c: normalise(c) for c in changed}
    epaths = [[normalise(p) for p in e.paths] for e in cov]
    esegs = [[_segments(p) for p in paths] for paths in epaths]
    pool = set(range(len(cov)))
    # Entry indexes by path (pass 1) and by last segment (pass 2): a
    # whole-segment suffix relation needs equal last segments, so only
    # those entries can hold a residual for a changed file.
    by_path: dict[str, list[int]] = {}
    by_base: dict[str, list[int]] = {}
    for i, paths in enumerate(epaths):
        for p in set(paths):
            by_path.setdefault(p, []).append(i)
        for base in {segs[-1] for segs in esegs[i]}:
            by_base.setdefault(base, []).append(i)

    # 1. Exact.
    exact_files: dict[int, list[str]] = {}
    for c in changed:
        for i in by_path.get(norm[c], ()):
            exact_files.setdefault(i, []).append(c)
    for i, files in exact_files.items():
        if len(files) > 1:
            for c in files:
                unmatched[c] = AMBIGUOUS
            pool.discard(i)
    for c in changed:
        if c in unmatched:
            continue
        hits = [i for i in by_path.get(norm[c], ()) if i in pool]
        if hits:
            matched[c] = _merge([cov[i] for i in hits])
            pool.difference_update(hits)
    remaining = [c for c in changed if c not in matched and c not in unmatched]

    # 2. Pools with residuals.
    pools: dict[str, dict[int, tuple[str, tuple[str, ...]]]] = {}
    for c in remaining:
        pools[c] = {}
        csegs = _segments(norm[c])
        for i in by_base.get(csegs[-1], ()):
            if i not in pool:
                continue
            for segs in esegs[i]:
                residual = _residual(segs, csegs)
                if residual is not None:
                    pools[c][i] = residual
                    break

    # 3. Shared entries leave every pool, once, without cascading.
    seen_in: dict[int, int] = {}
    for c in remaining:
        for i in pools[c]:
            seen_in[i] = seen_in.get(i, 0) + 1
    shared = {i for i, n in seen_in.items() if n > 1}
    for c in remaining:
        had = bool(pools[c])
        pools[c] = {i: r for i, r in pools[c].items() if i not in shared}
        if had and not pools[c]:
            unmatched[c] = AMBIGUOUS

    # 4. Residuals.
    for c in remaining:
        if c in unmatched:
            continue
        if not pools[c]:
            unmatched[c] = NO_CANDIDATE
        elif len(set(pools[c].values())) > 1:
            unmatched[c] = AMBIGUOUS

    # 5. Merge.
    for c in remaining:
        if c not in unmatched:
            matched[c] = _merge([cov[i] for i in sorted(pools[c])])
    return matched, unmatched


# --- arithmetic -------------------------------------------------------------

def diff_coverage(added: set[int], hits: dict[int, int]) -> tuple[int, int] | None:
    """``(covered, measurable)`` over added lines present in ``hits``, or ``None``."""
    measurable = [n for n in added if n in hits]
    if not measurable:
        return None
    covered = sum(1 for n in measurable if hits[n] > 0)
    return covered, len(measurable)


def overall(cov: Coverage) -> tuple[int, int]:
    """``(covered, instrumented)`` after merging entries by normalised primary path."""
    by_path: dict[str, list[Entry]] = {}
    for e in cov:
        if e.paths:
            by_path.setdefault(normalise(e.paths[0]), []).append(e)
    merged = [_merge(entries) for entries in by_path.values()]
    covered = sum(1 for hits in merged for h in hits.values() if h > 0)
    instrumented = sum(len(hits) for hits in merged)
    return covered, instrumented
