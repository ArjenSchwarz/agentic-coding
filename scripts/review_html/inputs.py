"""Guarded file reads.

``read_guarded`` is the only way the package reads an input file (diff
fragments, JUnit, coverage, diagram descriptions). It refuses inputs over
50 MB, inputs that are not UTF-8, and, for XML, inputs carrying a DOCTYPE
declaration; each refusal is recorded as a warning naming the file.
"""
from __future__ import annotations

from pathlib import Path

from .warnings import Warnings

MAX_INPUT_BYTES = 50 * 1024 * 1024
DOCTYPE_SCAN_BYTES = 64 * 1024


def read_guarded(path: Path, warnings: Warnings, xml: bool = False) -> str | None:
    try:
        size = path.stat().st_size
    except OSError as exc:
        warnings.add(f"{path.name}: cannot read ({exc.strerror or exc})")
        return None
    if size > MAX_INPUT_BYTES:
        warnings.add(f"{path.name}: skipped, larger than 50 MB ({size} bytes)")
        return None
    try:
        raw = path.read_bytes()
    except OSError as exc:
        warnings.add(f"{path.name}: cannot read ({exc.strerror or exc})")
        return None
    if xml and b"<!DOCTYPE" in raw[:DOCTYPE_SCAN_BYTES]:
        warnings.add(f"{path.name}: skipped, XML contains a DOCTYPE declaration")
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        warnings.add(f"{path.name}: skipped, not valid UTF-8")
        return None
