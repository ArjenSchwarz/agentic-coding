"""Guarded file reads.

``read_guarded`` is the only way the package reads an input file (diff
fragments, JUnit, coverage, diagram descriptions). It refuses inputs over
50 MB, inputs that are not UTF-8, and, for XML, inputs carrying a DOCTYPE
declaration; each refusal is recorded as a warning naming the file.
``read_json`` and ``xml_root`` build on it for the two structured formats.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from .warnings import Warnings

MAX_INPUT_BYTES = 50 * 1024 * 1024


def read_guarded(path: Path, warnings: Warnings, xml: bool = False) -> str | None:
    try:
        size = path.stat().st_size
        if size > MAX_INPUT_BYTES:
            warnings.add(f"{path.name}: skipped, larger than 50 MB ({size} bytes)")
            return None
        raw = path.read_bytes()
    except OSError as exc:
        warnings.add(f"{path.name}: cannot read ({exc.strerror or exc})")
        return None
    # The whole buffer, not a window: comments and processing instructions
    # may precede the DOCTYPE, so a window could be padded past.
    if xml and b"<!DOCTYPE" in raw:
        warnings.add(f"{path.name}: skipped, XML contains a DOCTYPE declaration")
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        warnings.add(f"{path.name}: skipped, not valid UTF-8")
        return None


def read_json(path: Path, warnings: Warnings, what: str) -> object:
    """Parsed JSON of a guarded read, or ``None`` with a warning naming ``what``."""
    text = read_guarded(path, warnings)
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError as exc:
        warnings.add(f"{path.name}: {what} is not valid JSON ({exc})")
        return None


def xml_root(text: str, name: str, warnings: Warnings, expected_tags: tuple,
             kind: str, expected: str) -> ET.Element | None:
    """Root element of ``text`` when it parses and its tag is expected, else ``None``.

    ``kind`` names the format in the malformed warning ("JUnit XML");
    ``expected`` describes the accepted root in the wrong-root warning.
    """
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        warnings.add(f"{name}: skipped, {kind} is malformed ({exc})")
        return None
    if root.tag not in expected_tags:
        warnings.add(f"{name}: skipped, root element is <{root.tag}>, not {expected}")
        return None
    return root
