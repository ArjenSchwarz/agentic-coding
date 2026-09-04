"""Helpers shared by every renderer module.

``sections.py`` and ``diagram.py`` both import from here; nothing here imports
from them.
"""
from __future__ import annotations

import hashlib
import html


def escape(s: object) -> str:
    """HTML-escape a value for text or attribute context; ``None`` becomes ``""``."""
    return html.escape("" if s is None else str(s), quote=True)


def digest(s: str) -> str:
    """First 10 hex characters of the SHA-1 of ``s``; shared by anchors and node ids."""
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]


def file_anchor(path: str) -> str:
    return "file-" + digest(path)


def severity_pill(sev: str) -> str:
    klass = {
        "blocking": "error",
        "major": "error",
        "minor": "warning",
        "nit": "tertiary",
        "info": "tertiary",
    }.get(sev.lower(), "tertiary")
    return f'<span class="pill pill-{klass}">{escape(sev)}</span>'
