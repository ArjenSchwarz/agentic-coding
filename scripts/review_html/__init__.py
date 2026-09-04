"""Renderer for the review HTML page used by the review skills.

The package is imported by ``scripts/build_review_html.py``, which owns the
command line; ``render`` is the only public entry point.
"""
from __future__ import annotations

from .render import render

__all__ = ["render"]
