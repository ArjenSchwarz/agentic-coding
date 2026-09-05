"""Diff fragments: loading, hunk arithmetic, and rendering.

``load_fragments`` resolves every file's diff text once so the Tests section
and the per-file diff blocks read the same bytes. ``added_lines`` and
``render_diff`` share one walk over the hunks so the line numbers used for
coverage lookups are the ones the rendered marks land on.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from .common import escape
from .inputs import read_guarded
from .warnings import Warnings

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def load_fragments(files: list[dict], diff_dir: Path | None, warnings: Warnings) -> dict[str, str]:
    """Map each file's path to its diff text or a placeholder.

    An inline ``diff`` wins over ``diff_file``. A ``diff_file`` is read from
    ``diff_dir`` through ``read_guarded``; a missing file keeps the historic
    placeholder, an undecodable one gets its own, and both leave the rest of
    the page intact.
    """
    fragments: dict[str, str] = {}
    for f in files:
        path = f.get("path", "")
        diff = f.get("diff")
        name = f.get("diff_file")
        if diff is None and name and diff_dir is not None:
            fragment = diff_dir / name
            if not fragment.exists():
                diff = f"(diff fragment {name!r} missing)"
            else:
                diff = read_guarded(fragment, warnings)
                if diff is None:
                    diff = f"(diff fragment {name!r} is not UTF-8)"
        if diff is None:
            diff = "(no diff provided)"
        fragments[path] = diff
    return fragments


def _walk(diff: str) -> Iterator[tuple[str, str, int | None]]:
    """Yield ``(line, css_class, new_file_number)`` for each line of a diff.

    ``new_file_number`` is set only on ``+`` lines and is the line's number in
    the new file, tracked from the ``@@`` headers. Context and ``+`` lines
    advance the counter; ``-`` lines, headers, and ``\\`` markers do not.
    Line classes match the renderer's historic prefix rules, except that
    ``+++`` and ``---`` are file headers only before a file section's first
    ``@@``; inside a hunk they are added or removed lines whose content
    happens to start with ``++`` or ``--``. A ``diff --git`` line starts a
    new file section.
    """
    if not diff:
        return
    lines = diff.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    next_new: int | None = None
    for line in lines:
        number = None
        if line.startswith("diff --git "):
            cls = "diff-context"
            next_new = None
        elif next_new is None and line.startswith(("+++", "---")):
            cls = "diff-file-header"
        elif line.startswith("@@"):
            cls = "diff-hunk"
            m = _HUNK.match(line)
            next_new = int(m.group(1)) if m else None
        elif line.startswith("+"):
            cls = "diff-add"
            if next_new is not None:
                number = next_new
                next_new += 1
        elif line.startswith("-"):
            cls = "diff-del"
        elif line.startswith("\\"):
            cls = "diff-meta"
        else:
            cls = "diff-context"
            if next_new is not None:
                next_new += 1
        yield line, cls, number


def added_lines(diff: str) -> set[int]:
    """New-file line numbers of every ``+`` line, from the ``@@`` headers."""
    return {number for _, _, number in _walk(diff) if number is not None}


def is_binary(diff: str) -> bool:
    return any(
        line.startswith(("Binary files ", "GIT binary patch"))
        for line in diff.split("\n")
    )


def render_diff(diff: str, uncovered: set[int] | None = None) -> str:
    """Render a unified diff as one <span class="diff-line"> per line.

    Each line is classified by its leading marker so consecutive additions or
    deletions paint a continuous full-width background bar. A ``+`` line whose
    new-file number is in ``uncovered`` also carries ``diff-uncovered``; with
    ``None`` the output is the historic rendering.
    """
    spans = []
    for line, cls, number in _walk(diff):
        if uncovered and number is not None and number in uncovered:
            cls += " diff-uncovered"
        spans.append(f'<span class="diff-line {cls}">{escape(line)}</span>')
    return "".join(spans)
